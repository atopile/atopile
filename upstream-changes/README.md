# Upstream Changes from feature/fabll_part2

These files were extracted from `origin/feature/fabll_part2` commit `ef41ce05b` ("logging server improvements").

## Files to Review

### NEW FILES (can be added directly)

| File | Description | Action |
|------|-------------|--------|
| `serve.py` | New CLI command `ato serve start/stop/status` | Add to `src/atopile/cli/` |
| `backendServer.ts` | Backend server client with health monitoring | Add to `src/vscode-atopile/src/common/` |

### CHANGED FILES (need careful integration)

| File | Key Changes | Integration Notes |
|------|-------------|-------------------|
| `server.py` | WebSocket manager, log streaming, `/api/build` | Port WebSocket classes to our comprehensive server.py |
| `appState.ts` | WebSocket client, `isBackendRunning`, log subscription | Merge with our `packagesError` and `fetchPackages` changes |
| `Sidebar.tsx` | Server status button, removed `onBuild` prop | Merge with our `warningMessage` on packages section |
| `Sidebar.css` | Server status indicator styles | Add new styles |
| `LogViewer.tsx` | Simplified filter UI, client-side filtering | Review filtering approach |
| `LogViewer.css` | Minor style updates | Merge styles |
| `build.ts` | Added `project_path`, `timestamp` to Build type | Merge with our `PackageSummaryItem` types |
| `build.py` | Early build summaries for faster UI feedback | Review and integrate |
| `buttons.ts` | Server button registration | Add server button |
| `BuildTargetItem.tsx` | Removed onBuild callback | Review changes |

## Key Features to Integrate

### 1. WebSocket Log Streaming (server.py)
```python
# Classes to port:
- ConnectionManager (WebSocket client management)
- LogSubscription (per-client filter settings)
- ClientState (client state tracking)
- _stream_logs_to_client() (async log streaming)
- /ws endpoint (WebSocket handler)
```

### 2. Build Execution API (server.py)
```python
# Endpoints to add:
- POST /api/build (start build via API)
- DELETE /api/build/{build_id} (cancel build)
- POST /api/config (configure ato binary)
- BuildRequest, BuildProcess models
```

### 3. Server Status UI (Sidebar.tsx, appState.ts)
```typescript
// State to add:
- isBackendRunning: boolean
- setBackendRunning(running: boolean)

// UI to add:
- Server status indicator (green/red dot)
- "Start Server" button when not running
```

### 4. CLI Command (serve.py)
```bash
ato serve start [--port] [--force]
ato serve stop [--port]
ato serve status [--port]
```

## Integration Order

1. **serve.py** - New file, add directly
2. **backendServer.ts** - New file, add directly
3. **server.py** - Port WebSocket classes to our existing server
4. **appState.ts** - Add `isBackendRunning` and WebSocket connection
5. **Sidebar.tsx/css** - Add server status UI
6. **build.ts** - Add new Build type fields
7. **LogViewer.tsx** - Review filter changes
8. **build.py** - Add early build summary feature

## What We Keep from Our Branch

- `/api/packages/summary` endpoint
- `packagesError` state and UI
- `warningMessage` on CollapsibleSection
- All package-related API endpoints
- dev-server.ts WebSocket implementation
