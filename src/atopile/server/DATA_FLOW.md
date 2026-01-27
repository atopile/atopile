# Server Data Flow Audit

Current state of WebSocket and HTTP usage across the server and frontend.

## Problem

Five different data flow patterns coexist with no consistent convention. The dominant pattern (empty WS notification -> HTTP refetch) means WebSocket adds no value over polling.

## Patterns in Use

### Pattern 1: Empty WS Event -> HTTP Refetch (dominant)

Server emits an event with no data. Frontend receives it and makes a full HTTP GET.

| WS Event | HTTP Endpoint(s) Hit |
|---|---|
| `builds_changed` | `GET /api/builds/history` + `GET /api/builds/active` |
| `projects_changed` | `GET /api/projects` |
| `packages_changed` | `GET /api/packages/summary` |
| `problems_changed` | `GET /api/problems` |
| `stdlib_changed` | `GET /api/stdlib` |
| `bom_changed` | `GET /api/bom` |
| `variables_changed` | `GET /api/variables` |

Emitters:
- `build_queue.py` -> `event_bus.emit_sync("builds_changed")`
- `server.py` -> `emit_event("stdlib_changed")`, `emit_event("bom_changed")`, etc.
- `problem_parser.py` -> `event_bus.emit_sync("problems_changed")`

Frontend handler (`eventHandler.ts`):
```ts
case 'builds_changed':
    await fetchBuilds();  // HTTP round-trip
    break;
```

### Pattern 2: WS Event with Metadata -> Still HTTP Refetch

Server sends a payload (e.g. `project_root`), but the frontend only uses it as a query parameter for an HTTP refetch.

| WS Event | Payload | HTTP Endpoint Hit |
|---|---|---|
| `project_files_changed` | `{project_root}` | `GET /api/files?project_root=X` |
| `project_modules_changed` | `{project_root}` | `GET /api/modules?project_root=X` |
| `project_dependencies_changed` | `{project_root}` | `GET /api/dependencies?project_root=X` |

Frontend handler:
```ts
case 'project_files_changed': {
    const projectRoot = detail.project_root ?? store.selectedProjectRoot;
    if (projectRoot) await fetchProjectFiles(projectRoot);  // HTTP
    break;
}
```

Note: Falls back to `store.selectedProjectRoot` if payload is missing, which may be stale.

### Pattern 3: WS Event with Error Info -> Partial Use + Refetch

`packages_changed` sends `{error, package_id}` on install failure. Frontend uses the error info directly but still refetches.

```ts
case 'packages_changed':
    if (typeof detail.error === 'string') {
        store.setInstallError(detail.package_id, detail.error);  // uses payload
    }
    await fetchPackages();  // still refetches
    break;
```

### Pattern 4: WS Event with Full Payload -> Direct State Update (no HTTP)

These events send complete data and the frontend applies it directly.

| WS Event | Payload |
|---|---|
| `atopile_config_changed` | `{source, currentVersion, branch, localPath, available_versions, available_branches, detected_installations, isInstalling, installProgress, error}` |
| `open_file` | `{path, line, column}` |
| `open_layout` | `{path}` |
| `open_kicad` | `{path}` |
| `open_3d` | `{path}` |

The `open_*` events are action commands (not state updates) forwarded to the VS Code extension via `postMessage`.

### Pattern 5: Separate WS Channel with Streaming

`/ws/logs` is a dedicated WebSocket endpoint with bidirectional request/response semantics. Client sends `{build_id, subscribe: true}`, server pushes log entries with cursor tracking (`after_id`). Actual data flows over WS.

## HTTP Endpoints

### State Queries (triggered by WS events)

| Endpoint | Triggered By |
|---|---|
| `GET /api/projects` | `projects_changed` |
| `GET /api/builds/history` | `builds_changed` |
| `GET /api/builds/active` | `builds_changed` |
| `GET /api/packages/summary` | `packages_changed` |
| `GET /api/problems` | `problems_changed` |
| `GET /api/stdlib` | `stdlib_changed` |
| `GET /api/bom` | `bom_changed` |
| `GET /api/variables` | `variables_changed` |
| `GET /api/files` | `project_files_changed` |
| `GET /api/modules` | `project_modules_changed` |
| `GET /api/dependencies` | `project_dependencies_changed` |

### Actions (HTTP POST, no WS equivalent)

| Endpoint | Purpose |
|---|---|
| `POST /api/build` | Start a build |
| `POST /api/build/{id}/cancel` | Cancel a build |
| `POST /api/packages/install` | Install a package |
| `POST /api/packages/uninstall` | Uninstall a package |

### Direct Lookups (no WS trigger)

| Endpoint | Purpose |
|---|---|
| `GET /api/build/{id}/status` | Poll single build status |
| `GET /api/build/{id}/info` | Get build metadata |
| `GET /api/build/{id}/bom` | Get BOM for a specific build |
| `GET /api/build/{id}/variables` | Get variables for a specific build |
| `GET /api/builds?project_root=&target=` | Query builds by project/target |
| `GET /api/registry/search` | Search package registry |

### Streaming

| Endpoint | Purpose |
|---|---|
| `WS /ws/logs` | Bidirectional log streaming |

## Frontend Initial Load

On page load, `fetchInitialData()` fires these HTTP calls in parallel (no WS involved):

```ts
await Promise.all([
    fetchProjects(),    // GET /api/projects
    fetchBuilds(),      // GET /api/builds/history + /api/builds/active
    fetchPackages(),    // GET /api/packages/summary
    fetchProblems(),    // GET /api/problems
    fetchStdlib(),      // GET /api/stdlib
]);
```

## Event Emission Sources

| Location | Events Emitted |
|---|---|
| `server.py` (file watchers) | `stdlib_changed`, `bom_changed`, `variables_changed`, `project_files_changed`, `project_modules_changed`, `project_dependencies_changed`, `projects_changed` |
| `build_queue.py` | `builds_changed` |
| `problem_parser.py` | `problems_changed` |
| `domains/actions.py` | `open_file`, `open_layout`, `open_kicad`, `open_3d` |
| `domains/packages.py` | `packages_changed` |
| `domains/atopile_config.py` | `atopile_config_changed` |
