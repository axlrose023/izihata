# IziHata API

Production-oriented FastAPI backend for the IziHata electrical goods store. The
project is based on `base_project_template` and keeps its modular API, unit of
work, Dishka dependency injection, Alembic, Taskiq, Docker, and monitoring
structure.

The reference React prototype was used only to derive the domain and API. Its
18 categories, complete subcategory tree, and expanded initial product catalog
are available as an idempotent database seed.

## Scope

The current backend implements only flows present in the reference product:

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Container liveness probe |
| `GET` | `/ready` | PostgreSQL and Redis readiness probe |
| `POST` | `/api/v1/auth/login` | Staff authentication |
| `POST` | `/api/v1/auth/refresh` | Refresh staff token pair |
| `POST` | `/api/v1/auth/logout` | Revoke a staff refresh session |
| `GET` | `/api/v1/catalog/categories` | Category tree with product counts |
| `GET` | `/api/v1/catalog/products` | Paginated search, filters, sorting, and facets |
| `GET` | `/api/v1/catalog/products/{slug}` | Product details |
| `GET` | `/api/v1/delivery/cities` | Nova Poshta settlement suggestions |
| `GET` | `/api/v1/delivery/points` | Nova Poshta branch or locker suggestions |
| `POST` | `/api/v1/checkout/quote` | Authoritative cart and promotion calculation |
| `POST` | `/api/v1/orders` | Idempotent guest checkout |
| `POST` | `/api/v1/leads` | Callback, quick-buy, or wholesale lead |
| `GET` | `/api/v1/admin/dashboard` | Real operational aggregates |
| `POST` | `/api/v1/admin/catalog/products` | Validated product creation |
| `PATCH` | `/api/v1/admin/catalog/products/{id}` | Validated product details and availability update |
| `GET` | `/api/v1/admin/orders` | Paginated order management list |
| `PATCH` | `/api/v1/admin/orders/{id}/status` | Validated order status transition |
| `GET` | `/api/v1/admin/leads` | Paginated and filtered lead queue |
| `PATCH` | `/api/v1/admin/leads/{id}/status` | Validated lead status transition |

Swagger UI is available at `/docs`; the OpenAPI document is at `/openapi.json`.

Cart, favourites, and comparison remain client-side because the prototype has
no customer account flow. Public registration, generic CRUD endpoints, fake
reviews, and fake payment integrations are intentionally absent.

## Local setup

Requirements: Python 3.13+, `uv`, PostgreSQL, and Redis/KeyDB.

```bash
cp .env.sample .env
uv sync --locked --dev
uv run cli bootstrap
uv run cli create-user
uv run app
```

Start background delivery of outbox events in separate terminals:

```bash
uv run taskiq worker app.tiq:broker -w 4 app.tasks
uv run taskiq scheduler app.tiq:scheduler app.tasks
```

Inspect the durable delivery queue or explicitly retry dead events:

```bash
uv run cli outbox-stats
uv run cli retry-dead-outbox --limit 100
```

The local/dev notification adapter logs domain events. In production it fails
explicitly, so an event is retried instead of being falsely marked as delivered.
Replace `NotificationDispatcher` with a CRM/SMS/email adapter without changing
order or lead services.

## Docker

```bash
cp backend/.env.sample .env
docker compose up --build -d
docker compose exec app cli create-user
```

The default compose stack includes the API, migration/seed job, Taskiq workers,
scheduler, PostgreSQL, and KeyDB. Start the optional observability profile with:

```bash
docker compose --profile observability up --build -d
```

That profile adds Prometheus, Loki, Promtail, and Grafana on port `3001`.

## Tests and quality gates

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src/app
uv run pytest src/tests -n auto --cov=src/app --cov-report=term
```

Every declared application route has success, validation, not-found, or access
control coverage as applicable. CI requires at least 80% application coverage
and separately verifies Alembic migrations, `SKIP LOCKED`, concurrent row locks,
order idempotency against PostgreSQL, the Redis rate-limit script, and a
production Docker build with an idle-worker liveness smoke-test.

## API rules that affect the frontend

- `POST /orders` requires an `Idempotency-Key` header of 8-128 safe ASCII
  characters. Repeating the same key and body returns the original order;
  reusing it with a different body returns `409`.
- The frontend never submits a trusted price, discount, or total. It sends
  product IDs and quantities to `/checkout/quote`; the same pricing service is
  run again atomically when the order is created.
- Money is returned as decimal JSON strings such as `"192.00"`, avoiding
  floating-point rounding errors.
- Product specification filters repeat the GET parameter in `key:value` form,
  for example `?spec=Полюси:1P&spec=Номінал:16%20А`.
- Anonymous cart, favourite, and comparison state can restore current product
  data through repeated product IDs, for example `?id=<uuid>&id=<uuid>`. The
  list is deduplicated and limited to 100 IDs.
- Card and invoice orders are created with `payment_status=pending`. No fake
  payment URL is returned until a real provider adapter and webhook are added.
- Product detail links use the public `slug`; UUIDs remain internal identifiers
  for checkout lines and protected management operations.
- Access tokens belong to a server-side staff session. Refresh tokens rotate on
  every use; replaying a replaced or revoked refresh token returns `401`.
- `POST /auth/logout` accepts the refresh token in its JSON body, returns `204`,
  and revokes the complete server-side session, including access tokens already
  issued for it. Repeating the request is safe.
- Public login, refresh, quote, order, and lead writes are rate-limited through
  Redis. The default is fail-closed: when Redis is unavailable, protected
  requests return `503` instead of silently bypassing the limit.
- `/health` only proves that the process is alive. Deployments should use the
  hidden `/ready` endpoint to gate traffic on PostgreSQL and Redis availability.

See [architecture](docs/architecture.md) for the domain model, request flows,
status transitions, and explicit design boundaries.
