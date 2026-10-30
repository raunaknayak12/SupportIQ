import os

class Config:
    # Security Settings
    SECRET_KEY = os.getenv("SECRET_KEY", "supportiq_secret_key")

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
    
    # Database URI priority: DATABASE_URL -> POSTGRES_URL -> Constructed URI
    _env_db_uri = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL") or os.getenv("SQLALCHEMY_DATABASE_URI")
    if _env_db_uri:
        if _env_db_uri.startswith("postgres://"):
            _env_db_uri = _env_db_uri.replace("postgres://", "postgresql+psycopg2://", 1)
        SQLALCHEMY_DATABASE_URI = _env_db_uri
    else:
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
