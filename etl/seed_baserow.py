import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import random
import datetime
import logging
from config import Config
from etl.baserow_client import BaserowClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("SeedBaserow")

CATEGORIES = [
    "Payment Failed", "Login Issue", "API Rate Limit", "Billing Dispute", 
    "Feature Request", "UI Bug", "Performance Degradation", "Account Suspension",
    "Data Export Error", "Integration Failure"
]

PRIORITIES = ["Urgent", "High", "Medium", "Low"]
PRIORITY_WEIGHTS = [0.15, 0.30, 0.40, 0.15]

STATUSES = ["Open", "In Progress", "Resolved", "Closed"]
STATUS_WEIGHTS = [0.08, 0.07, 0.65, 0.20]

CHANNELS = ["Email", "Web Portal", "Live Chat", "Phone"]
REGIONS = ["US-East", "US-West", "EU-Central", "APAC", "LATAM"]
TEAMS = ["Billing Ops", "Technical Support", "Tier-2 Escalations", "Enterprise Support"]
SEGMENTS = ["Enterprise", "Mid-Market", "SMB", "Free Tier"]
PLANS = ["Enterprise Platinum", "Pro Monthly", "Pro Annual", "Starter"]

PRODUCTS_DATA = [
    {"product_id": "PRD-01", "product_name": "Cloud API Gateway", "product_category": "Developer Tools"},
    {"product_id": "PRD-02", "product_name": "Billing & Payments Suite", "product_category": "Fintech Services"},
    {"product_id": "PRD-03", "product_name": "User Identity & Auth", "product_category": "Security"},
    {"product_id": "PRD-04", "product_name": "Analytics Dashboard Pro", "product_category": "Business Intelligence"},
    {"product_id": "PRD-05", "product_name": "Mobile SDK Platform", "product_category": "Mobile Software"}
]

AGENTS_DATA = [
    {"agent_id": "AGT-101", "name": "Rahul Sharma", "team": "Billing Ops", "region": "APAC", "joining_date": "2023-01-15", "manager": "Vikram Seth"},
    {"agent_id": "AGT-102", "name": "Priya Patel", "team": "Technical Support", "region": "APAC", "joining_date": "2023-03-20", "manager": "Vikram Seth"},
    {"agent_id": "AGT-103", "name": "Alex Mercer", "team": "Enterprise Support", "region": "US-East", "joining_date": "2022-06-10", "manager": "Sarah Jenkins"},
    {"agent_id": "AGT-104", "name": "Samantha Reed", "team": "Tier-2 Escalations", "region": "US-East", "joining_date": "2022-09-01", "manager": "Sarah Jenkins"},
    {"agent_id": "AGT-105", "name": "David Mueller", "team": "Technical Support", "region": "EU-Central", "joining_date": "2023-05-12", "manager": "Hans Weber"},
    {"agent_id": "AGT-106", "name": "Elena Rostova", "team": "Billing Ops", "region": "EU-Central", "joining_date": "2023-08-01", "manager": "Hans Weber"},
    {"agent_id": "AGT-107", "name": "Marcus Vance", "team": "Enterprise Support", "region": "US-West", "joining_date": "2021-11-04", "manager": "Sarah Jenkins"},
    {"agent_id": "AGT-108", "name": "Chloe Bennett", "team": "Tier-2 Escalations", "region": "US-West", "joining_date": "2024-02-01", "manager": "Sarah Jenkins"}
]

