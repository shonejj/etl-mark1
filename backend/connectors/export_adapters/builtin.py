"""Export adapters: Webhook, Odoo XML-RPC."""

import json
import xmlrpc.client
from typing import Dict, Any

import httpx

from backend.connectors.base import ExportAdapterBase


class WebhookExportAdapter(ExportAdapterBase):
    """Export data by POSTing to a webhook URL."""

    adapter_type = "webhook"

    def export(self, data_path: str, config: Dict[str, Any]) -> Dict[str, Any]:
        url = config["url"]
        headers = config.get("headers", {"Content-Type": "application/json"})

        # Read data
        with open(data_path, "r") as f:
            content = f.read()

        # Try to parse as JSON, fallback to raw
        try:
            payload = json.loads(content)
        except json.JSONDecodeError:
            payload = {"data": content}

        resp = httpx.post(
            url,
            json=payload if isinstance(payload, (dict, list)) else {"data": payload},
            headers=headers,
            timeout=30,
        )

        return {
            "status_code": resp.status_code,
            "response_body": resp.text[:500],
            "success": resp.status_code < 400,
        }


class OdooXMLRPCExportAdapter(ExportAdapterBase):
    """Export data to Odoo via XML-RPC."""

    adapter_type = "odoo_xmlrpc"

    def export(self, data_path: str, config: Dict[str, Any]) -> Dict[str, Any]:
        url = config["url"]  # e.g. "https://my-odoo.com"
        db = config["db"]
        username = config["username"]
        password = config["password"]
        model = config["model"]  # e.g. "product.product"
        method = config.get("method", "create")

        # Authenticate
        common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
        uid = common.authenticate(db, username, password, {})
        if not uid:
            return {"success": False, "error": "Authentication failed"}

        models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")

        # Read data from file
        with open(data_path, "r") as f:
            content = f.read()

        try:
            records = json.loads(content)
            if isinstance(records, dict):
                records = [records]
        except json.JSONDecodeError:
            return {"success": False, "error": "Data file is not valid JSON"}

        # Send records
        created_ids = []
        errors = []
        for record in records:
            try:
                result = models.execute_kw(
                    db, uid, password, model, method, [record]
                )
                created_ids.append(result)
            except Exception as e:
                errors.append(str(e))

        return {
            "success": len(errors) == 0,
            "created_ids": created_ids,
            "errors": errors,
            "total": len(records),
        }


# Export adapter registry
EXPORT_ADAPTER_REGISTRY: Dict[str, type] = {
    "webhook": WebhookExportAdapter,
    "odoo_xmlrpc": OdooXMLRPCExportAdapter,
}


def get_export_adapter(adapter_type: str) -> ExportAdapterBase:
    cls = EXPORT_ADAPTER_REGISTRY.get(adapter_type)
    if not cls:
        raise ValueError(f"Unknown export adapter: {adapter_type}")
    return cls()
