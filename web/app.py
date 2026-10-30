import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import logging
from flask import Flask, render_template, redirect, url_for, flash, request
from sqlalchemy import create_engine, text
import pandas as pd
from config import Config
from etl.pipeline import SupportIQPipeline
from web.insights_engine import ManagerInsightsEngine
from web.intake import intake_bp, ensure_ops_schema

logger = logging.getLogger("SupportIQApp")

def create_app(engine_override=None):
    """Application factory for SupportIQ Flask Web Console."""
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.secret_key = Config.SECRET_KEY if hasattr(Config, "SECRET_KEY") else os.getenv("SECRET_KEY", "supportiq_secret_key")

    engine = engine_override or create_engine(Config.SQLALCHEMY_DATABASE_URI)
    app.config["ENGINE"] = engine

    # Ensure operational schema exists on startup
    ensure_ops_schema(engine)

    # Register intake Blueprint (Single app, single port)
    app.register_blueprint(intake_bp, url_prefix="/intake")

    @app.context_processor
    def inject_nav_context():
        """Inject live SLA breach count into navbar templates."""
        breach_count = 0
        try:
            with engine.connect() as conn:
                df = pd.read_sql(
                    "SELECT COUNT(*) AS c FROM fact_tickets WHERE status IN ('Open', 'In Progress') AND (sla_risk_category = 'Breached' OR sla_risk_score >= 1.0)",
                    conn
                )
                if not df.empty and df.iloc[0]['c'] is not None:
                    breach_count = int(df.iloc[0]['c'])
        except Exception:
            breach_count = 0
        return {"sla_breach_count": breach_count}

    def get_executive_kpis():
        """Retrieve executive KPIs from v_executive_kpis view."""
        kpis = {}
        try:
            with engine.connect() as conn:
                kpi_df = pd.read_sql("SELECT * FROM v_executive_kpis", conn)
                if not kpi_df.empty:
                    kpis = kpi_df.iloc[0].to_dict()
        except Exception as e:
            logger.warning(f"Unable to fetch executive KPIs: {e}")
        return kpis

    def get_sla_risk_summary(limit=15):
        """Retrieve top SLA risk queue items."""
        risk_queue = []
        try:
            with engine.connect() as conn:
                risk_df = pd.read_sql(f"SELECT * FROM v_sla_risk_queue LIMIT {limit}", conn)
                if not risk_df.empty:
                    risk_queue = risk_df.to_dict(orient="records")
        except Exception as e:
            logger.warning(f"Unable to fetch SLA risk summary: {e}")
        return risk_queue

    def get_full_sla_risk_queue():
        """Retrieve complete SLA risk queue."""
        full_queue = []
        try:
            with engine.connect() as conn:
                risk_df = pd.read_sql("SELECT * FROM v_sla_risk_queue", conn)
                if not risk_df.empty:
                    full_queue = risk_df.to_dict(orient="records")
        except Exception as e:
            logger.warning(f"Unable to fetch full SLA risk queue: {e}")
        return full_queue

    def generate_manager_insights():
        """Generate operational manager insights from insights engine."""
        try:
            insights_engine = ManagerInsightsEngine(db_uri=str(engine.url))
            return insights_engine.generate_insights()
        except Exception as e:
            logger.warning(f"Unable to generate manager insights: {e}")
            return []

    @app.route("/")
    def home():
        """Redirect home to Ops Console."""
        return redirect(url_for("console"))

    @app.route("/console")
    def console():
        """Operational Console: Executive KPIs, SLA Risk summary & Manager Insights."""
        kpis = get_executive_kpis()
        risk_summary = get_sla_risk_summary()
        insights = generate_manager_insights()
        return render_template(
            "console.html",
            kpis=kpis,
            risk_summary=risk_summary,
            risk_queue=risk_summary,
            insights=insights
        )

    @app.route("/risk-queue")
    def risk_queue():
        """Full SLA Risk Queue table."""
        full_queue = get_full_sla_risk_queue()
        return render_template("risk_queue.html", queue=full_queue)

    @app.route("/run-elt", methods=["POST"])
    @app.route("/trigger-etl", methods=["POST"])
    def run_elt():
        """Trigger SupportIQ ETL Pipeline to refresh analytics store."""
        try:
            pipeline = SupportIQPipeline(db_uri=str(engine.url))
            pipeline.run_pipeline()
            flash("ELT Pipeline executed successfully! Data refreshed.", "success")
        except Exception as e:
            logger.error(f"ETL execution failed: {e}")
            flash(f"ETL execution failed: {str(e)}", "danger")
        return redirect(url_for("console"))

    # Backwards compatibility route for index
    @app.route("/index")
    def index():
        return redirect(url_for("console"))

    return app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)
