import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask, render_template, redirect, url_for, flash
from sqlalchemy import create_engine, text
import pandas as pd
from config import Config
from etl.pipeline import SupportIQPipeline
from web.insights_engine import ManagerInsightsEngine

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = "supportiq_secret_key"

engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)

@app.route("/")
def index():
    kpis = {}
    risk_queue = []
    insights = []
    
    try:
        with engine.connect() as conn:
            # Fetch KPIs
            kpi_df = pd.read_sql("SELECT * FROM v_executive_kpis", conn)
            if not kpi_df.empty:
                kpis = kpi_df.iloc[0].to_dict()

            # Fetch Risk Queue
            risk_df = pd.read_sql("SELECT * FROM v_sla_risk_queue LIMIT 20", conn)
            if not risk_df.empty:
                risk_queue = risk_df.to_dict(orient="records")

        # Insights
        insights_engine = ManagerInsightsEngine()
        insights = insights_engine.generate_insights()
    except Exception as e:
        flash(f"Database error: {str(e)}", "danger")

    return render_template("index.html", kpis=kpis, risk_queue=risk_queue, insights=insights)

@app.route("/trigger-etl", methods=["POST"])
def trigger_etl():
    try:
        pipeline = SupportIQPipeline()
        pipeline.run_pipeline()
        return redirect(url_for("index", message="ETL Pipeline executed successfully! Data refreshed."))
    except Exception as e:
        return redirect(url_for("index", message=f"ETL execution failed: {str(e)}"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)
