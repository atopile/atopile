# Install + Startup State Summary

This document captures the state model for the VS Code extension between
installation and a stable working state. It covers both normal and dev flows
after the simplifications (single backend URL, no auto-port, explicit restarts).

## Scope

- Extension activation → LSP + backend + UI ready
- Backend server lifecycle (fixed port / configured URL)
- Webview UI load path (prod vs dev)
- Areas that are still fragile or rely on external state

## Key Actors

- VS Code extension (`src/vscode-atopile/src/extension.ts`)
- LSP server (`ato lsp start`)
- Backend server (`ato serve backend --port <PORT>`)
- Webviews (Sidebar + LogViewer)
- UI server (Vite dev server in dev flow)

## Config Inputs

- `atopile.dashboardApiUrl` (default `http://localhost:8501`)
- `atopile.backendAutoStart` (default `true`)
- `atopile.ato` / `atopile.from` (binary/source selection)
- `atopile.uiMode` (`auto` | `dev` | `prod`)

## State Model (High-Level)

### 1) Installed (Extension Not Activated)
**State**: VS Code extension is installed but inactive.  
**Triggers to activate**:
- `onStartupFinished`
- `onLanguage:atopile`
- `workspaceContains:*.ato` or `workspaceContains:ato.yaml`
- Command invocations (e.g. `atopile.example`)

### 2) Activating
**Steps**:
- Initialize logging + telemetry
- Ensure ato binary (install via uv if missing and auto‑install enabled)
- Start / restart LSP (explicit, no implicit hot‑swap)
- Optionally auto‑start backend server
- Register webviews and commands

**Potential outcomes**:
- Success: transitions to **Ready**
- Failure: remains **Degraded** (e.g. no ato binary, LSP fails)

### 3) Backend Booting (Optional)
**When**: `backendAutoStart=true` during activation or user requests start.  
**Action**: `ato serve backend --port <PORT>` in a hidden terminal.  
**Key transitions**:
- Booting → Connected (WS `/ws/state` responds)
- Booting → Failed (no response within timeout)

**Single source of truth**:
- Backend URL/port is **always** `atopile.dashboardApiUrl`
- No auto‑port or port discovery

### 4) UI Loading
**State**: Webview is created and HTML is set.  
**Sub‑states**:
- **Prod**: uses compiled assets in `resources/webviews/`
- **Dev**: iframe to Vite dev server (`http://localhost:5173`)

**Backend connectivity**:
- Webview injects `__ATOPILE_API_URL__` / `__ATOPILE_WS_URL__`
- React app connects directly to backend `/ws/state`

### 5) Ready (Nominal)
**Definition**:
- LSP running
- Backend connected (or reachable if auto‑start disabled)
- Webviews loaded and receiving AppState over WS

### 6) Degraded / Partial
**Examples**:
- LSP missing or failed to start
- Backend not running and auto‑start disabled
- Webview not built in prod (shows “Webview not built” placeholder)

## Normal Flow (Production Extension)

1. Activation triggered.
2. Ensure ato binary.
3. Start LSP once.
4. If `backendAutoStart=true`, start backend on configured URL.
5. Register webviews (Sidebar + LogViewer).
6. Webview loads compiled assets.
7. UI connects to backend `/ws/state`.
8. State sync begins → Ready.

## Dev Flow (Extension + Vite)

1. Activation triggered.
2. Ensure ato binary.
3. Start LSP once.
4. If `backendAutoStart=true`, start backend on configured URL.
5. Webviews load iframe to Vite dev server.
6. React app connects to backend `/ws/state`.
7. State sync begins → Ready.

## State Transitions (Summary)

- **Installed → Activating**: activation events
- **Activating → Ready**: LSP + UI + backend OK
- **Activating → Degraded**: LSP fail or missing binary
- **Backend Booting → Connected**: WS responds to ping/action
- **Backend Booting → Failed**: timeout / process exit
- **Degraded → Ready**: user installs binary / restarts server

## Fragile / Unstable Points (Current)

- **Hidden terminal ownership**: backend process can outlive extension if host reloads.
- **External dependencies**: backend requires functional ato + Python env.
- **Webview build output**: prod view breaks if `resources/webviews/*` missing.
- **Backend unreachable**: UI hard depends on `/ws/state` connectivity.

## Design Decisions That Shrink State

- **Fixed backend URL** (no auto‑port, no port file scanning).
- **Explicit restarts only** (no UI‑driven hot‑swap).
- **Stateless webview providers** (UI owns state over WS).

## Notes

- `atopile.dashboardApiUrl` is the single address used by UI and extension.
- Any backend on a different port must be started explicitly and configured.
- Developer UI settings can force UI mode via `atopile.uiMode`.
  The webview still needs reload to apply the change.
