# IziHata Frontend

React 19 and Vite storefront and staff panel for the IziHata API. The old prototype is
used only as a visual reference; this implementation is modular, typed, tested,
and does not contain demo catalog or order data.

## Architecture

- `src/app` contains application composition, providers, and route declarations;
- `src/pages` contains route-level views without transport logic;
- `src/modules` owns catalog, cart, checkout, leads, collections, auth, and admin
  capabilities;
- `src/shared` contains the HTTP contract, API clients, formatting, and reusable
  UI primitives;
- `src/widgets` composes the public application shell.

Route modules are loaded on demand. TanStack Query owns server state, while
Zustand owns only anonymous browser state such as cart, favourites, and
comparison. FastAPI remains the only business-logic layer and the source of
truth for catalog data, prices, promotions, status transitions, and authorization.

All browser API traffic goes directly to same-origin `/api/v1`. In development,
Vite proxies this prefix to FastAPI; in production, Nginx does the same without a
Node.js runtime. FastAPI keeps the rotating refresh token in an `HttpOnly`
same-site cookie and returns only a short-lived access token to browser memory.

## Development

```bash
npm ci
npm run dev
```

The backend must be available at `http://127.0.0.1:8000` unless
`VITE_API_PROXY_TARGET` is changed.

## Quality gates

```bash
npm run format:check
npm run lint
npm run typecheck
npm run test:coverage
npm run build
npm run test:e2e
```

The production image contains only the compiled SPA and Nginx. Requests for
client routes fall back to `index.html`; `/api/*` is proxied to FastAPI.
