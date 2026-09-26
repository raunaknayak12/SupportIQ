import pytest
import pandas as pd
import datetime
from etl.transform import transform_tickets, classify_sla_risk
from etl.baserow_client import MockBaserowClient

def test_classify_sla_risk():
    assert classify_sla_risk(0.20) == "Low Risk"
    assert classify_sla_risk(0.65) == "Medium Risk"
    assert classify_sla_risk(0.90) == "High Risk"
    assert classify_sla_risk(1.25) == "Breached"

def test_transform_tickets():
    now = datetime.datetime.now(datetime.timezone.utc)
    created_open = (now - datetime.timedelta(hours=6)).isoformat()
    created_resolved = (now - datetime.timedelta(hours=10)).isoformat()
    resolved_time = (now - datetime.timedelta(hours=2)).isoformat()

    raw_data = pd.DataFrame([
        {
            "ticket_id": "TKT-001",
            "customer_id": "C001",
            "agent_id": "A001",
            "product_id": "P001",
            "category": "Payment Failed",
            "priority": "High",
            "channel": "Email",
            "status": "Open",
            "created_at": created_open,
            "first_response_at": (now - datetime.timedelta(hours=5)).isoformat(),
            "resolved_at": "",
            "sla_target_hours": 4.0,
            "csat": 0.0,
            "customer_region": "US-East"
        },
        {
            "ticket_id": "TKT-002",
            "customer_id": "C002",
            "agent_id": "A002",
            "product_id": "P001",
            "category": "Login Issue",
            "priority": "Low",
            "channel": "Web Portal",
            "status": "Resolved",
            "created_at": created_resolved,
            "first_response_at": (now - datetime.timedelta(hours=9)).isoformat(),
            "resolved_at": resolved_time,
            "sla_target_hours": 24.0,
            "csat": 5.0,
            "customer_region": "EU-Central"
        }
    ])

    df = transform_tickets(raw_data, reference_time=now)
    
    assert len(df) == 2
    
    # Check Open ticket SLA risk calculation (6h elapsed / 4h target = 1.5 risk score -> Breached)
    open_tkt = df[df['ticket_id'] == 'TKT-001'].iloc[0]
    assert open_tkt['sla_risk_score'] >= 1.4
    assert open_tkt['sla_risk_category'] == "Breached"
    
    # Check Resolved ticket resolution hours (8h elapsed vs 24h target -> is_sla_breached = False)
    res_tkt = df[df['ticket_id'] == 'TKT-002'].iloc[0]
    assert res_tkt['resolution_hours'] == 8.0
    assert res_tkt['is_sla_breached'] == False

def test_mock_baserow_client():
    client = MockBaserowClient()
    client.seed_data([], [], [], [{"ticket_id": "TKT-100"}])
    rows = client.get_rows(4)
    assert len(rows) == 1
    assert rows[0]["ticket_id"] == "TKT-100"
