import requests
import time
import logging
from config import Config

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("BaserowClient")

class BaserowClient:
    def __init__(self, base_url=None, email=None, password=None):
        self.base_url = (base_url or Config.BASEROW_URL).rstrip('/')
        self.email = email or Config.BASEROW_EMAIL
        self.password = password or Config.BASEROW_PASSWORD
        self.token = None
        self.workspace_id = None
        self.database_id = None
        self.tables = {}

    def authenticate(self):
        """Authenticate with Baserow and get JWT token, registering admin if necessary."""
        auth_url = f"{self.base_url}/api/user/token-auth/"
        payload = {"username": self.email, "password": self.password}
        
        try:
            res = requests.post(auth_url, json=payload, timeout=10)
            if res.status_code == 200:
                self.token = res.json()["token"]
                logger.info("Successfully authenticated with Baserow.")
                return self.token
        except Exception as e:
            logger.warning(f"Auth request failed: {e}")

        # If authentication failed, try registering initial admin user
        reg_url = f"{self.base_url}/api/user/"
        reg_payload = {
            "name": "SupportIQ Admin",
            "email": self.email,
            "password": self.password,
            "authenticate": True
        }
        try:
            res = requests.post(reg_url, json=reg_payload, timeout=10)
            if res.status_code in [200, 201, 204]:
                data = res.json()
                self.token = data.get("token")
                logger.info("Registered initial Baserow admin user successfully.")
                return self.token
            else:
                logger.error(f"Registration failed: {res.status_code} - {res.text}")
        except Exception as e:
            logger.error(f"Error during registration: {e}")

        # Try obtaining token once more
        try:
            res = requests.post(auth_url, json=payload, timeout=10)
            if res.status_code == 200:
                self.token = res.json()["token"]
                return self.token
        except Exception as e:
            logger.error(f"Failed to authenticate: {e}")

        raise RuntimeError("Could not authenticate or create user in Baserow.")

    def get_headers(self):
        if not self.token:
            self.authenticate()
        return {
            "Authorization": f"JWT {self.token}",
            "Content-Type": "application/json"
        }

    def get_or_create_workspace(self, name="SupportIQ Operations"):
        url = f"{self.base_url}/api/workspaces/"
        res = requests.get(url, headers=self.get_headers())
        if res.status_code == 200:
            workspaces = res.json()
            for ws in workspaces:
                if ws["name"] == name:
                    self.workspace_id = ws["id"]
                    logger.info(f"Found existing workspace '{name}' (ID: {self.workspace_id})")
                    return self.workspace_id

        # Create workspace
        res = requests.post(url, json={"name": name}, headers=self.get_headers())
        if res.status_code in [200, 201]:
            ws = res.json()
            self.workspace_id = ws["id"]
            logger.info(f"Created new workspace '{name}' (ID: {self.workspace_id})")
            return self.workspace_id
        else:
            raise RuntimeError(f"Failed to create workspace: {res.text}")

    def get_or_create_database(self, name=Config.BASEROW_DATABASE_NAME):
        if not self.workspace_id:
            self.get_or_create_workspace()
            
        url = f"{self.base_url}/api/applications/workspace/{self.workspace_id}/"
        res = requests.get(url, headers=self.get_headers())
        if res.status_code == 200:
            apps = res.json()
            for app in apps:
                if app["type"] == "database" and app["name"] == name:
                    self.database_id = app["id"]
                    logger.info(f"Found existing database '{name}' (ID: {self.database_id})")
                    return self.database_id

        # Create database application
        payload = {
            "name": name,
            "type": "database"
        }
        res = requests.post(url, json=payload, headers=self.get_headers())
        if res.status_code in [200, 201]:
            app = res.json()
            self.database_id = app["id"]
            logger.info(f"Created new database '{name}' (ID: {self.database_id})")
            return self.database_id
        else:
            raise RuntimeError(f"Failed to create database: {res.text}")

    def get_tables(self):
        if not self.database_id:
            self.get_or_create_database()
            
        url = f"{self.base_url}/api/database/tables/database/{self.database_id}/"
        res = requests.get(url, headers=self.get_headers())
        if res.status_code == 200:
            tables = res.json()
            for t in tables:
                self.tables[t["name"]] = t["id"]
            return self.tables
        return {}

    def create_table(self, name):
        if not self.database_id:
            self.get_or_create_database()

        existing = self.get_tables()
        if name in existing:
            return existing[name]

        url = f"{self.base_url}/api/database/tables/database/{self.database_id}/"
        res = requests.post(url, json={"name": name}, headers=self.get_headers())
        if res.status_code in [200, 201]:
            t = res.json()
            table_id = t["id"]
            self.tables[name] = table_id
            logger.info(f"Created table '{name}' (ID: {table_id})")
            return table_id
        else:
            raise RuntimeError(f"Failed to create table '{name}': {res.text}")

    def create_field(self, table_id, name, type_name="text", **kwargs):
        url = f"{self.base_url}/api/database/fields/table/{table_id}/"
        payload = {"name": name, "type": type_name, **kwargs}
        res = requests.post(url, json=payload, headers=self.get_headers())
        if res.status_code in [200, 201]:
            return res.json()
        else:
            logger.warning(f"Field creation '{name}' returned {res.status_code}: {res.text}")
            return None

    def get_rows(self, table_id, user_field_names=True):
        url = f"{self.base_url}/api/database/rows/table/{table_id}/?user_field_names={str(user_field_names).lower()}&size=200"
        all_rows = []
        while url:
            res = requests.get(url, headers=self.get_headers())
            if res.status_code == 200:
                data = res.json()
                all_rows.extend(data.get("results", []))
                url = data.get("next")
            else:
                logger.error(f"Error fetching rows: {res.status_code} - {res.text}")
                break
        return all_rows

    def batch_create_rows(self, table_id, rows, user_field_names=True):
        url = f"{self.base_url}/api/database/rows/table/{table_id}/batch/?user_field_names={str(user_field_names).lower()}"
        chunk_size = 200
        total_created = 0
        for i in range(0, len(rows), chunk_size):
            chunk = rows[i:i + chunk_size]
            payload = {"items": chunk}
            res = requests.post(url, json=payload, headers=self.get_headers())
            if res.status_code in [200, 201]:
                created = len(res.json().get("items", []))
                total_created += created
            else:
                logger.error(f"Batch insert error: {res.status_code} - {res.text}")
        logger.info(f"Inserted {total_created} rows into table {table_id}")
        return total_created


class MockBaserowClient:
    """Mock Baserow REST client for isolated offline unit testing."""
    def __init__(self):
        self.tables_data = {
            "Agents": [],
            "Customers": [],
            "Products": [],
            "Tickets": []
        }

    def seed_data(self, agents, customers, products, tickets):
        self.tables_data["Agents"] = agents
        self.tables_data["Customers"] = customers
        self.tables_data["Products"] = products
        self.tables_data["Tickets"] = tickets

    def get_tables(self):
        return {"Agents": 1, "Customers": 2, "Products": 3, "Tickets": 4}

    def get_rows(self, table_id, user_field_names=True):
        table_map = {1: "Agents", 2: "Customers", 3: "Products", 4: "Tickets"}
        name = table_map.get(table_id, "Tickets")
        return self.tables_data.get(name, [])
