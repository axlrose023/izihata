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

### Category filters

The curated keys in `backend/src/app/database/seed/category_filters.json` come
from existing supplier specifications. Configure them after importing products:

```bash
docker compose --env-file .env.production -f compose.production.yml exec -T app cli configure-catalog-filters
# Review the dry run, then apply:
docker compose --env-file .env.production -f compose.production.yml exec -T app cli configure-catalog-filters --apply
```

This adds only observed keys to the existing `CatalogAttribute` and
`CategoryAttribute` tables. It preserves existing definitions and assignments,
is safe to repeat, and does not modify products, specification values or media.
Configured categories expose their active, filterable definitions; unconfigured
categories keep the paginated fallback. Old links to other specifications still
filter products. Manufacturer codes remain in product details and SKU search.
Filter definitions do not forbid free-form supplier fields in the editor;
explicit required fields and numeric definitions still validate their values.

### Concurrent catalog check

Run the bounded public HTTP scenario in the deployed backend environment:

```bash
docker compose --env-file .env.production -f compose.production.yml exec -T app python -m cli.catalog_load --base-url https://izihata.com.ua --output /tmp/catalog-load.json
docker compose --env-file .env.production -f compose.production.yml cp app:/tmp/catalog-load.json /tmp/catalog-load.json
```

The default is 55 requests per stage with 1, 5, 10 and 20 concurrent requests.
It covers the grid, largest category, search, SKU lookup, basic and specification
filters, product details, category references, homepage HTML and a basket quote.
Responses use the application's existing schemas. Quotes do not create orders.
The report includes latency percentiles, throughput, statuses and validation
errors per stage and route. A failed response stops new requests; there are no
retries. The request budget leaves room below the catalog and quote rate limits.
Wait at least 60 seconds between runs to avoid sharing their per-IP quota.

This is a short concurrency check, not a capacity ceiling or a full browser test:
it does not simulate user think time, image downloads or external delivery calls.

Production check on 2026-10-02, application release `a71f032`, 23,736 products:

| Concurrent requests | Completed | p50 | p95 | Maximum | Requests/s |
| --- | --- | --- | --- | --- | --- |
| 1 | 55 | 90 ms | 169 ms | 191 ms | 10.36 |
| 5 | 55 | 100 ms | 314 ms | 398 ms | 42.94 |
| 10 | 55 | 159 ms | 441 ms | 568 ms | 49.24 |
| 20 | 55 | 221 ms | 514 ms | 613 ms | 67.44 |

All 220 measured responses returned HTTP 200 and passed schema validation.
No timeouts or rate-limit responses occurred. All six application services were
healthy before and after the run. These are short bursts with a warmed client;
each route has only five samples per stage, so its percentile is not a long-term
service guarantee.

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

Generated product images use WebP copies in the existing Bunny Storage bucket.
Run `cli image-variants --concurrency 2` in the application container after a
supplier import. The command resumes from stored metadata and preserves original
URLs, gallery order, transparency and aspect ratio. `--limit 1` processes a sample.
It uses the same `BUNNY_*` storage credentials as supplier imports and does not
require Bunny Image Optimizer. Failed conversions keep the original image and
are reported for retry. Metadata is ignored automatically if an original URL is
changed. Conversion uses [Pillow](https://pillow.readthedocs.io/en/stable/reference/Image.html).
