# atopile Playground

Public "Try atopile" playground that spins up an isolated web-IDE container for each visitor on Fly.io.

## Architecture

```
User → atopile-playground.fly.dev (spawner, always-on)
         │
         ├─ No cookie → landing page ("Try atopile")
         ├─ POST /api/spawn → create Machine via API, set cookie, redirect
         └─ Has cookie → fly-replay: app=atopile-ws;instance=<machine_id>
                              │
                              ▼
                         atopile-ws (workspace app, 0+ machines)
                         Each machine runs web-ide image on :3443
                         auto_destroy on stop, cleanup after 30min idle
```

Two Fly apps in the same org:

| App | Role | Spec |
|-----|------|------|
| `atopile-playground` | Spawner (always-on) | shared-cpu-1x, 256MB |
| `atopile-ws` | Workspaces (on-demand) | shared-cpu-1x, 1GB each |

Traffic routing uses the `fly-replay` response header — the spawner tells the Fly proxy to replay the request to the correct workspace machine. Works for both HTTP and WebSocket.

## Prerequisites

- [flyctl](https://fly.io/docs/flyctl/install/) installed and authenticated (`fly auth login`)
- A [Fly.io API token](https://fly.io/dashboard/personal/tokens) with Machine management permissions
- The web-IDE Docker image published to `ghcr.io/atopile/atopile-web-ide:latest`

## Deploy

```bash
# Set your API token (or the script will prompt you)
export FLY_API_TOKEN="fo1_..."

# Deploy both apps
./deploy.sh
```

The script will:
1. Create the `atopile-ws` workspace app (if it doesn't exist)
2. Create the `atopile-playground` spawner app (if it doesn't exist)
3. Set secrets (`FLY_API_TOKEN`, `WORKSPACE_APP`, `WORKSPACE_IMAGE`, `WORKSPACE_REGION`)
4. Deploy the spawner
5. Print the playground URL

## Local Development

```bash
# Run the spawner locally (needs a real Fly API token to spawn machines)
FLY_API_TOKEN="fo1_..." node server.js

# Visit http://localhost:8080
```

## Request Flow

1. **First visit**: `GET /` → landing page with "Try atopile" button
2. **Spawn**: `POST /api/spawn` → creates a Fly Machine (~1s) → waits for it to start (~15s) → sets signed cookie → redirects to `/`
3. **Subsequent requests**: cookie present → spawner returns `fly-replay` header → Fly proxy routes to workspace machine
4. **Session expired**: machine destroyed → spawner clears cookie → redirects to landing page

## Cleanup

A background loop runs every 5 minutes and destroys workspace machines that are:
- Idle for more than **30 minutes** (no requests through the spawner)
- Running for more than **60 minutes** (hard lifetime limit)

Machines are also configured with `auto_destroy: true`, so Fly will clean them up when they stop.

## Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Landing page (no cookie) or fly-replay to workspace (with cookie) |
| `/api/spawn` | POST | Create a new workspace machine |
| `/api/health` | GET | JSON health check (session count, uptime) |

## Cost Estimates

| Component | Cost |
|-----------|------|
| Spawner (always-on) | ~$2/mo |
| Each workspace (ephemeral) | ~$0.003/hr |
| 10 concurrent users | ~$25/mo |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8080` | Spawner listen port |
| `FLY_API_TOKEN` | — | Fly.io API token (required) |
| `WORKSPACE_APP` | `atopile-ws` | Fly app name for workspaces |
| `WORKSPACE_IMAGE` | `ghcr.io/atopile/atopile-web-ide:latest` | Docker image for workspaces |
| `WORKSPACE_REGION` | `iad` | Fly region for new machines |
