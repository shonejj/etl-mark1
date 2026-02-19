"""Custom exception classes for the ETL platform."""

from fastapi import HTTPException, status


class ETLPlatformError(Exception):
    """Base exception for ETL Platform."""

    def __init__(self, message: str = "An error occurred"):
        self.message = message
        super().__init__(self.message)


class AuthenticationError(ETLPlatformError):
    """Raised when authentication fails."""
    pass


class AuthorizationError(ETLPlatformError):
    """Raised when user lacks permission."""
    pass


class ResourceNotFoundError(ETLPlatformError):
    """Raised when a requested resource is not found."""
    pass


class ResourceConflictError(ETLPlatformError):
    """Raised when a resource already exists."""
    pass


class ValidationError(ETLPlatformError):
    """Raised when input validation fails."""
    pass


class ConnectorError(ETLPlatformError):
    """Raised when a connector operation fails."""
    pass


class ExecutionError(ETLPlatformError):
    """Raised when pipeline execution fails."""
    pass


class StorageError(ETLPlatformError):
    """Raised when MinIO/storage operation fails."""
    pass


class QuotaExceededError(ETLPlatformError):
    """Raised when a quota/limit is exceeded."""
    pass


# HTTP exception shortcuts
def not_found(detail: str = "Resource not found") -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def forbidden(detail: str = "Insufficient permissions") -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def bad_request(detail: str = "Bad request") -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def unauthorized(detail: str = "Not authenticated") -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)
