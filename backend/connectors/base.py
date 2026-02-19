"""Abstract base classes for connectors and operators."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class ConnectorBase(ABC):
    """Base class for all input/output connectors.

    Subclasses must implement connect, test_connection, read_data, and write_data.
    """

    @abstractmethod
    def connect(self, config: Dict[str, Any]) -> None:
        """Initialize the connection with config."""
        ...

    @abstractmethod
    def test_connection(self) -> bool:
        """Test if the connection is valid."""
        ...

    @abstractmethod
    def read_data(self, **kwargs) -> Any:
        """Read data from the source and return as file path or DataFrame."""
        ...

    @abstractmethod
    def write_data(self, data: Any, **kwargs) -> None:
        """Write data to the destination."""
        ...

    @property
    @abstractmethod
    def connector_type(self) -> str:
        """Return the connector type identifier (e.g., 'csv', 'postgres')."""
        ...


class TransformOperatorBase(ABC):
    """Base class for all transform operators.

    Subclasses must implement apply and describe.
    """

    @abstractmethod
    def apply(self, duckdb_conn: Any, source_view: str, params: Dict[str, Any]) -> str:
        """Apply the transformation and return the name of the result view.

        Args:
            duckdb_conn: Active DuckDB connection.
            source_view: Name of the input view/table.
            params: Operator-specific parameters.

        Returns:
            Name of the output view created by this transform.
        """
        ...

    @property
    @abstractmethod
    def operator_name(self) -> str:
        """Return the operator identifier (e.g., 'rename_column')."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of the operator."""
        ...

    def validate_params(self, params: Dict[str, Any]) -> bool:
        """Optional: validate params before apply. Override in subclasses."""
        return True


class ExportAdapterBase(ABC):
    """Base class for export adapters (webhook, Odoo XML-RPC, etc.)."""

    @abstractmethod
    def export(self, data_path: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Export data from a file path to the target system.

        Returns:
            Dict with export result metadata.
        """
        ...

    @property
    @abstractmethod
    def adapter_type(self) -> str:
        """Return the adapter type (e.g., 'webhook', 'odoo_xmlrpc')."""
        ...


class PipelineExecutorBase(ABC):
    """Base class for pipeline execution strategies."""

    @abstractmethod
    def execute(self, pipeline_def: Dict[str, Any], run_id: int) -> Dict[str, Any]:
        """Execute a full pipeline.

        Args:
            pipeline_def: JSON pipeline definition with nodes/edges.
            run_id: ID of the PipelineRun record.

        Returns:
            Execution summary dict.
        """
        ...
