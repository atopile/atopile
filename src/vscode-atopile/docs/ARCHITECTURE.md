# VS Code Extension Architecture

This document describes the internal architecture of the atopile VS Code extension for developers.

## Overview

The extension consists of several interconnected components:

```
┌─────────────────────────────────────────────────────────────────────┐
│                        VS Code Extension                             │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────────┐ │
│  │ extension  │  │  findbin   │  │  server    │  │ appState-ws    │ │
│  │    .ts     │──│    .ts     │──│    .ts     │  │ standalone.ts  │ │
│  │ (entry)    │  │(bin detect)│  │(LSP client)│  │(WebSocket sync)│ │
│  └────────────┘  └────────────┘  └────────────┘  └────────────────┘ │
│         │                │               │               │          │
└─────────┼────────────────┼───────────────┼───────────────┼──────────┘
          │                │               │               │
          ▼                ▼               ▼               ▼
    ┌──────────┐    ┌──────────┐    ┌───────────┐   ┌───────────┐
    │ ui/setup │    │   UV     │    │ ato lsp   │   │ ato serve │
    │   .ts    │    │ (binary) │    │  start    │   │  (Python) │
    │(uv setup)│    │          │    │  (stdio)  │   │ :<ephemeral> │
    └──────────┘    └──────────┘    └───────────┘   └───────────┘
```

## Key Files

| File | Purpose |
|------|---------|
| `src/extension.ts` | Extension entry point, activates all components |
| `src/common/findbin.ts` | Detects ato binary location, manages UV |
| `src/common/server.ts` | LSP client lifecycle management |
| `src/common/backendServer.ts` | Backend server lifecycle (auto-start, restart, stop) |
| `src/common/appState-ws-standalone.ts` | WebSocket state sync with Python backend |
| `src/common/settings.ts` | VS Code settings management |
| `src/ui/setup.ts` | UV download and installation |
| `src/ui/ui.ts` | Webview panels (sidebar, log viewer) |

---

## Bootstrap Flow

### 1. Extension Activation

```
extension.ts: activate()
  │
  ├─► initializeTelemetry()
  │
  ├─► initServer()
  │   ├─► initAtoBin()           // Set up binary detection
  │   │   ├─► Set g_uv_path_local (extension storage path)
  │   │   └─► Register config change listeners
  │   │
  │   └─► Fire onNeedsRestart    // Triggers LSP server start
  │
  ├─► ui.activate()
  │   └─► setup.activate()
  │       └─► ensureAtoBin()     // Download UV if needed
  │
  └─► initAtopileSettingsSync()  // Sync UI settings to VS Code
```

### 2. Binary Detection (findbin.ts)

Priority order:
1. **`atopile.ato` setting** → Direct path to ato binary
2. **Extension-managed UV** → `uv tool run -p 3.13 --from {source} ato`

The `--from` source comes from `atopile.from` setting:
- Release: `atopile` or `atopile@0.9.0`
- Branch: `git+https://github.com/atopile/atopile.git@branch-name`

### 3. UV Installation (ui/setup.ts)

If no ato binary found and `atopile.autoInstall` is true:
1. Download UV binary from GitHub releases
2. Extract to extension global storage
3. Run `ato self-check` via `uv tool run`
4. Fire `onDidChangeAtoBinInfoEvent` to start servers

---

## Server Management

### LSP Server (server.ts)

The Language Server provides:
- Syntax highlighting
- Diagnostics (errors/warnings)
- Go-to-definition
- Hover information
- Code completion

**Lifecycle:**
```typescript
// Start/restart server
onNeedsRestart → startOrRestartServer()
  │
  ├─► Stop existing client if any
  ├─► Get ato binary path via getAtoBin()
  ├─► Spawn: `ato lsp start`
  ├─► Create LanguageClient
  └─► Start client
```

**Restart triggers:**
- `onDidChangeAtoBinInfoEvent` (binary path changed)
- `atopile.restart` command
- Configuration changes (`atopile.ato`, `atopile.from`)

### Backend Server (Python)

The Python backend (`ato serve`) provides:
- Build queue management
- Project/package discovery
- BOM/variables data
- WebSocket state broadcasting
- Health check endpoint (`GET /health`)

**Lifecycle:** Managed automatically by `BackendServerManager` in `backendServer.ts`:
- Auto-started when extension activates (hidden terminal)
- Restarted when atopile version changes
- Gracefully stopped when extension deactivates

**Connection:** WebSocket at `ws://127.0.0.1:<ephemeral>/ws/state`

**Health Check:** The extension polls `GET /health` during startup to verify server is ready.

---

## State Management

### WebSocket State Sync (appState-ws-standalone.ts)

