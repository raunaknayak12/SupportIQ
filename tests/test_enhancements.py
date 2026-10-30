import pytest
import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool
from etl.transform import classify_sla_risk, transform_tickets
from web.insights_engine import ManagerInsightsEngine
from web.app import create_app
from web.intake import ensure_ops_schema
from config import Config

def test_classify_sla_risk_boundary_conditions():
    """Verify exact boundary classifications for SLA risk scores."""
    # Boundary at 1.0 (breached)
    assert classify_sla_risk(1.0) == "Breached"
    assert classify_sla_risk(1.0001) == "Breached"
    assert classify_sla_risk(2.5) == "Breached"

    # Boundary at 0.8 (high risk)
    assert classify_sla_risk(0.8) == "High Risk"
    assert classify_sla_risk(0.9999) == "High Risk"

    # Boundary at 0.5 (medium risk)
    assert classify_sla_risk(0.5) == "Medium Risk"
    assert classify_sla_risk(0.7999) == "Medium Risk"

    # Below 0.5 (low risk)
    assert classify_sla_risk(0.4999) == "Low Risk"
    assert classify_sla_risk(0.0) == "Low Risk"
    assert classify_sla_risk(-0.1) == "Low Risk"
    assert classify_sla_risk(None) == "Low Risk"

def test_manager_insights_calculations():
    """Verify ManagerInsightsEngine generates coherent metrics without SQL errors."""
    engine = create_engine("sqlite:///:memory:", poolclass=StaticPool, connect_args={"check_same_thread": False})
    
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE fact_tickets (
                ticket_id TEXT PRIMARY KEY,
                category TEXT,
                priority TEXT,
                status TEXT,
                is_sla_breached INTEGER,
                resolution_hours REAL,
                sla_risk_score REAL,
                sla_risk_category TEXT,
                csat REAL
            );
        """))
        conn.execute(text("""
            CREATE TABLE v_agent_performance (
                team TEXT,
                sla_compliance_pct REAL
            );
        """))
        # Insert test tickets
        conn.execute(text("""
            INSERT INTO fact_tickets VALUES
            ('T1', 'Payment Failed', 'High', 'Resolved', 1, 6.0, NULL, 'Resolved', 2.0),
            ('T2', 'Payment Failed', 'High', 'Open', 0, NULL, 0.85, 'High Risk', 0.0),
            ('T3', 'Payment Failed', 'Urgent', 'In Progress', 0, NULL, 1.2, 'Breached', 0.0),
            ('T4', 'Login Issue', 'Low', 'Open', 0, NULL, 0.2, 'Low Risk', 0.0);
        """))
        conn.execute(text("INSERT INTO v_agent_performance VALUES ('Billing Ops', 78.5);"))

    engine_uri = "sqlite:///:memory:"
    insights_engine = ManagerInsightsEngine(db_uri=engine_uri)
    insights_engine.engine = engine  # use the in-memory engine with tables populated

    insights = insights_engine.generate_insights()
    assert len(insights) >= 2

    # Check category alert
    cat_insight = [i for i in insights if i["type"] == "Category Alert"][0]
    assert "Payment Failed" in cat_insight["title"]
    assert "3 tickets" in cat_insight["evidence"]

    # Check SLA breach queue alert
    queue_insight = [i for i in insights if i["type"] == "SLA Breach Queue"][0]
    assert "3 active open tickets" in queue_insight["evidence"]
    assert "1 high-risk" in queue_insight["evidence"]

def test_navbar_sla_breach_badge():
    """Verify live SLA breach count badge renders in navbar when breached tickets exist."""
    engine = create_engine("sqlite:///:memory:", poolclass=StaticPool, connect_args={"check_same_thread": False})
    ensure_ops_schema(engine)

    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE fact_tickets (
                ticket_id TEXT PRIMARY KEY,
                customer_id TEXT,
                status TEXT,
                sla_risk_score REAL,
                sla_risk_category TEXT
            );
        """))
        conn.execute(text("""
            INSERT INTO fact_tickets VALUES
            ('TKT-1', 'CUST-1', 'Open', 1.25, 'Breached'),
            ('TKT-2', 'CUST-2', 'In Progress', 1.10, 'Breached'),
            ('TKT-3', 'CUST-3', 'Open', 0.40, 'Low Risk');
        """))
        conn.execute(text("""
            CREATE VIEW IF NOT EXISTS v_executive_kpis AS
            SELECT 3 AS total_tickets, 3 AS open_tickets, 0 AS resolved_tickets, 0.0 AS sla_compliance_pct, 0.0 AS avg_resolution_hours, 0.0 AS avg_csat, 100.0 AS unresolved_backlog_pct;
        """))
        conn.execute(text("""
            CREATE VIEW IF NOT EXISTS v_sla_risk_queue AS
            SELECT 'TKT-1' AS ticket_id, 'CUST-1' AS customer_id, 'Urgent' AS priority, 'Login' AS category, 'AGT-1' AS agent_id, 'Rahul' AS agent_name, 'Open' AS status, '2026-10-30' AS created_at, 2.0 AS sla_target_hours, 1.25 AS sla_risk_score, 'Breached' AS sla_risk_category;
        """))

    app = create_app(engine_override=engine)
    app.config["TESTING"] = True
    client = app.test_client()

    response = client.get("/console")
    assert response.status_code == 200
    html = response.data.decode("utf-8")

    # The badge with breach count "2" should appear in navbar
    assert 'class="badge bg-danger rounded-pill ms-1"' in html
    assert "2</span>" in html