def generate_synthetic_data(num_tickets=1284, num_customers=150):
    random.seed(42)
    now = datetime.datetime.now(datetime.timezone.utc)
    
    # 1. Customers
    customers = []
    for i in range(1, num_customers + 1):
        cid = f"CST-{1000 + i}"
        signup_dt = (now - datetime.timedelta(days=random.randint(100, 700))).strftime("%Y-%m-%d")
        customers.append({
            "customer_id": cid,
            "customer_segment": random.choice(SEGMENTS),
            "region": random.choice(REGIONS),
            "signup_date": signup_dt,
            "plan": random.choice(PLANS)
        })
        
    # 2. Tickets
    tickets = []
    for i in range(1, num_tickets + 1):
        tkt_id = f"TKT-{1000 + i}"
        customer = random.choice(customers)
        agent = random.choice(AGENTS_DATA)
        product = random.choice(PRODUCTS_DATA)
        category = random.choice(CATEGORIES)
        priority = random.choices(PRIORITIES, weights=PRIORITY_WEIGHTS)[0]
        channel = random.choice(CHANNELS)
        status = random.choices(STATUSES, weights=STATUS_WEIGHTS)[0]
        
        # Timeline generation (last 90 days)
        days_ago = random.uniform(0.05, 90)
        created_dt = now - datetime.timedelta(days=days_ago)
        
        sla_target = Config.SLA_TARGETS_HOURS[priority]
        
        # Response time (0.1h to 4h)
        first_resp_hrs = random.uniform(0.1, 4.0)
        first_resp_dt = created_dt + datetime.timedelta(hours=first_resp_hrs)
        
        resolved_dt_str = None
        csat = None
        
        if status in ["Resolved", "Closed"]:
            # 85% tickets resolved within SLA, 15% breached
            is_breach = random.random() < 0.15
            if is_breach:
                res_hrs = random.uniform(sla_target * 1.05, sla_target * 3.0)
            else:
                res_hrs = random.uniform(0.5, sla_target * 0.95)
                
            resolved_dt = created_dt + datetime.timedelta(hours=res_hrs)
            if resolved_dt > now:
                resolved_dt = now
            resolved_dt_str = resolved_dt.isoformat()
            
            # CSAT rating (1 to 5)
            if is_breach:
                csat = random.choices([1, 2, 3, 4, 5], weights=[0.4, 0.3, 0.2, 0.08, 0.02])[0]
            else:
                csat = random.choices([1, 2, 3, 4, 5], weights=[0.02, 0.05, 0.15, 0.45, 0.33])[0]

        tickets.append({
            "ticket_id": tkt_id,
            "customer_id": customer["customer_id"],
            "agent_id": agent["agent_id"],
            "product_id": product["product_id"],
            "category": category,
            "priority": priority,
            "channel": channel,
            "status": status,
            "created_at": created_dt.isoformat(),
            "first_response_at": first_resp_dt.isoformat(),
            "resolved_at": resolved_dt_str if resolved_dt_str else "",
            "sla_target_hours": float(sla_target),
            "csat": float(csat) if csat else 0.0,
            "customer_region": customer["region"]
        })

    return AGENTS_DATA, customers, PRODUCTS_DATA, tickets

def seed_baserow_instance():
    logger.info("Initializing Baserow connection...")
    client = BaserowClient()
    client.authenticate()
    client.get_or_create_workspace("SupportIQ Operations")
    client.get_or_create_database(Config.BASEROW_DATABASE_NAME)
    
    # Create Tables
    agents_table_id = client.create_table("Agents")
    customers_table_id = client.create_table("Customers")
    products_table_id = client.create_table("Products")
    tickets_table_id = client.create_table("Tickets")
    
    # Generate Synthetic Data
    logger.info("Generating 1,284 synthetic operational tickets...")
    agents, customers, products, tickets = generate_synthetic_data(num_tickets=1284, num_customers=150)
    
    # Populate Tables
    logger.info("Seeding Agents table...")
    client.batch_create_rows(agents_table_id, agents)
    
    logger.info("Seeding Customers table...")
    client.batch_create_rows(customers_table_id, customers)
    
    logger.info("Seeding Products table...")
    client.batch_create_rows(products_table_id, products)
    
    logger.info("Seeding Tickets table...")
    client.batch_create_rows(tickets_table_id, tickets)
    
    logger.info("Baserow seeding completed successfully!")
    return agents, customers, products, tickets

if __name__ == "__main__":
    seed_baserow_instance()