```typescript
// Singleton that manages WebSocket connection
class WebSocketAppStateManager {
    private _state: AppState;
    private _ws: WebSocket;
    private _listeners: StateChangeListener[];

    // Receive state from Python backend
    onMessage(data) {
        if (message.type === 'state') {
            this._state = message.data;
            this._notifyListeners();
        }
    }

    // Send actions to Python backend
    sendAction(action: string, payload: object) {
        this._ws.send({ type: 'action', action, payload });
    }
}
```

### Settings Sync Flow

When user changes version in UI:

```
1. UI sends action: setAtopileVersion({ version: "0.9.0" })
   │
2. Python backend:
   ├─► Sets atopile.current_version = "0.9.0"
   ├─► Sets atopile.is_installing = true
   └─► Broadcasts state to all clients
   │
3. Extension receives state change:
   └─► initAtopileSettingsSync() updates VS Code settings
       └─► config.update('from', 'atopile@0.9.0')
   │
4. Config change triggers onDidChangeAtoBinInfoEvent
   │
5. Server restart:
   ├─► LSP server restarts with new version
   └─► Extension sends: setAtopileInstalling({ installing: false })
   │
6. UI spinner disappears
```

---

## Configuration

### VS Code Settings

```json
{
    "atopile.ato": "",           // Direct path to ato binary
    "atopile.from": "atopile",   // UV source (PyPI or git+URL)
    "atopile.autoInstall": true, // Auto-install UV/atopile
    "atopile.telemetry": true    // Send telemetry
}
```

The backend server is always extension-managed and bound to a per-session local port.

### Version Requirements

The extension enforces a minimum supported version for **release** installations:

- **Minimum version:** 0.14.0 (defined in `atopile_install.py`)
- **Releases:** Only versions >= 0.14.0 shown in dropdown
- **Branches:** All branches allowed (developers may need older code)
- **Local paths:** Any version allowed (for development)

### Extension State (AtopileConfig)

```typescript
interface AtopileConfig {
    source: 'release' | 'branch' | 'local';
    currentVersion: string;
    localPath: string | null;
    branch: string | null;
    availableVersions: string[];
    availableBranches: string[];
    isInstalling: boolean;
    installProgress: { message: string; percent?: number } | null;
    error: string | null;
}
```

---

## Event Flow

### Key Events

| Event | Source | Triggers |
|-------|--------|----------|
| `onDidChangeAtoBinInfoEvent` | findbin.ts | Server restart |
| `onNeedsRestart` | server.ts | LSP server restart |
| `onBuildTargetChanged` | target.ts | LSP notification |
| `onDidChangeConfiguration` | VS Code | Settings sync |

### Sequence Diagram: Version Change

```
┌─────┐     ┌─────────┐     ┌─────────┐     ┌──────────┐
│ UI  │     │ Python  │     │Extension│     │LSP Server│
└──┬──┘     └────┬────┘     └────┬────┘     └────┬─────┘
   │             │               │               │
   │ setVersion  │               │               │
   │────────────►│               │               │
   │             │ state{installing:true}        │
   │             │──────────────►│               │
   │◄────────────┼───────────────│               │
   │  spinner    │               │               │
   │             │               │ update config │
   │             │               │───────┐       │
   │             │               │◄──────┘       │
   │             │               │               │
   │             │               │ restart       │
   │             │               │──────────────►│
   │             │               │               │
   │             │               │◄──────────────│
   │             │               │    ready      │
   │             │ setInstalling(false)          │
   │             │◄──────────────│               │
   │◄────────────┼───────────────│               │
   │  done       │               │               │
```

---

## Adding New Features

### Adding a New Setting

1. Add to `package.json` contributes.configuration
2. Add to `ISettings` interface in `settings.ts`
3. Read in `getWorkspaceSettings()`
4. If UI-controlled, add to `AtopileConfig` in `dataclasses.py`

### Adding a New Action

1. Add handler in `actions.py` (`handle_data_action`)
2. Add state setter in `state.py` if needed
3. Add frontend action call in React component
4. Add TypeScript method in `appState-ws-standalone.ts` if called from extension

### Adding a New Webview Panel

1. Create panel class in `src/ui/`
2. Create React component in `src/ui-server/src/components/`
3. Register in `ui.ts` activate()
4. Add view contribution in `package.json`

---

## Debugging

### Extension Logs

```
Output Panel → "atopile" channel
```

### LSP Logs

```
Output Panel → "atopile" channel (verbose mode)
```

### Backend Server Logs

```
Terminal → "ato serve" terminal
```

### WebSocket Messages

Enable verbose logging:
```typescript
traceVerbose(`Sent action: ${action}`);
traceVerbose(`Action result: ${JSON.stringify(message)}`);
```

---

## Future Improvements

See `.claude/plans/bootstrap-architecture.md` for planned changes:

1. **Backend Server Management** - Auto-start/restart backend server
2. **Unified Version Management** - Single source of truth for version
3. **Update Notifications** - Check for updates on startup
