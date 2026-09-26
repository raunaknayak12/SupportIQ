import os

class Config:
    # Baserow Settings
    BASEROW_URL = os.getenv("BASEROW_URL", "http://localhost:8000")
    BASEROW_EMAIL = os.getenv("BASEROW_EMAIL", "admin@supportiq.local")
    BASEROW_PASSWORD = os.getenv("BASEROW_PASSWORD", "SupportIQ2026!")
    BASEROW_DATABASE_NAME = "SupportIQ Operational Data"
    
    # PostgreSQL Analytics Settings
    POSTGRES_USER = os.getenv("POSTGRES_USER", "supportiq")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "supportiq_pass")
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5433")
    POSTGRES_DB = os.getenv("POSTGRES_DB", "supportiq_analytics")
    
    SQLALCHEMY_DATABASE_URI = (
        f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@"
        f"{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    )
    
    # SLA Targets (in hours) by Priority
    SLA_TARGETS_HOURS = {
        "Urgent": 2.0,
        "High": 4.0,
        "Medium": 8.0,
        "Low": 24.0
    }
