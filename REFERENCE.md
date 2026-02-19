# Developer Reference

## Common CLI Commands

### Backend

**Activate Environment:**
```bash
source venv/bin/activate
export PYTHONPATH=$PYTHONPATH:.
```

**Run Database Migrations:**
```bash
python -m backend.cli db migrate
```

**Create New Migration (Auto-generate):**
```bash
alembic revision --autogenerate -m "message"
```

**Seed Database:**
```bash
python -m backend.cli db seed
```

**Start API Server:**
```bash
python -m backend.cli serve --port 8000
```
*(Use `--reload` for auto-restart on changes)*

**Run Celery Worker:**
```bash
celery -A backend.tasks.celery_app worker --loglevel=info
```

**Run Tests:**
```bash
pytest
```

### Frontend

**Install Dependencies:**
```bash
cd frontend
npm install
```

**Start Dev Server:**
```bash
npm run dev
```

**Build for Production:**
```bash
npm run build
```

**Lint:**
```bash
npm run lint
```

## Directory Structure Reference

- **`backend/alembic/versions/`**: Database migration scripts.
- **`backend/api/`**: FastAPI routers (REST endpoints).
- **`backend/core/`**: Core configuration (`config.py`), security (`security.py`), middleware.
- **`backend/db/`**: Database session (`session.py`) and base model (`base.py`).
- **`backend/models/`**: SQLAlchemy ORM definitions.
- **`backend/schemas/`**: Pydantic models for request/response validation.
- **`backend/services/`**: Business logic layer (Controller).
- **`frontend/src/api/`**: Axios client setup and API integration functions.
- **`frontend/src/components/`**: Shared React components.
- **`frontend/src/context/`**: Global state management (Zustand stores).
- **`frontend/src/pages/`**: Main application views/routes.
- **`frontend/src/lib/`**: Utility functions (`cn`, helpers).

## Useful Links
- **API Docs (Swagger UI):** [http://localhost:8000/docs](http://localhost:8000/docs)
- **API Docs (ReDoc):** [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Frontend Local:** [http://localhost:5178](http://localhost:5178)
- **MinIO Console:** [http://localhost:9001](http://localhost:9001) (Default: minioadmin/minioadmin)
