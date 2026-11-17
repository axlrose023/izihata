# Nova Poshta delivery

Public endpoints are unchanged: `GET /api/v1/delivery/cities` and
`GET /api/v1/delivery/points`. The API key is server-only.

## Design

- The HTTP client maps NP responses, retries once and enforces an eight-second
  provider deadline. A Redis gate shares request pacing and cooldowns between
  the API and Taskiq workers. Redis failure never bypasses the provider limit.
- Redis stores two complete country snapshots: cities and delivery points.
  Each API process holds a bounded local cache and builds search indexes off
  the request loop. Reading an unchanged snapshot does not rebuild its index.
- A missing result can fall back to live NP search. These results have finite
  TTLs, a 512-entry Redis limit and single-flight loading across processes.
  Recent successful results remain usable during a provider outage.
- One Taskiq task checks snapshots every ten minutes. Cities refresh after
  twelve hours, points after six hours; previous snapshots can survive one
  additional day. A single owner-checked lease and ten-minute job deadline
  cover the entire refresh. Partial, empty and non-progressing downloads never
  replace valid snapshots.
- Stale/missing directories may enqueue that same task at most once per five
  minutes. Failed jobs do not cause a task for every subsequent user request.
- Point type and availability are filtered before cached pagination. Online
  responses retain raw page metadata so filtering cannot lose later pages.
  Public lookup has a ten-second deadline and a 300-request/minute IP limit.
  Controlled 503 responses retain the frontend's manual-address fallback.

The one-second provider pacing is configurable, not an official universal NP
quota. The scheduler, worker and API must use the same release.

## Verification

`test_redis_delivery.py` checks real Redis, four independent service instances,
concurrent cold misses, snapshot replacement, cancellation, bounds, failures,
pagination and provider pacing. `test_delivery_http.py` tests the real API and
500 concurrent requests from separate IPs across 500 synthetic cities.
No load test calls the real NP API or writes shop data.

```sh
uv run pytest src/integration_tests -m 'not load' --cov=src/app
uv run pytest src/integration_tests/test_delivery_http.py -m load -q -s
```

CI runs the burst separately from coverage tracing to avoid distorting socket
deadlines. This checks the delivery subsystem, not whole-store capacity.

Optional settings use `APP__NOVA_POSHTA__`: `DIRECTORY_ENABLED`,
`DIRECTORY_TTL_SECONDS`, `DIRECTORY_STALE_SECONDS`,
`REQUEST_INTERVAL_SECONDS`, `REQUEST_WAIT_SECONDS` and
`REQUEST_DEADLINE_SECONDS`.
