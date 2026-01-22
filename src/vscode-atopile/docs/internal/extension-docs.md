# VS Code Extension Notes

This file consolidates development notes, architecture summaries, and test plans
that used to live in `src/vscode-atopile/`. It is kept outside the packaged
extension to avoid shipping internal documentation.

## Development

### Recommended workflow

Use the debugging tools "Debug Extension and Python Attach to Process" to run
the extension in a new window. This will allow you to see the output of the
extension in the debug console.

### Backup

I've had trouble with the development tools here. Specifically, I'm unconvinced
the Python LSP debugger is working correctly.

For basic validation, it is easy to build a VSIX:

`vsce package --pre-release --no-git-tag-version --no-update-package-json 1000.0.0`

## Install + Startup State Summary

### Scope

- Extension activation → LSP + backend + UI ready
- Backend server lifecycle (fixed port / configured URL)
- Webview UI load path (prod vs dev)
- Areas that are still fragile or rely on external state

### Key actors

- VS Code extension (`src/vscode-atopile/src/extension.ts`)
- LSP server (`ato lsp start`)
- Backend server (`ato serve backend --port <PORT>`)
- Webviews (Sidebar + LogViewer)
- UI server (Vite dev server in dev flow)

### Config inputs

- `atopile.ato` / `atopile.from` (binary/source selection)

### Backend connection

- Backend is always started by the extension and bound to a per-session local port.
- The extension never connects to externally configured or pre-existing backend instances.

### State model (high-level)

1) Installed (extension not activated)
- Activation triggers: `onStartupFinished`, `onLanguage:atopile`,
  `workspaceContains:*.ato` or `workspaceContains:ato.yaml`, commands.

2) Activating
- Initialize logging + telemetry
- Ensure ato binary
- Start / restart LSP (explicit)
- Start backend server
- Register webviews and commands

3) Backend booting
- Starts `ato serve backend --port <PORT>` in a hidden terminal
- Booting → Connected (WS `/ws/state` responds)
- Booting → Failed (no response within timeout)

4) UI loading
- Prod: compiled assets in `resources/webviews/`
- Dev: iframe to Vite dev server (`http://localhost:5173`)
- Webview injects `__ATOPILE_API_URL__` / `__ATOPILE_WS_URL__`

5) Ready (nominal)
- LSP running, backend connected, webviews receiving AppState

6) Degraded / partial
- LSP missing/failed
- Backend not running and auto-start disabled
- Webview assets missing

### Fragile points

- Hidden terminal ownership: backend process can outlive extension reloads.
- Backend depends on functional ato + Python env.
- Missing `resources/webviews/*` breaks prod UI.
- UI hard depends on `/ws/state` connectivity.

## Refactor Review + Staged Plan

### Review findings (selected)

- Webview entrypoints still load VS Code-bound UI (`Sidebar`/`LogViewer`), so the
  stateless/iframe flow will not work in dev.
- WS URL and message types do not match backend (`/ws/state` vs `/ws`,
  `action_result` vs `actionResponse`).
- UI server still has leftover dev/proxy coupling.

### Stage 1: Make UI server VS Code-agnostic

- Switch webview entrypoints to store-based UI (e.g. `SidebarNew`).
- Remove `acquireVsCodeApi` usage from core UI paths.
- Align WS URL and message types with backend.

### Stage 2: Move UI server to `src/ui-server`

- Relocate Vite app (src/config/tests) to `src/ui-server`.
- Update scripts/docs to run Vite from new location.
- Remove/replace old webviews dev server/proxy.

### Stage 3: Shrink `webviews/` to minimal wrappers

- Replace webview HTML with iframe wrappers pointing at Vite dev server.
- Remove React app code from `webviews/`.
- Update tests to cover iframe wrappers/providers.

## Debugging Investigation Summary (highlights)

### Open buttons (ato/kicad/layout/3d)

Problem: actions called missing methods:
- `set_open_file`
- `set_open_layout`
- `set_open_kicad`
- `set_open_3d`

Fix applied (prior work):
- Added methods to `state.py`
- Added fields to `dataclasses.py`
- Added handler in `appState-ws-standalone.ts`

### Standard library items expanded

Problem: `StdLibCard` always rendered children.
Fix: Only show details when selected.

### Debugging steps

- Webview DevTools: check WS / JS errors
- Backend logs: start with `ATOPILE_LOG_LEVEL=DEBUG`
- Add logging in `actions.py`, `websocket.ts`, `state.py`

## Extension Architecture Overview

### Overview

```
React UI (Vite) -> REST + WebSocket -> Python Backend (FastAPI)
```

### WebSocket events (selected)

- `build:started`
- `build:stage`
- `build:completed`
- `logs`
- `summary:updated`
- `problems:updated`

### REST endpoints (selected)

- `/api/projects`
- `/api/build`
- `/api/builds/active`
- `/api/summary`
- `/api/packages`
- `/api/packages/install`
- `/api/problems`

## Install Flow Test Plan (condensed)

1) Fresh install, autoInstall=true
- Expect uv download, ato self-check, LSP + backend start, installing=false

2) autoInstall=false with no ato configured
- No install attempt, LSP fails to start (documented behavior)

3) Valid `atopile.ato`
- No uv download, LSP + backend start

4) Invalid `atopile.ato`
- Error logged, auto-install runs if enabled

5) `atopile.from` variants
- uv uses `--from`, LSP + backend reflect selected version

6) Settings change → restart behavior
- LSP + backend restart on change

7) Race: install vs initial LSP start
- Possible early error; restart should recover

8) uv download failure
- Error toast, extension remains idle

9) Windows path with spaces
- Validate quoting in terminal commands

10) Reinstall/cleanup
- uv re-downloads after deletion
