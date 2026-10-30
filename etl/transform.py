import pandas as pd
import datetime
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("Transform")

def classify_sla_risk(risk_score):
    if risk_score is None:
        return "Low Risk"
    if risk_score >= 1.0:
        return "Breached"
    elif risk_score >= 0.8:
        return "High Risk"
    elif risk_score >= 0.5:
        return "Medium Risk"
    else:
        return "Low Risk"

def transform_tickets(raw_tickets_df, reference_time=None):
    if raw_tickets_df.empty:
        return pd.DataFrame()

    df = raw_tickets_df.copy()
    if reference_time is None:
        reference_time = datetime.datetime.now(datetime.timezone.utc)

    # Convert timestamps
    df['created_at'] = pd.to_datetime(df['created_at'], utc=True)
    df['first_response_at'] = pd.to_datetime(df['first_response_at'], utc=True, errors='coerce')
    df['resolved_at'] = pd.to_datetime(df['resolved_at'], utc=True, errors='coerce')

    # Convert SLA Target
    df['sla_target_hours'] = pd.to_numeric(df['sla_target_hours'], errors='coerce').fillna(8.0)
    df['csat'] = pd.to_numeric(df['csat'], errors='coerce').fillna(0.0)

    # Calculate first response hours
    df['first_response_hours'] = (
        (df['first_response_at'] - df['created_at']).dt.total_seconds() / 3600.0
    ).round(2)

    # Calculate resolution hours for resolved tickets
    df['resolution_hours'] = (
        (df['resolved_at'] - df['created_at']).dt.total_seconds() / 3600.0
    ).round(2)

    # SLA Breach status for resolved tickets
    df['is_sla_breached'] = df.apply(
        lambda r: (r['resolution_hours'] > r['sla_target_hours']) if r['status'] in ['Resolved', 'Closed'] and pd.notnull(r['resolution_hours']) else False,
        axis=1
    )

    # SLA Risk Score calculation for open / in-progress tickets
    def calc_risk(row):
        if row['status'] in ['Open', 'In Progress']:
            elapsed = (reference_time - row['created_at']).total_seconds() / 3600.0
            score = round(max(0.0, elapsed) / max(0.1, float(row['sla_target_hours'])), 4)
            return score
        else:
            return None

    df['sla_risk_score'] = df.apply(calc_risk, axis=1)
    df['sla_risk_category'] = df['sla_risk_score'].apply(
        lambda s: classify_sla_risk(s) if pd.notnull(s) else 'Resolved'
    )

    df['updated_at'] = reference_time
    logger.info(f"Transformed {len(df)} ticket records.")
    return df

def transform_dim_table(raw_df):
    if raw_df.empty:
        return pd.DataFrame()
    return raw_df.copy()
