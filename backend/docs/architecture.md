# IziHata backend architecture

## 1. Reference analysis

The source repository is a single-file React prototype, not an existing
backend. It contains 18 electrical-goods categories, a full subcategory tree,
54 initial products, local filtering and sorting, a guest cart, one promotion,
checkout, three lead forms, and an in-memory admin demo.

The backend boundary follows observable product behaviour:

- catalogue data, prices, availability, product attributes, promotions,
  orders, leads, and admin state must be durable and authoritative;
- cart, favourites, and comparison are anonymous browser state until a real
  customer account use case exists;
- hard-coded testimonials and dashboard conversion are presentation mocks, so
  they are not persisted or exposed as invented APIs;
- Nova Poshta addresses are read through an external adapter; payment acquiring,
  SMS, and CRM remain external seams rather than mocked domain truth.

This keeps the API small while leaving explicit seams for later integrations.

## 2. Module boundaries

```text
HTTP route
  -> application service
     -> UnitOfWork
        -> focused gateways
           -> SQLAlchemy models / PostgreSQL
     -> transactional outbox event

Taskiq scheduler/worker
  -> claim outbox batch
     -> notification adapter
        -> future CRM / SMS / email provider
```

Each feature under `src/app/api/modules` owns its schemas, gateways, models, and
enums where applicable. Role-specific HTTP handlers live in
`routes/user.py` and `routes/admin.py`. Concrete use cases live in focused
`services/` modules; the module-level `service.py` is only a public facade.
Non-Pydantic normalization helpers live in `utils.py`. Routes validate transport
data and delegate, gateways contain queries, and the unit of work owns the
transaction. Dishka only assembles dependencies.

Cross-module dependencies point toward reusable domain capabilities:

- `orders` depends on the `checkout.PricingService` rather than duplicating
  money and promotion logic;
- `orders` and `leads` append outbox events inside their database transaction;
- `admin` aggregates existing gateways and does not own duplicate models;
- authentication uses the internal staff `User` model; there is no public user
  resource or registration route.

## 3. Data model

| Aggregate | Tables | Important invariants |
| --- | --- | --- |
| Catalogue | `categories`, `subcategories`, `products`, `product_attributes` | Unique slugs/SKU; non-negative prices; old price cannot be below current price; normalised indexed attributes support portable facets |
| Checkout | `promotions` | Case-normalised unique code; active time window; discount rate in `(0, 1]` |
| Order | `orders`, `order_items` | Immutable item name/SKU/price snapshots; server totals; unique idempotency key; positive quantities |
| Lead | `leads` | Typed callback/quick-buy/wholesale context; optional product FK uses `SET NULL` |
| Staff auth | `users`, `auth_sessions` | Unique username; bcrypt password hash; active flag; one current refresh JTI per revocable session |
| Delivery | `outbox_events` | Durable event payload; retry count; next attempt; processing lease; processed/dead state |

Money uses `NUMERIC(12, 2)` and Python `Decimal`. Product specifications are
normalised into rows instead of a JSON blob so filters and facet counts use
ordinary indexed SQL in both PostgreSQL and SQLite tests. PostgreSQL additionally
uses `pg_trgm` GIN search on product names.

## 4. Catalogue query

`GET /catalog/products` owns all browse/search behaviour in one route:

- pagination: `page`, `page_size`;
- bounded repeated `id` values for restoring anonymous client-side lists;
- selection: `search`, `category`, `subcategory`, repeated `brand`;
- availability and money: `in_stock`, `min_price`, `max_price`;
- repeated specification filters: `spec=key:value`;
- stable sorting: popular, price ascending/descending, newest.

The response includes products, pagination metadata, brand facets,
specification facets, and the applicable price range. A separate endpoint per
filter would add round trips and duplicate query semantics, so facets are part
of the catalogue result.

## 5. Pricing and order creation

