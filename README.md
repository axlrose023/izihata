# IziHata

IziHata is a full-stack electrical goods store organized as two independent
applications in one repository:

- `backend/` — FastAPI, PostgreSQL, Redis/KeyDB, Taskiq, and Alembic;
- `frontend/` — React, Vite, TypeScript, and production Nginx.

The applications share only the versioned HTTP contract under `/api/v1`.
Business rules and authoritative pricing remain in the backend; the frontend
owns presentation and anonymous browser state.

## Local development

Backend:

```bash
cd backend
cp .env.sample .env
uv sync --locked --dev
uv run cli bootstrap
uv run app
```

Frontend:

```bash
cd frontend
npm ci
npm run dev
```

The storefront is available at `http://localhost:3000`; Vite forwards its
same-origin `/api/v1` requests to `http://localhost:8000` by default.

See `backend/README.md` and `frontend/README.md` for application-specific
commands and architecture.

## Full stack with Docker

```bash
cp backend/.env.sample .env
docker compose up --build -d
docker compose exec app cli create-user
```

The storefront is served at `http://localhost:3000`; the API remains available
directly at `http://localhost:18000`. The optional observability profile exposes
Grafana at `http://localhost:3001`.
