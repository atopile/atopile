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
| `atopile-ws` | Workspaces (on-demand) | performance-1x, 2GB each |

Traffic routing uses the `fly-replay` response header — the spawner tells the Fly proxy to replay the request to the correct workspace machine. Works for both HTTP and WebSocket.

## Prerequisites

- [flyctl](https://fly.io/docs/flyctl/install/) installed and authenticated (`fly auth login`)
- A [Fly.io API token](https://fly.io/dashboard/personal/tokens) with Machine management permissions

## Deploy

### Full deploy (workspace image + spawner)

Builds the web-IDE Docker image via Fly's remote builder, pushes it to
`registry.fly.io/atopile-ws:latest`, then deploys the spawner.

```bash
cd web-ide/playground

# Set your API token (or the script will prompt)
export FLY_API_TOKEN="fo1_..."

# Build workspace image + deploy spawner
./deploy.sh
```

The script will:
1. Create the `atopile-ws` and `atopile-playground` apps (if they don't exist)
2. Build the workspace Docker image via Fly's remote builder
3. Push the image to `registry.fly.io/atopile-ws:latest`
4. Destroy old workspace machines so new sessions use the updated image
5. Configure spawner secrets and deploy the spawner
6. Print the playground URL and monitoring commands

### Spawner-only deploy

Use when you've only changed `server.js` or `fly.spawner.toml` and don't need
to rebuild the workspace image:

```bash
./deploy.sh --spawner-only
```

### Workspace image-only deploy

Use when you've changed the web-IDE (extension, Dockerfile, etc.) but don't
need to redeploy the spawner:

```bash
./deploy.sh --workspace-only
```

This builds the image, pushes it, and cycles existing workspace machines.
The spawner's pool replenishes automatically within ~30 seconds.

### Validate after deploy

```bash
cd web-ide
node scripts/validate.mjs 'https://atopile-playground.fly.dev' --timeout=120000
```

## How the image gets to Fly

The workspace image lives in Fly's built-in registry at
`registry.fly.io/atopile-ws:latest`. The deploy script uses `fly deploy` to
build via Fly's remote builder and push to this registry. This avoids needing
GHCR credentials or external registry auth.

The spawner's `WORKSPACE_IMAGE` defaults to `registry.fly.io/atopile-ws:latest`
(set in `server.js`), so new workspace machines automatically use the latest
pushed image.

When the deploy script cycles workspace machines (destroys old ones), the
spawner's background pool replenishment loop creates fresh machines with the
new image within ~30 seconds.

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
| `WORKSPACE_IMAGE` | `registry.fly.io/atopile-ws:latest` | Docker image for workspaces |
| `WORKSPACE_REGION` | `iad` | Fly region for new machines |

## Troubleshooting

### Workspace machines stuck on old image

Destroy all workspace machines — the spawner will replenish the pool with fresh
ones using the latest image:

```bash
fly machines list --app atopile-ws
fly machines destroy <id> --app atopile-ws --force
```

### Backend shows "Connecting..." in status bar

The atopile backend server takes ~20-30 seconds to start after the machine
boots. If it persists, SSH in and check:

```bash
fly ssh console --app atopile-ws --machine <id> \
  -C 'sh -lc "pgrep -af ato"'
```

### Checking spawner health

```bash
curl https://atopile-playground.fly.dev/api/health
fly logs --app atopile-playground
```
