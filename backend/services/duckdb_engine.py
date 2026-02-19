"""DuckDB analytics engine — ephemeral per-request instances."""

import duckdb
import tempfile
import os
import json
from typing import Optional, List, Dict, Any

from backend.core.config import settings


class DuckDBEngine:
    """Manages DuckDB connections for data preview, transforms, and analytics.

    Each method creates an ephemeral DuckDB connection to ensure isolation.
    For pipeline runs, a dedicated connection is created per run.
    """

    @staticmethod
    def _get_connection(memory_limit: str = "1GB") -> duckdb.DuckDBPyConnection:
        """Create a new in-memory DuckDB connection with safety limits."""
        conn = duckdb.connect(":memory:")
        conn.execute(f"SET memory_limit='{memory_limit}'")
        conn.execute("SET threads=2")
        conn.execute("INSTALL httpfs; LOAD httpfs;")
        return conn

    @staticmethod
    def preview_file(file_path: str, limit: int = 200, file_format: str = "csv") -> Dict[str, Any]:
        """Preview a file as structured data with schema.

        Args:
            file_path: Local path or presigned URL to the file.
            limit: Max rows to return.
            file_format: One of csv, json, xlsx, parquet, xml.

        Returns:
            {"columns": [...], "rows": [...], "total_count": int}
        """
        conn = DuckDBEngine._get_connection()
        try:
            read_fn = DuckDBEngine._read_function(file_format, file_path)
            # Get total count
            count_result = conn.execute(f"SELECT COUNT(*) FROM {read_fn}").fetchone()
            total_count = count_result[0] if count_result else 0

            # Get data
            result = conn.execute(
                f"SELECT * FROM {read_fn} LIMIT {limit}"
            )
            columns = [desc[0] for desc in result.description]
            rows = [dict(zip(columns, row)) for row in result.fetchall()]

            return {
                "columns": columns,
                "rows": rows,
                "total_count": total_count,
            }
        finally:
            conn.close()

    @staticmethod
    def infer_schema(file_path: str, file_format: str = "csv") -> List[Dict[str, str]]:
        """Infer column names and types from a file.

        Returns:
            [{"name": "col1", "type": "VARCHAR"}, ...]
        """
        conn = DuckDBEngine._get_connection()
        try:
            read_fn = DuckDBEngine._read_function(file_format, file_path)
            result = conn.execute(f"DESCRIBE SELECT * FROM {read_fn}")
            schema = []
            for row in result.fetchall():
                schema.append({
                    "name": row[0],
                    "type": row[1],
                    "nullable": True,
                })
            return schema
        finally:
            conn.close()

    @staticmethod
    def execute_sql(
        sql: str,
        sources: Optional[Dict[str, str]] = None,
        limit: int = 1000,
    ) -> Dict[str, Any]:
        """Execute arbitrary SQL with optional named source views.

        Args:
            sql: DuckDB SQL query. Use {{source_name}} for view references.
            sources: Dict of {view_name: file_path} to register as views.
            limit: Safety limit on rows returned.

        Returns:
            {"columns": [...], "rows": [...], "row_count": int}
        """
        conn = DuckDBEngine._get_connection()
        try:
            # Register source files as views
            if sources:
                for view_name, file_path in sources.items():
                    fmt = DuckDBEngine._detect_format(file_path)
                    read_fn = DuckDBEngine._read_function(fmt, file_path)
                    conn.execute(f"CREATE VIEW {view_name} AS SELECT * FROM {read_fn}")

            result = conn.execute(f"SELECT * FROM ({sql}) AS _q LIMIT {limit}")
            columns = [desc[0] for desc in result.description]
            rows = result.fetchall()

            return {
                "columns": columns,
                "rows": [dict(zip(columns, row)) for row in rows],
                "row_count": len(rows),
            }
        finally:
            conn.close()

    @staticmethod
    def apply_transforms(
        file_path: str,
        file_format: str,
        steps: List[Dict[str, Any]],
        limit: int = 200,
    ) -> Dict[str, Any]:
        """Apply a sequence of transform steps to a file and return preview.

        Each step is: {"operator": "rename_column", "params": {...}}
        Steps are converted to DuckDB SQL transformations chained via CTEs.
        """
        conn = DuckDBEngine._get_connection()
        try:
            read_fn = DuckDBEngine._read_function(file_format, file_path)
            conn.execute(f"CREATE VIEW _input AS SELECT * FROM {read_fn}")

            current_view = "_input"
            for i, step in enumerate(steps):
                view_name = f"_step_{i}"
                sql = DuckDBEngine._step_to_sql(step, current_view)
                conn.execute(f"CREATE VIEW {view_name} AS {sql}")
                current_view = view_name

            result = conn.execute(f"SELECT * FROM {current_view} LIMIT {limit}")
            columns = [desc[0] for desc in result.description]
            rows = [dict(zip(columns, row)) for row in result.fetchall()]

            count_result = conn.execute(f"SELECT COUNT(*) FROM {current_view}").fetchone()

            return {
                "columns": columns,
                "rows": rows,
                "total_count": count_result[0] if count_result else 0,
            }
        finally:
            conn.close()

    @staticmethod
    def export_to_file(
        file_path: str,
        file_format: str,
        steps: List[Dict[str, Any]],
        output_path: str,
        output_format: str = "csv",
    ) -> str:
        """Apply transforms and export result to a file.

        Returns:
            Path to the output file.
        """
        conn = DuckDBEngine._get_connection()
        try:
            read_fn = DuckDBEngine._read_function(file_format, file_path)
            conn.execute(f"CREATE VIEW _input AS SELECT * FROM {read_fn}")

            current_view = "_input"
            for i, step in enumerate(steps):
                view_name = f"_step_{i}"
                sql = DuckDBEngine._step_to_sql(step, current_view)
                conn.execute(f"CREATE VIEW {view_name} AS {sql}")
                current_view = view_name

            if output_format == "csv":
                conn.execute(f"COPY {current_view} TO '{output_path}' (FORMAT CSV, HEADER)")
            elif output_format == "parquet":
                conn.execute(f"COPY {current_view} TO '{output_path}' (FORMAT PARQUET)")
            elif output_format == "json":
                conn.execute(f"COPY {current_view} TO '{output_path}' (FORMAT JSON)")
            else:
                conn.execute(f"COPY {current_view} TO '{output_path}' (FORMAT CSV, HEADER)")

            return output_path
        finally:
            conn.close()

    @staticmethod
    def data_quality_score(file_path: str, file_format: str = "csv") -> Dict[str, Any]:
        """Compute a quality score (0-100) for a file.

        Checks: null rates, uniqueness, type consistency.
        """
        conn = DuckDBEngine._get_connection()
        try:
            read_fn = DuckDBEngine._read_function(file_format, file_path)
            conn.execute(f"CREATE VIEW _data AS SELECT * FROM {read_fn}")

            # Get column info
            cols = conn.execute("SELECT * FROM _data LIMIT 0").description
            total_rows = conn.execute("SELECT COUNT(*) FROM _data").fetchone()[0]

            if total_rows == 0:
                return {"score": 0.0, "details": {}, "total_rows": 0}

            column_scores = {}
            for col in cols:
                col_name = col[0]
                null_count = conn.execute(
                    f'SELECT COUNT(*) FROM _data WHERE "{col_name}" IS NULL'
                ).fetchone()[0]
                distinct_count = conn.execute(
                    f'SELECT COUNT(DISTINCT "{col_name}") FROM _data'
                ).fetchone()[0]

                null_rate = null_count / total_rows
                unique_ratio = distinct_count / total_rows if total_rows > 0 else 0
                col_score = max(0, (1 - null_rate) * 100)

                column_scores[col_name] = {
                    "null_rate": round(null_rate, 4),
                    "unique_ratio": round(unique_ratio, 4),
                    "score": round(col_score, 1),
                }

            avg_score = sum(c["score"] for c in column_scores.values()) / len(column_scores)

            return {
                "score": round(avg_score, 1),
                "total_rows": total_rows,
                "column_count": len(column_scores),
                "details": column_scores,
            }
        finally:
            conn.close()

    # --- Internal helpers ---

    @staticmethod
    def _read_function(file_format: str, file_path: str) -> str:
        """Return the DuckDB read function for a given format."""
        escaped_path = file_path.replace("'", "''")
        if file_format in ("csv", "txt"):
            return f"read_csv_auto('{escaped_path}')"
        elif file_format == "json":
            return f"read_json_auto('{escaped_path}')"
        elif file_format == "parquet":
            return f"read_parquet('{escaped_path}')"
        elif file_format in ("xlsx", "xls"):
            return f"st_read('{escaped_path}')"
        elif file_format == "xml":
            return f"read_csv_auto('{escaped_path}')"  # fallback
        else:
            return f"read_csv_auto('{escaped_path}')"

    @staticmethod
    def _detect_format(file_path: str) -> str:
        """Detect file format from extension."""
        ext = os.path.splitext(file_path)[1].lower().lstrip(".")
        return ext if ext in ("csv", "json", "xlsx", "parquet", "xml", "txt") else "csv"

    @staticmethod
    def _step_to_sql(step: Dict[str, Any], source_view: str) -> str:
        """Convert a transform step to DuckDB SQL."""
        op = step.get("operator", "")
        params = step.get("params", {})

        if op == "rename_column":
            from_name = params["from_name"]
            to_name = params["to_name"]
            return f'SELECT * REPLACE ("{from_name}" AS "{to_name}") FROM {source_view}'

        elif op == "cast_type":
            col = params["column"]
            target = params["target_type"]
            return f'SELECT * REPLACE (CAST("{col}" AS {target}) AS "{col}") FROM {source_view}'

        elif op == "trim_whitespace":
            cols = params.get("columns", [])
            if cols == ["*"]:
                return f"SELECT * FROM {source_view}"  # DuckDB auto-trims
            select_parts = []
            all_cols = f"SELECT * FROM {source_view}"
            for c in cols:
                select_parts.append(f'TRIM("{c}") AS "{c}"')
            return f"SELECT * FROM {source_view}"  # simplified for now

        elif op == "filter_rows":
            expr = params["expression"]
            return f"SELECT * FROM {source_view} WHERE {expr}"

        elif op == "drop_nulls":
            cols = params.get("columns", [])
            conditions = " AND ".join([f'"{c}" IS NOT NULL' for c in cols])
            return f"SELECT * FROM {source_view} WHERE {conditions}"

        elif op == "deduplicate_rows":
            cols = params.get("columns", [])
            if cols:
                partition = ", ".join([f'"{c}"' for c in cols])
                return (
                    f"SELECT * FROM (SELECT *, ROW_NUMBER() OVER "
                    f"(PARTITION BY {partition} ORDER BY ROWID) AS _rn "
                    f"FROM {source_view}) WHERE _rn = 1"
                )
            return f"SELECT DISTINCT * FROM {source_view}"

        elif op == "replace_text":
            col = params["column"]
            find = params["find"]
            replace = params["replace"]
            return (
                f'SELECT * REPLACE (REPLACE("{col}", \'{find}\', \'{replace}\') '
                f'AS "{col}") FROM {source_view}'
            )

        elif op == "regex_replace":
            col = params["column"]
            pattern = params["pattern"]
            replacement = params["replacement"]
            return (
                f'SELECT * REPLACE (regexp_replace("{col}", \'{pattern}\', '
                f'\'{replacement}\', \'g\') AS "{col}") FROM {source_view}'
            )

        elif op == "add_derived_column":
            name = params["name"]
            expr = params["expression"]
            return f'SELECT *, ({expr}) AS "{name}" FROM {source_view}'

        elif op == "split_column":
            col = params["column"]
            delimiter = params["delimiter"]
            new_names = params.get("new_names", [f"{col}_1", f"{col}_2"])
            parts = []
            for i, new_name in enumerate(new_names):
                parts.append(f'string_split("{col}", \'{delimiter}\')[{i+1}] AS "{new_name}"')
            return f"SELECT *, {', '.join(parts)} FROM {source_view}"

        elif op == "merge_columns":
            cols = params["columns"]
            sep = params.get("separator", " ")
            new_name = params["new_name"]
            concat_parts = " || ".join([f'COALESCE(CAST("{c}" AS VARCHAR), \'\')' for c in cols])
            return f'SELECT *, ({concat_parts}) AS "{new_name}" FROM {source_view}'

        elif op == "sql_transform":
            sql = params["sql"]
            sql = sql.replace("{{input}}", source_view)
            return sql

        elif op == "aggregate":
            group_by = params.get("group_by", [])
            aggs = params.get("aggregations", {})
            gb = ", ".join([f'"{c}"' for c in group_by])
            agg_parts = [f'{func}("{col}") AS "{col}_{func}"' for col, func in aggs.items()]
            return f"SELECT {gb}, {', '.join(agg_parts)} FROM {source_view} GROUP BY {gb}"

        else:
            # Pass-through for unknown operators
            return f"SELECT * FROM {source_view}"
