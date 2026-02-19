# ETL Platform

A powerful, visual ETL (Extract, Transform, Load) Pipeline Automation Platform built with modern technologies.

## 🚀 Tech Stack

### Backend
- **Language:** Python 3.12+
- **Framework:** FastAPI
- **Database:** MySQL 8.0 (Async/Sync via SQLAlchemy)
- **Data Processing:** DuckDB (In-memory OLAP)
- **Task Queue:** Celery + Redis
- **Storage:** MinIO (S3 Compatible)
- **Authentication:** JWT (Access + Refresh Tokens)

### Frontend
- **Framework:** React 18 + TypeScript
- **Build Tool:** Vite
- **Styling:** Tailwind CSS + Shadcn UI
- **State Management:** Zustand
- **Networking:** Axios + React Query
- **Charts/Flow:** ReactFlow, Recharts

## 🛠️ Setup & Installation

### Prerequisites
- Python 3.12+
- Node.js 18+
- Docker & Docker Compose

### 1. Start Infrastructure (Database, Redis, MinIO)
```bash
docker-compose up -d
# OR specific services
docker-compose up -d mysql minio redis
```

### 2. Backend Setup
```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run Migrations
python -m backend.cli db migrate

# Seed Initial Data (Roles, Admin, Settings)
python -m backend.cli db seed

# Start API Server
export PYTHONPATH=$PYTHONPATH:.
python -m backend.cli serve --port 8000
```
API Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)

### 3. Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Start Development Server
npm run dev
```
Frontend URL: [http://localhost:5178](http://localhost:5178) (Port may vary)

## 🔑 Default Credentials

**Super Admin:**
- **Email:** `admin@example.com`
- **Password:** `admin123`

## 📂 Project Structure

- `backend/`: FastAPI application
  - `api/`: API endpoints (routers)
  - `core/`: Config, security, middleware
  - `models/`: SQLAlchemy database models
  - `schemas/`: Pydantic data schemas
  - `services/`: Business logic
  - `executor/`: Pipeline execution engine
- `frontend/`: React application
  - `src/components/`: Reusable UI components
  - `src/pages/`: Page views
  - `src/api/`: API integration
  - `src/context/`: Global state (Zustand)
