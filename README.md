# IziHata

IziHata is a full-stack electrical goods store organized as two independent
applications in one repository:

- `backend/` — FastAPI, PostgreSQL, Redis/KeyDB, Taskiq, and Alembic;
- `frontend/` — React, Vite, TypeScript, and production Nginx.

The applications share only the versioned HTTP contract under `/api/v1`.
Business rules and authoritative pricing remain in the backend; the frontend
owns presentation and anonymous browser state.

The storefront includes public catalog section hubs, structured filtering,
product media/documents/reviews, an availability subscription, direct customer
accounts with B2B pricing, electrical calculators, and custom-board requests.
The staff panel moderates reviews, B2B companies, catalog items, orders, leads,
and board requests.

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

Run frontend checks with `npm run check`; end-to-end tests expect the full
stack at `http://localhost:3000` and are run with `npm run test:e2e`.

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

## Production deployment

Production uses `compose.production.yml`: Traefik is the only public service,
terminates TLS, redirects HTTP to HTTPS, serves the storefront, and sends
`/api` requests straight to FastAPI. PostgreSQL, KeyDB, Taskiq workers, and
the migration job are private to the Docker network.

```bash
cp .env.production.example .env.production
# Set all required values in .env.production, then:
docker compose -f compose.production.yml up --build -d
```

The production environment file contains credentials and is intentionally
ignored by Git. Keep database backups outside this server before treating a
deployment as recoverable.
