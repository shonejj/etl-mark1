"""ETL Platform CLI tool (etlctl)."""

import typer
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = typer.Typer(name="etlctl", help="ETL Platform CLI")
db_app = typer.Typer(help="Database management commands")
app.add_typer(db_app, name="db")


@db_app.command("create")
def db_create():
    """Create the MySQL database if it doesn't exist."""
    import pymysql
    from backend.core.config import settings

    # Parse connection URL to get host/user/pass
    # URL format: mysql+pymysql://user:pass@host:port/dbname
    parts = settings.MYSQL_URL.replace("mysql+pymysql://", "").split("/")
    db_name = parts[-1]
    auth_host = parts[0]
    user_pass, host_port = auth_host.split("@")
    user, password = user_pass.split(":")
    host, port = host_port.split(":")

    conn = pymysql.connect(host=host, port=int(port), user=user, password=password)
    try:
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        conn.commit()
        typer.echo(f"✅ Database '{db_name}' created (or already exists)")
    finally:
        conn.close()


@db_app.command("migrate")
def db_migrate():
    """Run Alembic migrations (auto-generate + upgrade)."""
    os.system("cd /home/hp/Documents/feb2026etl && source venv/bin/activate && alembic revision --autogenerate -m 'auto' 2>/dev/null; alembic upgrade head")
    typer.echo("✅ Migrations applied")


@db_app.command("seed")
def db_seed():
    """Seed roles, super-admin, and sample data."""
    from backend.db.session import SessionLocal
    from backend.db.seeds.seed_roles import seed_roles
    from backend.db.seeds.seed_super_admin import seed_super_admin
    from backend.db.seeds.seed_sample_data import seed_sample_data

    db = SessionLocal()
    try:
        seed_roles(db)
        seed_super_admin(db)
        seed_sample_data(db)
    finally:
        db.close()
    typer.echo("✅ All seeds applied")


@db_app.command("reset")
def db_reset():
    """Drop and recreate the database (DANGER)."""
    confirm = typer.confirm("⚠️  This will DROP the entire database. Continue?")
    if not confirm:
        raise typer.Abort()
    import pymysql
    from backend.core.config import settings

    parts = settings.MYSQL_URL.replace("mysql+pymysql://", "").split("/")
    db_name = parts[-1]
    auth_host = parts[0]
    user_pass, host_port = auth_host.split("@")
    user, password = user_pass.split(":")
    host, port = host_port.split(":")

    conn = pymysql.connect(host=host, port=int(port), user=user, password=password)
    try:
        cursor = conn.cursor()
        cursor.execute(f"DROP DATABASE IF EXISTS `{db_name}`")
        cursor.execute(f"CREATE DATABASE `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        conn.commit()
        typer.echo(f"✅ Database '{db_name}' reset")
    finally:
        conn.close()


@app.command("upload")
def upload_file(
    file_path: str = typer.Argument(..., help="Path to file to upload"),
    team_id: int = typer.Option(None, help="Team ID"),
):
    """Upload a file via the API."""
    import httpx
    with open(file_path, "rb") as f:
        resp = httpx.post(
            "http://localhost:8000/api/files/upload",
            files={"file": (os.path.basename(file_path), f)},
            params={"team_id": team_id} if team_id else {},
            headers={"Authorization": "Bearer <your-token>"},
            timeout=60,
        )
    typer.echo(resp.json())


@app.command("run")
def run_pipeline(
    pipeline_id: int = typer.Argument(..., help="Pipeline ID to execute"),
):
    """Trigger a pipeline run."""
    import httpx
    resp = httpx.post(
        f"http://localhost:8000/api/pipelines/{pipeline_id}/run",
        headers={"Authorization": "Bearer <your-token>"},
    )
    typer.echo(resp.json())


@app.command("list-pipelines")
def list_pipelines():
    """List all pipelines."""
    import httpx
    resp = httpx.get(
        "http://localhost:8000/api/pipelines/",
        headers={"Authorization": "Bearer <your-token>"},
    )
    data = resp.json()
    for p in data.get("pipelines", []):
        typer.echo(f"  [{p['id']}] {p['name']} (v{p['version']})")


@app.command("schedule")
def create_schedule(
    pipeline_id: int = typer.Argument(..., help="Pipeline ID"),
    cron: str = typer.Argument(..., help="Cron expression"),
):
    """Schedule a pipeline."""
    import httpx
    resp = httpx.post(
        "http://localhost:8000/api/schedules/",
        json={"pipeline_id": pipeline_id, "cron_expr": cron},
        headers={"Authorization": "Bearer <your-token>"},
    )
    typer.echo(resp.json())


@app.command("serve")
def serve(
    host: str = typer.Option("0.0.0.0", help="Host"),
    port: int = typer.Option(8000, help="Port"),
    reload: bool = typer.Option(True, help="Auto-reload"),
):
    """Start the FastAPI development server."""
    import uvicorn
    uvicorn.run("backend.main:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    app()
