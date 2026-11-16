# Nova Poshta delivery directory

## Request path

The public API remains `GET /api/v1/delivery/cities` and
`GET /api/v1/delivery/points`. The API key stays on the server.

The directory service searches complete cached snapshots, not the provider on
each keystroke. Redis shares snapshots and coordination across web processes
and Taskiq workers. Each process keeps at most 64 decoded snapshots for 30
seconds, avoiding repeated JSON decoding of large cities. City matching uses a
pre-normalized index and a bounded 256-query result cache.

On a cold miss, online search remains available. Identical requests share one
loader through an owner-checked Redis lease; distinct cold provider requests
have a bounded wait and an overall deadline. Recent successful results are
usable during provider outages. Corrupt, expired and partial data is not
published as a valid directory.

## Background work and bounds

- `refresh_delivery_city`: queued once when a city is first used or its
  snapshot becomes stale. Downloads all pages before atomically replacing the
  snapshot. Failed refreshes preserve the previous successful snapshot.
- `refresh_delivery_directories`: every 10 minutes checks the country
  directory and up to 64 recently used cities. Cities refresh after 12 hours;
  point snapshots after one hour by default.
- Redis retains at most 64 city-point snapshots, one country snapshot and 512
  query results. All have finite TTLs. Active-city tracking is also bounded.
- A shared per-key gate spaces outbound request starts by 500 ms by default.
  Waiting for a slot is limited to two seconds; an individual provider lookup
  is limited to eight seconds including its one retry.
- The complete public lookup has a 10-second deadline. The IP-level abuse
  guard allows 300 directory reads per minute; it is independent of the much
  stricter shared provider-key budget. Normal users sharing a NAT are not
  restricted to the old 60 combined city/point queries per minute.
- Provider rate-limit responses (including HTTP 200 with error code
  `20000401501`) and HTTP 429 trigger a shared pause; `Retry-After` is
  respected. A failed provider lookup opens a short shared cooldown.
- Redis coordination failure does not fall back to unrestricted provider
  calls. The existing public 503/error UI and manual-address fallback remain.
- Disabled points (`DenyToSelect`), drop-off and fulfilment points are not
  offered for delivery. Filtering never removes the knowledge of subsequent
  provider pages.

The pacing is a conservative application setting, **not a claim of an official
universal NP quota**. The provider may apply account-specific limits or other
consumers may use the same API key.

The application Redis client uses a blocking asynchronous pool, bounded to 64
connections with a two-second queue wait. Bursts wait briefly for a reusable
connection instead of immediately failing with `MaxConnectionsError`. Pool
limits are configurable through `APP__REDIS__MAX_CONNECTIONS` and
`APP__REDIS__POOL_TIMEOUT_SECONDS`; the pool is closed by the application scope.

Optional environment settings use the existing nested configuration:

```dotenv
APP__NOVA_POSHTA__DIRECTORY_ENABLED=true
APP__NOVA_POSHTA__DIRECTORY_TTL_SECONDS=3600
APP__NOVA_POSHTA__DIRECTORY_STALE_SECONDS=86400
APP__NOVA_POSHTA__REQUEST_INTERVAL_SECONDS=0.5
APP__NOVA_POSHTA__REQUEST_WAIT_SECONDS=2
APP__NOVA_POSHTA__REQUEST_DEADLINE_SECONDS=8
```

The scheduler and workers must run the same backend release as the API.
Background synchronization is disabled without a configured NP API key.

## Verification

`src/integration_tests/test_redis_delivery.py` uses real Redis and synthetic NP
responses. It checks four independent cache/service instances, cold request
coalescing, many distinct searches, owner-safe leases, storage bounds, failure
rollback, cancelled loaders, stale results, pagination and the shared gate.

`scripts/benchmark_delivery.py` runs a burst benchmark against the configured
Redis using four service instances and synthetic directories. It makes **zero
real NP requests**, never changes shop data and cleans only its unique
temporary namespace (also protected by TTL). It measures the directory/service
layer, not total HTTP/site throughput or thousands of continuous shoppers.

```bash
uv run python scripts/benchmark_delivery.py --concurrency 500 --size 10000
```

Recorded measurements and production smoke checks should include the tested
release, hardware/environment, concurrency, directory size, response percentiles
and upstream-call count. Cold caches serving entirely different, previously
unused cities still depend on the provider's quota; bounded overload is
reported as a controlled 503 rather than unbounded waiting or provider flooding.

## References

- [Nova Poshta integration entry points](https://novaposhta.ua/for-business/cooperation/integration/)
- [WebX directory synchronization](https://webx-ui.github.io/webx-ui/guide/delivery-novaposhta)
- [Redis distributed rate limiting](https://redis.io/docs/latest/develop/use-cases/rate-limiter/)
- [Redis cache-aside and request coalescing](https://github.com/redis/docs/blob/main/content/develop/use-cases/cache-aside/nodejs/_index.md)
- [Redis owner-checked leases](https://redis.io/docs/latest/manual/patterns/distributed-locks/)
- [redis-py asynchronous connection pools](https://redis.readthedocs.io/en/stable/connections.html#redis.asyncio.connection.BlockingConnectionPool)
