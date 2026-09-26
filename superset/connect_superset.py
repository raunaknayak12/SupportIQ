import requests
import json
import logging
import os

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("SupersetAutoConnect")

SUPERSET_URL = os.getenv("SUPERSET_URL", "http://localhost:8088").rstrip('/')
SUPERSET_USERNAME = os.getenv("SUPERSET_ADMIN_USER", "admin")
SUPERSET_PASSWORD = os.getenv("SUPERSET_ADMIN_PASS", "admin")

class SupersetAutomation:
    def __init__(self, base_url=SUPERSET_URL, username=SUPERSET_USERNAME, password=SUPERSET_PASSWORD):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.access_token = None
        self.csrf_token = None

    def authenticate(self):
        login_url = f"{self.base_url}/api/v1/security/login"
        payload = {
            "username": self.username,
            "password": self.password,
            "provider": "db",
            "refresh": True
        }
        res = self.session.post(login_url, json=payload, timeout=10)
        if res.status_code == 200:
            self.access_token = res.json()["access_token"]
            self.session.headers.update({
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            })
            logger.info("Successfully authenticated with Superset REST API.")
            self.get_csrf_token()
            return True
        else:
            logger.error(f"Superset authentication failed: {res.status_code} - {res.text}")
            return False

    def get_csrf_token(self):
        url = f"{self.base_url}/api/v1/security/csrf_token/"
        res = self.session.get(url, timeout=10)
        if res.status_code == 200:
            self.csrf_token = res.json()["result"]
            self.session.headers.update({"X-CSRFToken": self.csrf_token})
            return self.csrf_token
        return None

    def get_or_create_database(self, database_name="SupportIQ Analytics DB", sqlalchemy_uri="postgresql+psycopg2://supportiq:supportiq_pass@supportiq_postgres:5432/supportiq_analytics"):
        url = f"{self.base_url}/api/v1/database/"
        res = self.session.get(url)
        if res.status_code == 200:
            databases = res.json().get("result", [])
            for db in databases:
                if db["database_name"] == database_name:
                    logger.info(f"Found existing Superset database '{database_name}' (ID: {db['id']})")
                    return db["id"]

        # Create database connection
        payload = {
            "database_name": database_name,
            "sqlalchemy_uri": sqlalchemy_uri,
            "expose_in_sqllab": True,
            "allow_run_async": False,
            "allow_ctas": True,
            "allow_cvas": True,
            "allow_dml": False,
            "allow_file_upload": True
        }
        res = self.session.post(url, json=payload)
        if res.status_code in [200, 201]:
            db_id = res.json()["id"]
            logger.info(f"Successfully registered Superset database '{database_name}' (ID: {db_id})")
            return db_id
        else:
            logger.error(f"Failed to create Superset database connection: {res.status_code} - {res.text}")
            return None

    def register_dataset(self, db_id, table_name, schema="public"):
        url = f"{self.base_url}/api/v1/dataset/"
        res = self.session.get(f"{url}?q=(filters:[(col:table_name,opr:eq,value:'{table_name}')])")
        if res.status_code == 200 and res.json().get("count", 0) > 0:
            ds_id = res.json()["result"][0]["id"]
            logger.info(f"Dataset '{table_name}' already registered (ID: {ds_id})")
            return ds_id

        payload = {
            "database": db_id,
            "schema": schema,
            "table_name": table_name
        }
        res = self.session.post(url, json=payload)
        if res.status_code in [200, 201]:
            ds_id = res.json()["id"]
            logger.info(f"Registered Superset dataset '{table_name}' (ID: {ds_id})")
            return ds_id
        else:
            logger.warning(f"Dataset registration response for '{table_name}': {res.status_code} - {res.text}")
            return None

def auto_setup_superset():
    auto = SupersetAutomation()
    if auto.authenticate():
        db_id = auto.get_or_create_database()
        if db_id:
            datasets = [
                "fact_tickets", "v_executive_kpis", "v_agent_performance",
                "v_sla_risk_queue", "v_customer_issue_intelligence"
            ]
            for ds in datasets:
                auto.register_dataset(db_id, ds)
            logger.info("All Superset datasets registered successfully!")

if __name__ == "__main__":
    auto_setup_superset()