```text
Frontend cart IDs + quantities
  -> POST /checkout/quote
     -> load active products
     -> validate promotion window
     -> Decimal line totals, discount, total
  -> show authoritative quote

Confirmed contact/delivery/payment data + same cart
  -> POST /orders with Idempotency-Key
     -> reject conflicting key reuse
     -> run the same PricingService again
     -> save order + item snapshots + outbox event in one commit
     -> return created or previously created order
```

Recalculation during order creation closes the time-of-check/time-of-use gap if
an administrator changes a price between quote and confirmation. Client-sent
price and total fields are forbidden by strict request schemas.

## 6. Order state machine

Allowed transitions are deliberately explicit:

```text
new -> processing -> confirmed -> shipped -> delivered
 |         |             |
 +---------+-------------+----> cancelled
```

Delivered and cancelled are terminal. Skipping operational states returns
`422`, and every accepted transition emits an outbox event. Payment status is a
separate state because fulfilment and acquiring are different processes.

## 7. Background work and delivery guarantees

Enqueuing a broker task after a database commit can lose notifications if the
process dies between the two operations. IziHata therefore stores an outbox row
in the same transaction as the order or lead.

Workers claim rows with `FOR UPDATE SKIP LOCKED`, set a five-minute processing
lease, and commit before calling an external adapter. Each worker takes at most
10 rows and each provider call has a 15-second timeout, so the lease exceeds the
maximum normal batch duration. A crashed worker leaves a recoverable lease;
failed deliveries use bounded exponential backoff and move to `dead` after the
configured attempt limit. A daily task removes old processed rows. This is safe
with multiple Taskiq workers and does not hold database locks during a network
call.

## 8. Security and operational decisions

- only staff routes require bearer tokens; public catalogue, quote, order, and
  lead flows match guest checkout in the prototype;
- password hashes use bcrypt and are verified outside the event-loop thread;
- access and refresh tokens have independent TTLs and reference a server-side
  session; each successful refresh rotates its JTI under a row lock, so replay
  and concurrent reuse are rejected;
- logout validates a signed refresh token and revokes the complete session
  under the same row lock. A previously rotated token may revoke its own
  session, making logout idempotent and deterministic when it races refresh;
- public user creation from the base template was removed; staff accounts are
  created through an operator CLI;
- CORS origins and trusted hosts are explicit environment settings;
- proxy headers are trusted only from explicitly configured proxy addresses;
- JWT signing is restricted to HS256 and production rejects weak secrets;
- public write/auth endpoints use atomic Redis-backed fixed-window rate limits
  and fail closed by default when Redis is unavailable;
- PostgreSQL connections use pre-ping, bounded pooling, recycling, and a
  statement timeout; application shutdown disposes the engine cleanly;
- response models exclude password hashes and internal idempotency/request
  hashes;
- customer PII is not included in outbox payloads or structured logs;
- dashboard day boundaries use the configured `Europe/Kyiv` business timezone;
- `/health` is a liveness check, while the hidden `/ready` probe verifies the
  database and Redis dependency before a deployment receives traffic;
- Prometheus metrics and health checks remain enabled, while Loki/Promtail and
  Grafana are available through the optional compose observability profile.

Operational recovery is explicit rather than exposed as an HTTP business API:
`cli outbox-stats` reports queue states and `cli retry-dead-outbox` moves a
bounded, locked batch of dead events back to pending. Expired auth sessions and
old processed outbox rows are removed by scheduled Taskiq maintenance tasks.

## 9. Deliberate next extensions

The following should be implemented only when provider and product requirements
are known:

1. payment provider adapter, signed webhook, and payment-attempt table;
2. Nova Poshta city/branch cache and delivery quote adapter;
3. real CRM/SMS/email notification adapters behind `NotificationDispatcher`;
4. customer accounts, then persisted carts/favourites/comparison;
5. media/object-storage model when product images become managed content;
6. inventory reservation if stock quantity replaces the current binary
   in-stock/preorder status.

These extensions fit the existing client/service/gateway/outbox seams without
adding speculative routes today.
