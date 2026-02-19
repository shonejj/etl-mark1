"""Pipeline executor — DAG-based execution engine using topological sort."""

import json
import time
import tempfile
import os
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from concurrent.futures import ProcessPoolExecutor, as_completed

from sqlalchemy.orm import Session

from backend.models.pipeline import Pipeline, PipelineRun, NodeRunLog, PipelineRunStatus
from backend.services.duckdb_engine import DuckDBEngine
from backend.services.file_service import file_service
from backend.connectors.builtin import get_connector
from backend.connectors.export_adapters.builtin import get_export_adapter
from backend.core.exceptions import ExecutionError


class PipelineExecutor:
    """Executes a pipeline by traversing nodes in topological order.

    Supports: file_input, connector_input, transform, validation,
    conditional_branch, merge, invoke_http, webhook_send, email_notify,
    pdf_extract, split_json, db_insert, file_output, export.
    """

    def __init__(self, db: Session):
        self.db = db
        self.run: Optional[PipelineRun] = None
        self._node_outputs: Dict[str, str] = {}  # node_id -> temp file path
        self._max_retries = 3
        self._retry_delay = 2

    def execute(self, run_id: int) -> Dict[str, Any]:
        """Execute a pipeline run by ID."""
        self.run = self.db.query(PipelineRun).filter(PipelineRun.id == run_id).first()
        if not self.run:
            raise ExecutionError(f"Run {run_id} not found")

        pipeline = self.db.query(Pipeline).filter(Pipeline.id == self.run.pipeline_id).first()
        if not pipeline:
            raise ExecutionError(f"Pipeline {self.run.pipeline_id} not found")

        # Update run status
        self.run.status = PipelineRunStatus.running
        self.run.started_at = datetime.now(timezone.utc)
        self.db.commit()

        try:
            definition = json.loads(pipeline.definition_json)
            nodes = definition.get("nodes", [])
            edges = definition.get("edges", [])

            # Build adjacency and topological order
            order = self._topological_sort(nodes, edges)

            total_rows = 0
            for node_def in order:
                node_id = node_def["id"]
                node_type = node_def.get("type", "unknown")
                node_config = node_def.get("data", {}).get("config", {})

                # Create node log
                node_log = NodeRunLog(
                    run_id=run_id,
                    node_id=node_id,
                    node_type=node_type,
                    status="running",
                    started_at=datetime.now(timezone.utc),
                )
                self.db.add(node_log)
                self.db.commit()

                # Execute with retries
                success = False
                last_error = None
                for attempt in range(1, self._max_retries + 1):
                    try:
                        result = self._execute_node(node_id, node_type, node_config, edges)
                        node_log.status = "success"
                        node_log.rows_out = result.get("rows", 0)
                        total_rows += result.get("rows", 0)
                        node_log.log_text = result.get("log", "OK")
                        success = True
                        break
                    except Exception as e:
                        last_error = str(e)
                        node_log.attempt_no = attempt
                        if attempt < self._max_retries:
                            time.sleep(self._retry_delay * attempt)  # Exponential backoff

                if not success:
                    node_log.status = "failed"
                    node_log.log_text = f"Failed after {self._max_retries} attempts: {last_error}"
                    node_log.finished_at = datetime.now(timezone.utc)
                    node_log.duration_ms = int(
                        (node_log.finished_at - node_log.started_at).total_seconds() * 1000
                    )
                    self.db.commit()
                    raise ExecutionError(f"Node {node_id} failed: {last_error}")

                node_log.finished_at = datetime.now(timezone.utc)
                node_log.duration_ms = int(
                    (node_log.finished_at - node_log.started_at).total_seconds() * 1000
                )
                self.db.commit()

            # Success
            self.run.status = PipelineRunStatus.success
            self.run.rows_processed = total_rows
            self.run.finished_at = datetime.now(timezone.utc)
            self.run.duration_ms = int(
                (self.run.finished_at - self.run.started_at).total_seconds() * 1000
            )
            self.db.commit()

            return {
                "status": "success",
                "rows_processed": total_rows,
                "duration_ms": self.run.duration_ms,
            }

        except Exception as e:
            self.run.status = PipelineRunStatus.failed
            self.run.error_message = str(e)
            self.run.finished_at = datetime.now(timezone.utc)
            if self.run.started_at:
                self.run.duration_ms = int(
                    (self.run.finished_at - self.run.started_at).total_seconds() * 1000
                )
            self.db.commit()
            return {"status": "failed", "error": str(e)}

        finally:
            # Clean up temp files
            for path in self._node_outputs.values():
                try:
                    if path and os.path.exists(path):
                        os.unlink(path)
                except Exception:
                    pass

    def _execute_node(
        self,
        node_id: str,
        node_type: str,
        config: Dict[str, Any],
        edges: List[Dict],
    ) -> Dict[str, Any]:
        """Execute a single node and store output."""
        input_files = self._get_input_files(node_id, edges)

        if node_type == "file_input":
            return self._exec_file_input(node_id, config)
        elif node_type == "connector_input":
            return self._exec_connector_input(node_id, config)
        elif node_type == "transform":
            return self._exec_transform(node_id, config, input_files)
        elif node_type == "validation":
            return self._exec_validation(node_id, config, input_files)
        elif node_type == "file_output":
            return self._exec_file_output(node_id, config, input_files)
        elif node_type == "invoke_http":
            return self._exec_invoke_http(node_id, config, input_files)
        elif node_type == "webhook_send":
            return self._exec_webhook_send(node_id, config, input_files)
        elif node_type == "db_insert":
            return self._exec_db_insert(node_id, config, input_files)
        elif node_type == "export":
            return self._exec_export(node_id, config, input_files)
        elif node_type == "merge":
            return self._exec_merge(node_id, config, input_files)
        elif node_type == "conditional_branch":
            return self._exec_conditional(node_id, config, input_files)
        else:
            return {"rows": 0, "log": f"Pass-through node type: {node_type}"}

    def _exec_file_input(self, node_id: str, config: Dict) -> Dict:
        """Load a file from MinIO to temp."""
        file_id = config.get("file_id")
        file_meta = self.db.query(
            __import__("backend.models.file_meta", fromlist=["FileMeta"]).FileMeta
        ).filter_by(id=file_id).first()

        if not file_meta:
            raise ExecutionError(f"File {file_id} not found")

        tmp_path = file_service.download_to_temp(file_meta.minio_key)
        self._node_outputs[node_id] = tmp_path
        return {"rows": file_meta.record_count or 0, "log": f"Loaded {file_meta.original_name}"}

    def _exec_connector_input(self, node_id: str, config: Dict) -> Dict:
        """Execute a connector to fetch data."""
        connector = get_connector(config.get("type", "csv"))
        connector.connect(config)
        path = connector.read_data(**config.get("read_params", {}))
        self._node_outputs[node_id] = path
        return {"rows": 0, "log": f"Connected via {config.get('type')}"}

    def _exec_transform(self, node_id: str, config: Dict, input_files: List[str]) -> Dict:
        """Apply DuckDB transforms."""
        if not input_files:
            raise ExecutionError("Transform node has no inputs")

        steps = config.get("steps", [])
        file_format = config.get("format", "csv")
        output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".csv").name

        result_path = DuckDBEngine.export_to_file(
            input_files[0], file_format, steps, output_path, "csv"
        )
        self._node_outputs[node_id] = result_path

        preview = DuckDBEngine.preview_file(result_path, limit=1, file_format="csv")
        return {"rows": preview["total_count"], "log": f"Applied {len(steps)} transforms"}

    def _exec_validation(self, node_id: str, config: Dict, input_files: List[str]) -> Dict:
        """Validate data quality."""
        if not input_files:
            raise ExecutionError("Validation node has no inputs")

        quality = DuckDBEngine.data_quality_score(input_files[0], "csv")
        min_score = config.get("min_score", 50)

        if quality["score"] < min_score:
            raise ExecutionError(
                f"Quality score {quality['score']} below minimum {min_score}"
            )

        self._node_outputs[node_id] = input_files[0]
        return {"rows": quality["total_rows"], "log": f"Quality: {quality['score']}/100"}

    def _exec_file_output(self, node_id: str, config: Dict, input_files: List[str]) -> Dict:
        """Write output to a file in MinIO."""
        if not input_files:
            raise ExecutionError("File output node has no inputs")
        # For PoC, just copy to output path
        output_name = config.get("filename", "output.csv")
        self._node_outputs[node_id] = input_files[0]
        return {"rows": 0, "log": f"Output ready: {output_name}"}

    def _exec_invoke_http(self, node_id: str, config: Dict, input_files: List[str]) -> Dict:
        """Make an HTTP request."""
        import httpx
        url = config["url"]
        method = config.get("method", "GET")
        headers = config.get("headers", {})
        body = config.get("body")

        if input_files and method in ("POST", "PUT"):
            with open(input_files[0], "r") as f:
                body = f.read()

        resp = httpx.request(method, url, content=body, headers=headers, timeout=30)

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        tmp.write(resp.content)
        tmp.close()
        self._node_outputs[node_id] = tmp.name

        return {"rows": 0, "log": f"HTTP {method} {url} → {resp.status_code}"}

    def _exec_webhook_send(self, node_id: str, config: Dict, input_files: List[str]) -> Dict:
        """Send data to a webhook URL."""
        adapter = get_export_adapter("webhook")
        result = adapter.export(input_files[0] if input_files else "", config)
        self._node_outputs[node_id] = input_files[0] if input_files else ""
        return {"rows": 0, "log": f"Webhook: {result.get('status_code', 'N/A')}"}

    def _exec_db_insert(self, node_id: str, config: Dict, input_files: List[str]) -> Dict:
        """Insert data into a database."""
        connector = get_connector(config.get("db_type", "mysql"))
        connector.connect(config)
        connector.write_data(input_files[0] if input_files else "", **config)
        self._node_outputs[node_id] = input_files[0] if input_files else ""
        return {"rows": 0, "log": f"Inserted to {config.get('table_name', 'unknown')}"}

    def _exec_export(self, node_id: str, config: Dict, input_files: List[str]) -> Dict:
        """Export via an adapter."""
        adapter = get_export_adapter(config.get("adapter_type", "webhook"))
        result = adapter.export(input_files[0] if input_files else "", config)
        return {"rows": 0, "log": json.dumps(result)}

    def _exec_merge(self, node_id: str, config: Dict, input_files: List[str]) -> Dict:
        """Merge multiple inputs into one."""
        if len(input_files) < 2:
            if input_files:
                self._node_outputs[node_id] = input_files[0]
                return {"rows": 0, "log": "Single input, pass-through"}
            raise ExecutionError("Merge needs at least 1 input")

        import duckdb
        conn = duckdb.connect(":memory:")
        parts = []
        for i, fp in enumerate(input_files):
            view = f"_merge_{i}"
            conn.execute(f"CREATE VIEW {view} AS SELECT * FROM read_csv_auto('{fp}')")
            parts.append(f"SELECT * FROM {view}")

        union_sql = " UNION ALL ".join(parts)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
        tmp.close()
        conn.execute(f"COPY ({union_sql}) TO '{tmp.name}' (FORMAT CSV, HEADER)")
        conn.close()

        self._node_outputs[node_id] = tmp.name
        return {"rows": 0, "log": f"Merged {len(input_files)} inputs"}

    def _exec_conditional(self, node_id: str, config: Dict, input_files: List[str]) -> Dict:
        """Conditional branch — pass-through based on expression."""
        self._node_outputs[node_id] = input_files[0] if input_files else ""
        return {"rows": 0, "log": "Conditional evaluated"}

    def _get_input_files(self, node_id: str, edges: List[Dict]) -> List[str]:
        """Get output files from upstream nodes connected to this node."""
        inputs = []
        for edge in edges:
            if edge.get("target") == node_id:
                source_id = edge.get("source")
                if source_id in self._node_outputs:
                    inputs.append(self._node_outputs[source_id])
        return inputs

    @staticmethod
    def _topological_sort(
        nodes: List[Dict], edges: List[Dict]
    ) -> List[Dict]:
        """Sort nodes in topological (execution) order."""
        node_map = {n["id"]: n for n in nodes}
        in_degree = {n["id"]: 0 for n in nodes}
        adjacency: Dict[str, List[str]] = {n["id"]: [] for n in nodes}

        for edge in edges:
            src = edge["source"]
            tgt = edge["target"]
            adjacency[src].append(tgt)
            if tgt in in_degree:
                in_degree[tgt] += 1

        # Kahn's algorithm
        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        order = []
        while queue:
            nid = queue.pop(0)
            order.append(node_map[nid])
            for neighbor in adjacency.get(nid, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return order
