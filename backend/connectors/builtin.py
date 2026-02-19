"""Built-in connectors: CSV, JSON, HTTP, MySQL, Postgres."""

import os
import json
import tempfile
from typing import Dict, Any, Optional
import httpx
from backend.connectors.base import ConnectorBase


class CSVConnector(ConnectorBase):
    """Local CSV file connector."""

    connector_type = "csv"

    def __init__(self):
        self._path: Optional[str] = None

    def connect(self, config: Dict[str, Any]) -> None:
        self._path = config.get("path")

    def test_connection(self) -> bool:
        return self._path is not None and os.path.exists(self._path)

    def read_data(self, **kwargs) -> str:
        return self._path

    def write_data(self, data: Any, **kwargs) -> None:
        import duckdb
        conn = duckdb.connect(":memory:")
        output_path = kwargs.get("output_path", self._path)
        conn.execute(f"COPY (SELECT * FROM read_csv_auto('{data}')) TO '{output_path}' (FORMAT CSV, HEADER)")
        conn.close()


class JSONConnector(ConnectorBase):
    """Local JSON file connector."""

    connector_type = "json"

    def __init__(self):
        self._path: Optional[str] = None

    def connect(self, config: Dict[str, Any]) -> None:
        self._path = config.get("path")

    def test_connection(self) -> bool:
        return self._path is not None and os.path.exists(self._path)

    def read_data(self, **kwargs) -> str:
        return self._path

    def write_data(self, data: Any, **kwargs) -> None:
        import duckdb
        conn = duckdb.connect(":memory:")
        output_path = kwargs.get("output_path", self._path)
        conn.execute(f"COPY (SELECT * FROM read_json_auto('{data}')) TO '{output_path}' (FORMAT JSON)")
        conn.close()


class HTTPConnector(ConnectorBase):
    """HTTP/REST API connector for fetching data."""

    connector_type = "http"

    def __init__(self):
        self._url: Optional[str] = None
        self._method: str = "GET"
        self._headers: Dict[str, str] = {}
        self._auth_type: Optional[str] = None
        self._auth_config: Dict[str, str] = {}

    def connect(self, config: Dict[str, Any]) -> None:
        self._url = config["url"]
        self._method = config.get("method", "GET")
        self._headers = config.get("headers", {})
        self._auth_type = config.get("auth_type")
        self._auth_config = config.get("auth_config", {})

    def test_connection(self) -> bool:
        try:
            resp = httpx.request(
                self._method, self._url, headers=self._headers, timeout=10
            )
            return resp.status_code < 400
        except Exception:
            return False

    def read_data(self, **kwargs) -> str:
        """Fetch data from HTTP and save to temp file."""
        headers = {**self._headers}
        if self._auth_type == "bearer":
            headers["Authorization"] = f"Bearer {self._auth_config.get('token', '')}"
        elif self._auth_type == "api_key":
            key_name = self._auth_config.get("key_name", "X-API-Key")
            headers[key_name] = self._auth_config.get("key_value", "")

        resp = httpx.request(
            self._method,
            self._url,
            headers=headers,
            timeout=30,
            params=kwargs.get("params"),
        )
        resp.raise_for_status()

        # Determine format
        content_type = resp.headers.get("content-type", "")
        if "json" in content_type:
            ext = ".json"
        elif "csv" in content_type:
            ext = ".csv"
        elif "xml" in content_type:
            ext = ".xml"
        else:
            ext = ".json"

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
        tmp.write(resp.content)
        tmp.close()
        return tmp.name

    def write_data(self, data: Any, **kwargs) -> None:
        """POST data to the HTTP endpoint."""
        with open(data, "r") as f:
            content = f.read()
        httpx.post(self._url, content=content, headers=self._headers, timeout=30)


class MySQLConnector(ConnectorBase):
    """MySQL database connector using SQLAlchemy."""

    connector_type = "mysql"

    def __init__(self):
        self._connection_url: Optional[str] = None

    def connect(self, config: Dict[str, Any]) -> None:
        host = config.get("host", "localhost")
        port = config.get("port", 3306)
        user = config.get("user", "root")
        password = config.get("password", "")
        database = config.get("database", "")
        self._connection_url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"

    def test_connection(self) -> bool:
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(self._connection_url)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    def read_data(self, **kwargs) -> str:
        """Execute a query and save results to temp CSV."""
        from sqlalchemy import create_engine, text
        import csv
        query = kwargs.get("query", "SELECT 1")
        engine = create_engine(self._connection_url)
        with engine.connect() as conn:
            result = conn.execute(text(query))
            columns = list(result.keys())
            rows = result.fetchall()

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode="w", newline="")
        writer = csv.writer(tmp)
        writer.writerow(columns)
        for row in rows:
            writer.writerow(row)
        tmp.close()
        return tmp.name

    def write_data(self, data: Any, **kwargs) -> None:
        """Import CSV data into a MySQL table."""
        import duckdb
        table_name = kwargs.get("table_name", "import_data")
        conn = duckdb.connect(":memory:")
        conn.execute("INSTALL mysql; LOAD mysql;")
        conn.execute(f"ATTACH '{self._connection_url}' AS mysql_db (TYPE mysql)")
        conn.execute(f"CREATE OR REPLACE TABLE mysql_db.{table_name} AS SELECT * FROM read_csv_auto('{data}')")
        conn.close()


# Connector registry
CONNECTOR_REGISTRY: Dict[str, type] = {
    "csv": CSVConnector,
    "json": JSONConnector,
    "http": HTTPConnector,
    "mysql": MySQLConnector,
}


def get_connector(connector_type: str) -> ConnectorBase:
    """Get a connector instance by type."""
    cls = CONNECTOR_REGISTRY.get(connector_type)
    if not cls:
        raise ValueError(f"Unknown connector type: {connector_type}")
    return cls()
