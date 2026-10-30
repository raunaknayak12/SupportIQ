import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
from sqlalchemy import create_engine, text
import logging
from config import Config
from etl.baserow_client import BaserowClient, MockBaserowClient
from etl.transform import transform_tickets, transform_dim_table

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ETLPipeline")

class SupportIQPipeline:
    def __init__(self, db_uri=None, use_mock=False):
        self.db_uri = db_uri or Config.SQLALCHEMY_DATABASE_URI
        self.use_mock = use_mock
        self.engine = create_engine(self.db_uri)

    def init_database_schema(self):
        """Execute PostgreSQL schema DDL file to create tables and views."""
        schema_path = os.path.join(os.path.dirname(__file__), "..", "database", "schema.sql")
        with open(schema_path, "r") as f:
            sql_script = f.read()

        logger.info("Initializing PostgreSQL Analytics Database Schema and Views...")
        # For non-PostgreSQL engines (e.g. SQLite), skip DDL execution that contains Postgres-only syntax
        if "sqlite" in str(self.engine.url):
            return
        with self.engine.begin() as conn:
            conn.execute(text(sql_script))
        logger.info("Database schema initialized successfully.")

    def clear_database_data(self):
        """Cleanly drop views and truncate tables before re-loading."""
        with self.engine.begin() as conn:
            if "sqlite" in str(self.engine.url):
                for tbl in ["fact_tickets", "dim_agents", "dim_customers", "dim_products", "sla_risk_log"]:
                    try:
                        conn.execute(text(f"DELETE FROM {tbl};"))
                    except Exception:
                        pass
            else:
                conn.execute(text("DROP VIEW IF EXISTS v_executive_kpis CASCADE;"))
                conn.execute(text("DROP VIEW IF EXISTS v_agent_performance CASCADE;"))
                conn.execute(text("DROP VIEW IF EXISTS v_sla_risk_queue CASCADE;"))
                conn.execute(text("DROP VIEW IF EXISTS v_customer_issue_intelligence CASCADE;"))
                conn.execute(text("TRUNCATE fact_tickets, dim_agents, dim_customers, dim_products, sla_risk_log RESTART IDENTITY CASCADE;"))

    def run_pipeline(self):
        logger.info("Starting SupportIQ ETL Pipeline...")
        self.init_database_schema()
        self.clear_database_data()

        if self.use_mock:
            logger.info("Running pipeline with Mock Baserow Client...")
            client = MockBaserowClient()
        else:
            logger.info("Connecting to live Baserow REST API...")
            client = BaserowClient()
            client.authenticate()

        tables = client.get_tables()
        if not tables and not self.use_mock:
            raise RuntimeError("No tables found in Baserow database!")

        # 1. Fetch Agents
        agents_table_id = tables.get("Agents")
        raw_agents = client.get_rows(agents_table_id) if agents_table_id else []
        df_agents = pd.DataFrame(raw_agents)
        if not df_agents.empty:
            cols = [c for c in ['agent_id', 'name', 'team', 'region', 'joining_date', 'manager'] if c in df_agents.columns]
            df_agents = df_agents[cols].dropna(subset=['agent_id'])
            df_agents = df_agents[df_agents['agent_id'] != ''].drop_duplicates(subset=['agent_id'])
            df_agents.to_sql("dim_agents", self.engine, if_exists="append", index=False)
            logger.info(f"Loaded {len(df_agents)} rows into dim_agents.")

        # 2. Fetch Customers
        customers_table_id = tables.get("Customers")
        raw_customers = client.get_rows(customers_table_id) if customers_table_id else []
        df_customers = pd.DataFrame(raw_customers)
        if not df_customers.empty:
            cols = [c for c in ['customer_id', 'customer_segment', 'region', 'signup_date', 'plan'] if c in df_customers.columns]
            df_customers = df_customers[cols].dropna(subset=['customer_id'])
            df_customers = df_customers[df_customers['customer_id'] != ''].drop_duplicates(subset=['customer_id'])
            df_customers.to_sql("dim_customers", self.engine, if_exists="append", index=False)
            logger.info(f"Loaded {len(df_customers)} rows into dim_customers.")

        # 3. Fetch Products
        products_table_id = tables.get("Products")
        raw_products = client.get_rows(products_table_id) if products_table_id else []
        df_products = pd.DataFrame(raw_products)
        if not df_products.empty:
            cols = [c for c in ['product_id', 'product_name', 'product_category'] if c in df_products.columns]
            df_products = df_products[cols].dropna(subset=['product_id'])
            df_products = df_products[df_products['product_id'] != ''].drop_duplicates(subset=['product_id'])
            df_products.to_sql("dim_products", self.engine, if_exists="append", index=False)
            logger.info(f"Loaded {len(df_products)} rows into dim_products.")

        # 4. Fetch Tickets from Baserow + Ops Intake Tickets
        tickets_table_id = tables.get("Tickets")
        raw_tickets = client.get_rows(tickets_table_id) if tickets_table_id else []

        # Ingest operational tickets submitted via web console intake
        try:
            with self.engine.connect() as conn:
                is_sqlite = "sqlite" in str(self.engine.url)
                ops_tbl = '"ops.tickets"' if is_sqlite else "ops.tickets"
                ops_rows = conn.execute(text(f"SELECT * FROM {ops_tbl}")).fetchall()
                if ops_rows:
                    for row in ops_rows:
                        ot = dict(row._mapping)
                        prio = ot.get("priority", "Medium")
                        sla_target = Config.SLA_TARGETS_HOURS.get(prio, 8.0)
                        ot.setdefault("sla_target_hours", sla_target)
                        ot.setdefault("customer_region", "US-East")
                        ot.setdefault("first_response_at", None)
                        ot.setdefault("resolved_at", None)
                        ot.setdefault("csat", 0.0)
                        raw_tickets.append(ot)
                    logger.info(f"Ingested {len(ops_rows)} operational tickets from ops.tickets.")
        except Exception as e:
            logger.debug(f"ops.tickets check skipped: {e}")

        df_tickets = pd.DataFrame(raw_tickets)
        if not df_tickets.empty:
            df_tickets = df_tickets.dropna(subset=['ticket_id'])
            df_tickets = df_tickets[df_tickets['ticket_id'] != ''].drop_duplicates(subset=['ticket_id'])
            df_tickets_transformed = transform_tickets(df_tickets)
            
            target_cols = [
                'ticket_id', 'customer_id', 'agent_id', 'product_id', 'category',
                'priority', 'channel', 'status', 'created_at', 'first_response_at',
                'resolved_at', 'sla_target_hours', 'first_response_hours', 'resolution_hours',
                'is_sla_breached', 'sla_risk_score', 'sla_risk_category', 'csat',
                'customer_region', 'updated_at'
            ]
            
            present_cols = [c for c in target_cols if c in df_tickets_transformed.columns]
            df_final = df_tickets_transformed[present_cols]
            
            df_final.to_sql("fact_tickets", self.engine, if_exists="append", index=False)
            logger.info(f"Successfully loaded {len(df_final)} rows into fact_tickets.")

            # Log open high-risk tickets to sla_risk_log
            open_risk_df = df_final[df_final['status'].isin(['Open', 'In Progress']) & df_final['sla_risk_score'].notnull()]
            if not open_risk_df.empty:
                risk_log_rows = []
                for _, r in open_risk_df.iterrows():
                    risk_log_rows.append({
                        "ticket_id": r['ticket_id'],
                        "elapsed_hours": round(r['sla_risk_score'] * r['sla_target_hours'], 2),
                        "sla_target_hours": r['sla_target_hours'],
                        "sla_risk_score": r['sla_risk_score'],
                        "sla_risk_category": r['sla_risk_category']
                    })
                pd.DataFrame(risk_log_rows).to_sql("sla_risk_log", self.engine, if_exists="append", index=False)
                logger.info(f"Logged {len(risk_log_rows)} open ticket SLA risk snapshots.")

        # Re-apply view definitions to ensure proper relations
        self.init_database_schema()
        logger.info("SupportIQ ETL Pipeline run completed cleanly!")
        return True

if __name__ == "__main__":
    pipeline = SupportIQPipeline()
    pipeline.run_pipeline()
