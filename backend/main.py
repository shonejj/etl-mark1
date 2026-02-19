"""FastAPI main application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from backend.core.config import settings
from backend.core.middleware import setup_middleware
from backend.core.rate_limiter import limiter
from backend.core.exceptions import ETLPlatformError

from backend.api.auth import router as auth_router
from backend.api.files import router as files_router
from backend.api.pipelines import router as pipelines_router
from backend.api.templates import router as templates_router
from backend.api.transforms import router as transforms_router
from backend.api.connectors import router as connectors_router
from backend.api.schedules import router as schedules_router
from backend.api.teams import router as teams_router
from backend.api.admin import router as admin_router
from backend.api.webhooks import router as webhooks_router

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("etl_platform")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("🚀 Starting ETL Platform API")
    # Ensure MinIO bucket exists
    try:
        from backend.services.file_service import file_service
        file_service.ensure_bucket()
        logger.info("✅ MinIO bucket ready")
    except Exception as e:
        logger.warning(f"⚠️  MinIO not available: {e}")

    # Redis check
    try:
        from backend.services.cache_service import cache_service
        if cache_service.health_check():
            logger.info("✅ Redis connected")
        else:
            logger.warning("⚠️  Redis not available")
    except Exception:
        logger.warning("⚠️  Redis not available")

    yield

    logger.info("🔻 Shutting down ETL Platform API")


app = FastAPI(
    title="ETL Platform API",
    description="Visual ETL Pipeline Automation Platform",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Middleware
setup_middleware(app)

# Rate limiting
app.state.limiter = limiter

# Exception handler for custom ETL errors
@app.exception_handler(ETLPlatformError)
async def etl_exception_handler(request: Request, exc: ETLPlatformError):
    return JSONResponse(
        status_code=400,
        content={"detail": exc.message},
    )

# Register routers
app.include_router(auth_router, prefix="/api")
app.include_router(files_router, prefix="/api")
app.include_router(pipelines_router, prefix="/api")
app.include_router(templates_router, prefix="/api")
app.include_router(transforms_router, prefix="/api")
app.include_router(connectors_router, prefix="/api")
app.include_router(schedules_router, prefix="/api")
app.include_router(teams_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(webhooks_router, prefix="/api")


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": "0.1.0",
        "docs": "/docs",
    }


@app.get("/api/health")
async def health():
    """Quick health check endpoint."""
    return {"status": "ok"}


# WebSocket endpoint for live pipeline updates
from fastapi import WebSocket, WebSocketDisconnect
import json as _json
import asyncio


class ConnectionManager:
    """WebSocket connection manager for live updates."""

    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, channel: str):
        await websocket.accept()
        if channel not in self.active_connections:
            self.active_connections[channel] = []
        self.active_connections[channel].append(websocket)

    def disconnect(self, websocket: WebSocket, channel: str):
        if channel in self.active_connections:
            self.active_connections[channel] = [
                ws for ws in self.active_connections[channel] if ws != websocket
            ]

    async def broadcast(self, channel: str, message: dict):
        if channel in self.active_connections:
            for ws in self.active_connections[channel]:
                try:
                    await ws.send_json(message)
                except Exception:
                    pass


ws_manager = ConnectionManager()


@app.websocket("/ws/runs/{run_id}")
async def websocket_run(websocket: WebSocket, run_id: int):
    """WebSocket endpoint for live pipeline run updates."""
    channel = f"run:{run_id}"
    await ws_manager.connect(websocket, channel)
    try:
        while True:
            # Keep alive — clients can send pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, channel)
