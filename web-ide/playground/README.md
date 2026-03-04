# atopile Playground (Python Production App)

Playground spawner for atopile web-IDE, implemented as a standalone Python app with:
- `uv` project management
- Typer CLI
- FastAPI server
- Pydantic models/config
- TypeScript landing client built by Bun + esbuild

## Commands

From `web-ide/playground`:

```bash
uv run main.py server start
uv run main.py infra deploy
uv run main.py infra status
uv run main.py infra status --local
```

## Configuration

Single source of truth is [`config.toml`](./config.toml).

Runtime secret behavior:
- `infra deploy`: prefers `FLY_API_TOKEN` if it can access workspace machines; otherwise creates a Fly deploy token scoped to `infra.ws.app` and stores it as spawner `FLY_API_TOKEN`
- `server start`: requires token and resolves from `FLY_API_TOKEN` env or `fly auth token` (fails fast otherwise)

Infra structure:
- `infra.spawner`: spawner app/deploy/manifest settings
- `infra.ws`: workspace machines/runtime image/deploy settings
  - `infra.ws.machine`: Fly machine runtime sizing/restart settings (vm, restart)

## HTTP Contract

The server preserves the previous spawner contract:
- `GET /` landing page (or fly replay when session cookie is valid)
- `POST /api/spawn` create/claim machine, set session cookie, redirect to `/`
- `GET /api/health` health stats
- `GET /dashboard` dashboard UI
- `GET /api/dashboard/series` active/warm/total history for charts

Security behavior:
- Spawner replay now includes machine-bound `state=...` and workers require matching replay state.
- Direct requests to the workspace app host are denied unless they arrive via replay.

Capacity failures return:

```json
{"error":"No free machines available. Try later or install locally"}
```

## Frontend Build

`server start` auto-builds landing assets when stale/missing:
1. Generate TypeScript types from Pydantic models.
2. Build `web/src/main.ts` with Bun + esbuild.

Manual build:

```bash
uv run main.py web build
```

## Deploy Notes

`infra deploy` performs parity operations with the old script:
- ensure Fly apps exist
- build/push workspace image
  - uses local Docker builder when available, otherwise `fly --remote-only`
- cycle workspace machines
- update spawner runtime secret (`FLY_API_TOKEN`)
- generate Fly manifest from `config.toml` and deploy spawner app

## Development

Run tests:

```bash
uv run --group dev pytest tests
```
