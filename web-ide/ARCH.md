# Web IDE Networking Architecture

Last updated: 2026-02-16

## Scope

This document describes how network traffic flows in the `web-ide` deployment:

- Browser clients (local, LAN, or Tailscale)
- Caddy reverse proxy
- OpenVSCode Server
- atopile VS Code extension host
- atopile backend server (`ato serve backend`)

## Topology

```text
Client Browser
    |
    | HTTPS :3443 (recommended)
    v
Host port publish (podman compose, WEB_IDE_BIND_ADDR)
    |
    v
Container: Caddy
    |-- /ws/* /api/* /health ----------> 127.0.0.1:8501 (atopile backend)
    \-- everything else ---------------> 127.0.0.1:3001 (OpenVSCode Server)
```

Inside OpenVSCode:

- The extension host starts/stops `ato serve backend`.
- Webviews (sidebar, log viewer) communicate with backend through:
  - Extension-host proxy messages (`postMessage`) as primary path.
  - Native WebSocket fallback to `wss://<host>:3443/ws/...` if webview API bridge is unavailable.

## Port and Bindings

- Host published ports (from `docker-compose.yml`):
  - `${WEB_IDE_HTTPS_PORT:-3443}` -> container `3443` (Caddy HTTPS front door)
- Internal-only container services:
  - `127.0.0.1:3001` OpenVSCode Server
  - `127.0.0.1:8501` atopile backend

The backend is intentionally bound to localhost (`ATOPILE_BACKEND_HOST=127.0.0.1`).

## Request Routing

### 1. Workbench and extension host traffic

1. Browser opens `https://<host>:3443/`.
2. Caddy forwards non-`/ws/*` paths to OpenVSCode on `127.0.0.1:3001`.
3. Browser establishes VS Code websocket channels (`/stable-...`) through Caddy to OpenVSCode.
4. OpenVSCode extension host runs inside container and activates atopile extension.

### 2. Backend state and command traffic (`/ws/state`, HTTP API)

Primary path (used by sidebar and shared UI):

1. Webview JS overrides `fetch` and `WebSocket`.
2. Webview sends `fetchProxy` / `wsProxy*` messages to extension host via `acquireVsCodeApi().postMessage(...)`.
3. Extension host executes:
   - Node `fetch` to backend HTTP endpoints.
   - Node websocket connection to backend `/ws/state`.
4. Extension host posts results/events back to webview.

Fallback path for websocket (new behavior):

1. If `acquireVsCodeApi` is unavailable or throws in the webview, webview opens native websocket.
2. URL is rewritten from local target (`ws://localhost:8501/...`) to parent origin (`wss://<host>:3443/ws/...`).
3. Caddy routes `/ws/*` to backend on `127.0.0.1:8501`.

### 3. Log viewer traffic (`/ws/logs`)

1. Log viewer webview uses the same websocket proxy contract (`wsProxyConnect/wsProxySend/wsProxyClose`).
2. Extension host rewrites target to internal backend URL (`127.0.0.1:8501`) and opens Node websocket.
3. If webview API bridge is not available, fallback uses native websocket to `wss://<host>:3443/ws/logs`.
4. Caddy forwards `/ws/logs` to backend.

## TLS / Origin Notes

- Caddy terminates TLS on `:3443` with `tls internal`.
- Cert hostnames include: `localhost`, `127.0.0.1`, `code-vm`, and `${WEB_IDE_PUBLIC_HOST}`.
- `default_sni` is set to `${WEB_IDE_PUBLIC_HOST}` to handle clients that omit SNI.

## Security Posture (Network-relevant)

- Backend is not directly exposed by port publish.
- Caddy routes `/ws/*`, `/api/*`, and `/health` to the backend (`127.0.0.1:8501`); all other paths go to OpenVSCode Server.
- OpenVSCode and backend listen on loopback inside container.
- External exposure is controlled by:
  - `WEB_IDE_BIND_ADDR` (interface binding)
  - Host firewall / Tailscale ACL policy

## Runtime Control

- Start/rebuild/recreate: `./scripts/web-idectl.sh start`
- Status: `./scripts/web-idectl.sh status`
- Stop: `./scripts/web-idectl.sh stop`

`start` now runs compose with `--build --force-recreate` so extension/webview networking changes are reliably applied.

## Source Files

- `docker-compose.yml`
- `scripts/Caddyfile`
- `scripts/entrypoint.sh`
- `../src/vscode-atopile/src/common/backendServer.ts`
- `../src/vscode-atopile/src/common/webview-bridge.ts`
- `../src/vscode-atopile/src/common/webview-bridge-runtime.ts`
- `../src/vscode-atopile/src/providers/SidebarProvider.ts`
- `../src/vscode-atopile/src/providers/LogViewerProvider.ts`
- `../src/vscode-atopile/src/ui/layout-editor.ts`
