import pytest
import re
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool
from web.app import create_app
from web.intake import ensure_ops_schema

@pytest.fixture
def test_app():
    # Use shared in-memory SQLite database with StaticPool for fast, isolated testing
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    ensure_ops_schema(engine)
    
    # Create test views so console / risk-queue queries run cleanly
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE VIEW IF NOT EXISTS v_executive_kpis AS
            SELECT 
                100 AS total_tickets,
                15 AS open_tickets,
                85 AS resolved_tickets,
                92.5 AS sla_compliance_pct,
                4.2 AS avg_resolution_hours,
                4.5 AS avg_csat,
                15.0 AS unresolved_backlog_pct;
        """))
        conn.execute(text("""
            CREATE VIEW IF NOT EXISTS v_sla_risk_queue AS
            SELECT 
                'TKT-TEST-01' AS ticket_id,
                'CUST-001' AS customer_id,
                'Enterprise' AS customer_segment,
                'Urgent' AS priority,
                'Login Issue' AS category,
                'A001' AS agent_id,
                'Alice Smith' AS agent_name,
                'Open' AS status,
                '2026-10-19 12:00:00' AS created_at,
                2.0 AS sla_target_hours,
                0.95 AS sla_risk_score,
                'High Risk' AS sla_risk_category;
        """))

    app = create_app(engine_override=engine)
    app.config["TESTING"] = True
    return app

@pytest.fixture
def client(test_app):
    return test_app.test_client()

def test_home_redirect(client):
    """Test that GET / redirects to /console."""
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/console")

def test_console_navbar_active_state(client):
    """Test that GET /console renders base navbar with Console active."""
    response = client.get("/console")
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    
    # Check navbar brand and links presence
    assert "SupportIQ" in html
    assert "Operational Console" in html
    
    # Console link should have the active class
    assert re.search(r'<a\s+href="[^"]*/console"[^>]*class="[^"]*active[^"]*"', html)
    # Intake and Risk Queue should NOT have active class
    assert not re.search(r'<a\s+href="[^"]*/intake[^"]*"[^>]*class="[^"]*active[^"]*"', html)

def test_intake_navbar_active_state(client):
    """Test that GET /intake renders base navbar with New Ticket active."""
    response = client.get("/intake")
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    
    assert "Submit a New Ticket" in html
    # New Ticket link should have the active class
    assert re.search(r'<a\s+href="[^"]*/intake[^"]*"[^>]*class="[^"]*active[^"]*"', html)
    # Console should NOT have active class
    assert not re.search(r'<a\s+href="[^"]*/console"[^>]*class="[^"]*active[^"]*"', html)

def test_risk_queue_navbar_active_state(client):
    """Test that GET /risk-queue renders base navbar with Risk Queue active."""
    response = client.get("/risk-queue")
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    
    assert "Full SLA Risk Queue" in html
    # Risk Queue link should have the active class
    assert re.search(r'<a\s+href="[^"]*/risk-queue"[^>]*class="[^"]*active[^"]*"', html)
    # Console and Intake should NOT have active class
    assert not re.search(r'<a\s+href="[^"]*/console"[^>]*class="[^"]*active[^"]*"', html)
    assert not re.search(r'<a\s+href="[^"]*/intake[^"]*"[^>]*class="[^"]*active[^"]*"', html)

def test_intake_submit_parameterized_sql(client, test_app):
    """Test POST /intake/submit creates a new ticket in ops.tickets using parameterized SQL."""
    form_data = {
        "customer_id": "CUST-9999",
        "product_id": "PROD-002",
        "category": "Payment Failed",
        "priority": "Urgent",
        "channel": "Email",
        "agent_id": "AGENT-007",
        "notes": "Customer reported card declined on checkout."
    }
    response = client.post("/intake/submit", data=form_data, follow_redirects=True)
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert "submitted successfully to ops.tickets" in html

    # Verify ticket in database
    engine = test_app.config["ENGINE"]
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM ops.tickets WHERE customer_id = :cid"), {"cid": "CUST-9999"})
        row = result.fetchone()
        assert row is not None
        assert row._mapping["category"] == "Payment Failed"
        assert row._mapping["priority"] == "Urgent"
        assert row._mapping["status"] == "Open"

def test_post_ticket_status_update(client, test_app):
    """Test updating ticket status using POST route instead of PATCH."""
    # First insert a ticket
    engine = test_app.config["ENGINE"]
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO ops.tickets (ticket_id, customer_id, category, priority, channel, status) VALUES (:tid, :cid, :cat, :prio, :ch, :st)"),
            {"tid": "TKT-UPDATE-01", "cid": "CUST-111", "cat": "Login Issue", "prio": "High", "ch": "Web Portal", "st": "Open"}
        )

    # 1. Test POST /intake/tickets/<id>/status
    response = client.post("/intake/tickets/TKT-UPDATE-01/status", data={"status": "In Progress"}, follow_redirects=True)
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert "updated to In Progress" in html



    # Verify status changed in DB
    with engine.connect() as conn:
        res = conn.execute(text("SELECT status FROM ops.tickets WHERE ticket_id = :tid"), {"tid": "TKT-UPDATE-01"})
        assert res.scalar() == "In Progress"

    # 2. Test POST /intake/tickets/<id>
    response2 = client.post("/intake/tickets/TKT-UPDATE-01", data={"status": "Resolved"}, follow_redirects=True)
    assert response2.status_code == 200

    with engine.connect() as conn:
        res2 = conn.execute(text("SELECT status FROM ops.tickets WHERE ticket_id = :tid"), {"tid": "TKT-UPDATE-01"})
        assert res2.scalar() == "Resolved"

def test_sql_injection_safety(client, test_app):
    """Test that potentially malicious inputs in form fields are safely parameterized."""
    malicious_input = "'; DROP TABLE ops.tickets; --"
    form_data = {
        "customer_id": malicious_input,
        "product_id": "PROD-001",
        "category": malicious_input,
        "priority": "Low",
        "channel": "Chat",
        "notes": malicious_input
    }
    response = client.post("/intake/submit", data=form_data, follow_redirects=True)
    assert response.status_code == 200

    # Ensure table still exists and data was inserted literally
    engine = test_app.config["ENGINE"]
    with engine.connect() as conn:
        res = conn.execute(text("SELECT customer_id FROM ops.tickets WHERE customer_id = :cid"), {"cid": malicious_input})
        assert res.scalar() == malicious_input
