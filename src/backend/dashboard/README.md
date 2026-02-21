# Components Dashboard

React frontend for the components backend observability dashboard.

## Local development

```bash
cd /Users/narayanpowderly/projects/atopile/src/backend/dashboard
npm install
npm run dev
```

Vite runs on `http://127.0.0.1:5174/dashboard/`.

## Build for serving from FastAPI

```bash
cd /Users/narayanpowderly/projects/atopile/src/backend/dashboard
npm install
npm run build
```

This writes static assets to `dist/`.

The backend serve process mounts that directory at `/dashboard`.

## Tailscale deployment

Run the components backend with:

```bash
export ATOPILE_COMPONENTS_SERVE_HOST=0.0.0.0
uv run python -m backend.components.serve.main
```

Access over Tailscale at:

- `http://<tailscale-ip>:8079/dashboard`
- `http://<tailscale-ip>:8079/v1/dashboard/metrics`

No separate dashboard server is required.
