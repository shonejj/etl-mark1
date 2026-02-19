# Project Roadmap & Plan

This document outlines the development plan and future roadmap for the ETL Platform.

## ✅ Completed Phases

### Phase 1: Foundation & Infrastructure
- [x] **Project Scaffolding**: Directory structure, Python/Node.js setup.
- [x] **Infrastructure**: Docker Compose for MySQL, Redis, MinIO.
- [x] **Database Design**: Initial schema for Users, Roles, Pipelines.
- [x] **Authentication**: JWT-based Auth, RBAC, Password Hashing.

### Phase 2: Frontend Setup
- [x] **Vite + React**: Project initialization.
- [x] **Styling**: Tailwind CSS + Shadcn UI configuration.
- [x] **Auth Flow**: Login, Register, Logout, Protected Routes.
- [x] **API Client**: Axios setup with interceptors.

## 🚧 Current Phase: Core Features

### Phase 3: Dashboard & Basic Management
- [ ] **Dashboard**: Widgets for pipeline stats, recent runs.
- [ ] **Data Sources**: UI to add/manage database and file connections.
- [ ] **File Manager**: Upload, list, and preview files from MinIO.

### Phase 4: Pipeline Builder
- [ ] **Visual Editor**: React Flow integration for drag-and-drop building.
- [ ] **Node Library**: Collection of nodes (Input, Transform, Output).
- [ ] **Configuration Panels**: Sidebars to configure node properties.

## 🔮 Future Roadmap

### Phase 5: Execution Engine (Advanced)
- [ ] **Live Monitoring**: WebSocket integration for real-time progress.
- [ ] **Smart Retries**: Conditional logic and retry policies.
- [ ] **Parallel Execution**: optimize Celery limits.

### Phase 6: Checkpoints & Resume
- [ ] **State persistence**: Save intermediate DuckDB states.
- [ ] **Resume**: Ability to restart failed pipelines from the last successful node.

### Phase 7: Advanced Adapters
- [ ] **CRM Connectors**: Salesforce, HubSpot integration.
- [ ] **ERP Connectors**: Odoo, SAP integration.
- [ ] **AI Transforms**: LLM-based text processing nodes.

## Reference Checklist

For a detailed task-by-task breakdown, check `task.md`.

## Contributing

1. **Pick a task** from `task.md`.
2. **Create a branch**: `feature/your-feature-name`.
3. **Commit changes**: conventional commits (e.g., `feat: add new connector`).
4. **Open a PR** for review.
