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

### Production backups and health

`ops/backup-production.sh` saves a custom PostgreSQL dump, local uploaded media,
the release commit and checksums in `/home/deployer/backups/izihata`. Completed
daily snapshots older than 14 days are removed only after a new backup succeeds.
Supplier photos remain in Bunny Storage; this archive contains database references
and files from the server's media volume.

`ops/check-production.sh` checks container health, the public catalog and backup
freshness, and records dead outbox events. Changed results are sent to local syslog
under `izihata-health`; the current report is in
`/home/deployer/.local/state/izihata/health.txt`. Task health verifies a scheduled
heartbeat has actually run on a worker in the last three minutes.

The deployer's crontab runs backups daily at 02:30 UTC and checks every five minutes.
These copies remain on this server, as agreed. To restore, use an isolated empty
PostgreSQL database with the same major version: verify `SHA256SUMS`, run
`pg_restore --no-owner --no-acl --exit-on-error -d <isolated_database> database.dump`,
and extract `media.tar.gz` to a separate media directory. Compare product,
attribute and gallery counts before switching any application to that copy.

Responsive product image URLs are prepared behind `BUNNY_OPTIMIZER_ENABLED=true`
in `.env.production` (frontend build argument). Enable this only after Bunny
Optimizer is active on the product Pull Zone and a `?width=320` request actually
returns a smaller image. The default is `false`: the current CDN returns the
original unchanged when this option is inactive. Images from other hosts and
local uploads keep their original URLs.
