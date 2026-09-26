import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import requests
import json
import logging
from config import Config

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("SupersetAutoConnect")

SUPERSET_URL = os.getenv("SUPERSET_URL", "http://localhost:8088").rstrip('/')
SUPERSET_USER = os.getenv("SUPERSET_USER", "admin")
SUPERSET_PASS = os.getenv("SUPERSET_PASS", "admin")

class SupersetAutomator:
    def __init__(self):
        self.base_url = SUPERSET_URL
        self.session = requests.Session()
        self.access_token = None
        self.csrf_token = None

    def authenticate(self):
        auth_url = f"{self.base_url}/api/v1/security/login"
        payload = {
            "username": SUPERSET_USER,
            "password": SUPERSET_PASS,
            "provider": "db",
            "refresh": True
        }
        res = self.session.post(auth_url, json=payload, timeout=10)
        if res.status_code == 200:
            self.access_token = res.json()["access_token"]
            self.session.headers.update({"Authorization": f"Bearer {self.access_token}"})
            logger.info("Successfully authenticated with Superset API.")
            self._fetch_csrf_token()
            return self.access_token
        else:
            logger.error(f"Superset login failed: {res.status_code} - {res.text}")
            raise RuntimeError("Could not authenticate with Superset.")

    def _fetch_csrf_token(self):
        csrf_url = f"{self.base_url}/api/v1/security/csrf_token/"
        res = self.session.get(csrf_url)
        if res.status_code == 200:
            self.csrf_token = res.json().get("result")
            self.session.headers.update({"X-CSRFToken": self.csrf_token})
            logger.info("Retrieved CSRF token.")

    def register_database(self):
        url = f"{self.base_url}/api/v1/database/"
        # Check existing databases
        res = self.session.get(url)
        if res.status_code == 200:
            dbs = res.json().get("result", [])
            for db in dbs:
                if db["database_name"] == "SupportIQ Analytics DB":
                    logger.info(f"Database 'SupportIQ Analytics DB' already registered (ID: {db['id']})")
                    return db["id"]

        sqlalchemy_uri = f"postgresql+psycopg2://{Config.POSTGRES_USER}:{Config.POSTGRES_PASSWORD}@host.docker.internal:{Config.POSTGRES_PORT}/{Config.POSTGRES_DB}"
        payload = {
            "database_name": "SupportIQ Analytics DB",
            "engine": "postgresql",
            "sqlalchemy_uri": sqlalchemy_uri,
            "extra": json.dumps({"allows_virtual_table_explore": True})
        }
        res = self.session.post(url, json=payload)
        if res.status_code in [200, 201]:
            db_id = res.json().get("id")
            logger.info(f"Registered 'SupportIQ Analytics DB' in Superset (ID: {db_id})")
            return db_id
        else:
            logger.warning(f"Database registration output: {res.status_code} - {res.text}")
            return None

    def register_dataset(self, db_id, table_name, schema="public"):
        url = f"{self.base_url}/api/v1/dataset/"
        payload = {
            "database": db_id,
            "schema": schema,
            "table_name": table_name
        }
        res = self.session.post(url, json=payload)
        if res.status_code in [200, 201]:
            ds_id = res.json().get("id")
            logger.info(f"Registered dataset '{table_name}' in Superset (ID: {ds_id})")
            return ds_id
        else:
            logger.info(f"Dataset '{table_name}' status: {res.status_code} - {res.text}")
            return None

def main():
    automator = SupersetAutomator()
    try:
        automator.authenticate()
        db_id = automator.register_database()
        if db_id:
            for table in ["fact_tickets", "v_executive_kpis", "v_agent_performance", "v_sla_risk_queue", "v_customer_issue_intelligence"]:
                automator.register_dataset(db_id, table)
            logger.info("All SupportIQ datasets registered successfully in Superset!")
    except Exception as e:
        logger.error(f"Superset automation error: {e}")

if __name__ == "__main__":
    main()
