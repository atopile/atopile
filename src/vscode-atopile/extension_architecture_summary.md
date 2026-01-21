# Atopile Dashboard Architecture

## Overview

The dashboard is a VS Code extension webview that provides a UI for managing atopile builds, viewing logs, browsing packages, and exploring the standard library. It uses a two-tier architecture:

```
┌─────────────────────────────────────────────────────────────────────┐
│                         React UI (Vite)                             │
│                    http://localhost:5173                            │
│   Sidebar, BuildQueuePanel, LogViewer, ProblemsPanel, BOMPanel     │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ REST + WebSocket
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Python Backend (FastAPI)                         │
│                    http://localhost:8501                            │
│    Single source of truth: builds, logs, projects, packages         │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Running the Dev Environment

```bash
cd src/ui-server
./dev.sh /path/to/workspace1 /path/to/workspace2

# This starts:
# - Python backend on :8501
# - Vite on :5173
```

Open http://localhost:5173 to see the UI.

---

## Build System

The build system is the core feature. Here's how it works end-to-end.

### Build Flow

```
┌─────────┐     POST /api/build      ┌─────────────┐
│   UI    │ ──────────────────────►  │   Backend   │
│         │  {project_root, targets} │             │
└────┬────┘                          └──────┬──────┘
     │                                      │
     │  Response: {build_id, status:"queued"}
     │ ◄────────────────────────────────────┤
     │                                      │
     │  UI calls fetchBuilds()              │  Add to _active_builds
     │  (renders whatever backend returns)  │  Add to BuildQueue (max 4)
     │                                      │
     │                                      ▼
     │                               ┌──────────────┐
     │   WS: build:started           │ Worker picks │
     │ ◄──────────────────────────── │ from queue   │
     │   → triggers fetchBuilds()    └──────┬───────┘
     │                                      │
     │   WS: build:stage (repeated)         │ Polls summary.json
     │ ◄──────────────────────────────────  │ every 500ms
     │   → triggers fetchBuilds()           │
     │                                      │
     │   WS: build:completed                │ Subprocess done
     │ ◄──────────────────────────────────  │ Status updated in _active_builds
     │   → triggers fetchBuilds()           │
     │                                      │
     ▼                                      ▼
  Re-renders with new state          Save to SQLite history
  (backend is source of truth)       (builds stay in _active_builds)
```

### Key Concepts

**BuildQueue** - Limits concurrent builds to 4. Builds are queued with status "queued" until a slot opens, then transition to "building".

**Deduplication** - If you trigger the same build twice (same project + targets), the second request returns the existing build_id instead of creating a duplicate.

**Real-time Stages** - While a build runs, the backend polls `summary.json` (written by `ato build` CLI every 500ms) and broadcasts `build:stage` events as stages complete.

**Build History** - Completed builds are saved to SQLite (`build_history.db`) so history persists across server restarts.

### State Management

**Backend State (Single Source of Truth):**
```python
_active_builds: dict[str, dict]  # ALL tracked builds (queued/building/completed/cancelled)
_build_queue: BuildQueue         # Manages concurrency (max 4)
_build_lock: threading.Lock      # Thread-safe access
```

**Frontend State (AppState) - Display Only:**
```typescript
builds: Build[]        // All builds from /api/summary (for Projects panel)
queuedBuilds: Build[]  // Filtered to queued/building from /api/builds/active (for Queue panel)
```

> **Note:** The frontend does NOT maintain separate state. It fetches from the backend and renders. See [Stateless Frontend Architecture](#stateless-frontend-architecture) for details.

### Build Record Fields

| Field | Type | Description |
|-------|------|-------------|
| `build_id` | str | Unique ID like `build-1-1234567890` |
| `status` | str | `queued` → `building` → `success`/`failed`/`cancelled` |
| `build_key` | str | Content hash for deduplication |
| `project_root` | str | Absolute path to project |
| `targets` | list[str] | Build target names |
| `process` | Popen \| None | Subprocess reference (for cancellation) |
| `stages` | list[dict] | Current stage progress |
| `return_code` | int \| None | Exit code after completion |
| `error` | str \| None | Error message on failure |
| `started_at` | float | Unix timestamp |

---

## WebSocket Events

| Event | Direction | When | Data |
|-------|-----------|------|------|
| `build:started` | Server→Client | Build transitions queued→building | `{build_id, project_root, targets, status}` |
| `build:stage` | Server→Client | Stage status changes | `{build_id, stage_name, display_name, status}` |
| `build:completed` | Server→Client | Build finishes | `{build_id, status, return_code, stages}` |
| `logs` | Server→Client | New log entries | `{logs: [...], total, incremental}` |
| `summary:updated` | Server→Client | Summary file changed | `{}` |
| `problems:updated` | Server→Client | Problems changed | `{}` |

---

## REST API Endpoints

### Build Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/build` | POST | Start a build (returns immediately with build_id) |
| `/api/build/{id}/status` | GET | Get build status |
| `/api/build/{id}/cancel` | POST | Cancel a running/queued build |
| `/api/builds/active` | GET | List all active builds (for queue panel) |
| `/api/builds/queue` | GET | Get queue status (debugging) |
| `/api/builds/history` | GET | Query historical builds from SQLite |
| `/api/summary` | GET | Get build summary from summary.json |

### Projects & Packages

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/projects` | GET | Discover projects from workspace paths |
| `/api/modules` | GET | List modules in a project |
| `/api/packages` | GET | List installed packages |
| `/api/packages/install` | POST | Install a package |
| `/api/packages/remove` | POST | Remove a package |
| `/api/registry/search` | GET | Search package registry |

### Logs & Problems

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/logs/query` | GET | Query logs with filtering/pagination |
| `/api/problems` | GET | Parse errors/warnings from logs |

### Other

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/bom` | GET | Get Bill of Materials for a build |
| `/api/variables` | GET | Get parameter/variable values |
| `/api/stdlib` | GET | Get standard library items |

---

## UI Components

| Component | File | Purpose |
|-----------|------|---------|
| Sidebar | `Sidebar.tsx` | Main container, orchestrates all panels |
| BuildQueuePanel | `BuildQueuePanel.tsx` | Shows queued/building builds with cancel buttons |
| ProjectsPanel | `ProjectsPanel.tsx` | Project tree, build targets, status indicators |
| LogViewer | `LogViewer.tsx` | Filterable build logs with level badges |
| ProblemsPanel | `ProblemsPanel.tsx` | Errors/warnings from builds |
| BOMPanel | `BOMPanel.tsx` | Bill of Materials view |
| StandardLibraryPanel | `StandardLibraryPanel.tsx` | Browse stdlib modules/interfaces |
| PackageDetailPanel | `PackageDetailPanel.tsx` | Package info and installation |

---

## File Structure

```
src/atopile/dashboard/
├── server.py          # FastAPI backend
├── stdlib.py          # Standard library introspection
└── __main__.py        # Entry point for standalone server

src/vscode-atopile/webviews/
├── dev.sh             # Start dev environment
├── server/
│   └── dev-server.ts  # TypeScript dev server
├── src/
│   ├── components/    # React components
│   ├── types/         # TypeScript types (build.ts is source of truth)
│   └── __tests__/     # Vitest tests
├── package.json
└── vite.config.ts
```

---

## Testing

```bash
# Python tests (includes build queue tests)
uv run pytest test/test_dashboard_server.py -v

# TypeScript tests
cd src/vscode-atopile/webviews
npm test
```

Key test classes:
- `TestBuildQueue` - Queue initialization, enqueueing, concurrency
- `TestBuildDeduplication` - Build key generation, duplicate detection
- `TestBuildQueueEndToEnd` - Full start→cancel flow via API

---

## Stateless Frontend Architecture

### Philosophy

**The frontend is a thin rendering layer.** All business logic, state management, and data transformation happens in the backend. The frontend's only jobs are:

1. **Render** what the backend sends
2. **Send commands** when the user clicks buttons

This is sometimes called "dumb UI" or "passive view" architecture. The backend is the **single source of truth** for all state.

### Why This Matters

When the frontend tries to be smart, bugs multiply:

- **Synchronization issues**: Frontend and backend state drift apart
- **Race conditions**: Async updates arrive out of order
- **Duplicate logic**: Same transformation in Python and TypeScript
- **Debugging nightmares**: "Is the bug in the frontend or backend?"

With a stateless frontend, there's only one place to look: the backend.

### Core Principles

| Principle | Do This | Not This |
|-----------|---------|----------|
| **Data transformation** | Backend formats data ready-to-render | Frontend transforms/filters/sorts |
| **State derivation** | Backend computes derived values | Frontend calculates from raw data |
| **Event handling** | Frontend triggers fetch, renders result | Frontend updates local state from event |
| **Caching** | Backend caches, frontend just displays | Frontend maintains its own cache |

### Best Practices (with examples)

#### 1. Backend provides display-ready data

**Good** - Backend formats the build queue:
```python
# server.py - /api/builds/active
builds.append({
    "build_id": bid,
    "status": b["status"],
    "display_name": f"{project_name}:{target_name}",  # Pre-formatted!
    "elapsed_seconds": elapsed,  # Pre-calculated!
    "stages": b.get("stages", []),
})
# Sort on backend
builds.sort(key=lambda x: (x["status"] != "building", x.get("queue_position") or 999))
```

**Good** - Frontend just renders:
```tsx
// BuildQueuePanel.tsx
export function BuildQueuePanel({ builds, onCancelBuild }) {
  // STATELESS: Backend provides pre-filtered, pre-sorted queue data
  // Just render what we receive - no frontend logic needed
  return (
    <div className="build-queue-panel">
      {builds.map(build => (
        <BuildQueueItem key={build.build_id} build={build} ... />
      ))}
    </div>
  );
}
```

#### 2. Events trigger fetches, not state updates

**Good** - WebSocket event triggers a fetch:
```typescript
// dev-server.ts
private handleBuildCompletedEvent(data: any): void {
  // Don't try to update state from event data
  // Just fetch fresh state from backend
  this.fetchBuilds();
}
```

**Bad** - Event handler tries to update local state:
```typescript
// DON'T DO THIS
private handleBuildCompletedEvent(data: any): void {
  // Trying to be clever with local state updates
  const build = this.state.activeBuilds.find(b => b.build_id === data.build_id);
  if (build) {
    build.status = data.status;  // Now state can drift from backend!
    build.stages = data.stages;
  }
  this.state.activeBuilds = this.state.activeBuilds.filter(b =>
    b.status === 'queued' || b.status === 'building'
  );
  // What if the fetch and event arrive out of order? Bugs!
}
```

#### 3. Single helper for matching logic

**Good** - One function, used everywhere:
```typescript
// Sidebar.tsx
function findBuildForTarget(
  builds: Build[],
  projectName: string,
  targetName: string
): Build | undefined {
  // Single source of truth for build matching
  let build = builds.find(b => {
    if (b.status !== 'building' && b.status !== 'queued') return false;
    const buildProjectName = b.project_name || ...;
    if (buildProjectName !== projectName) return false;
    const targets = b.targets || [];
    return targets.length > 0 ? targets.includes(targetName) : b.name === targetName;
  });

  if (!build) {
    build = builds.find(b => b.name === targetName && ...);
  }
  return build;
}

// Used by both projects and packages
const transformedProjects = useMemo(() => {
  ...
  const build = findBuildForTarget(state.builds, p.name, t.name);
  ...
});

const transformedPackages = useMemo(() => {
  ...
  const build = findBuildForTarget(state.builds, pkg.name, targetName);
  ...
});
```

**Bad** - Duplicate logic that drifts apart:
```typescript
// DON'T DO THIS - same logic duplicated and slightly different
const transformedProjects = useMemo(() => {
  let build = state.builds.find(b => {
    // Logic A
    if (b.status !== 'building') return false;  // Forgot 'queued'!
    return b.targets?.includes(t.name);
  });
});

const transformedPackages = useMemo(() => {
  let build = state.builds.find(b => {
    // Logic B - subtly different
    if (b.status === 'building' || b.status === 'queued') {
      return b.target_names?.includes(targetName);  // Wrong field name!
    }
  });
});
```

#### 4. Backend tracks all build states

**Good** - Backend keeps completed builds in memory:
```python
# server.py - /api/summary
# Include ALL tracked builds, not just active ones
with _build_lock:
    for build_id, build_info in _active_builds.items():
        # Returns queued, building, success, failed, AND cancelled
        tracked_build = {
            "build_id": build_id,
            "status": build_info["status"],  # Whatever it is
            "stages": build_info.get("stages", []),
            ...
        }
        all_builds.insert(0, tracked_build)
```

**Bad** - Only returning active builds, losing state:
```python
# DON'T DO THIS
for build_id, build_info in _active_builds.items():
    if build_info["status"] in ("queued", "building"):  # Filters out completed!
        ...
# Result: Completed builds disappear from UI immediately
# Frontend can't show final status or stages
```

### Anti-Pattern: The "Smart Frontend" That Broke

Here's a real bug we had when the frontend tried to be smart:

**The Problem**: Both "default" and "usage" targets showed "building" status, even though only one was actually building.

**Root Cause**: Frontend was using `activeBuilds` (a separate list) and trying to match builds to targets with incomplete logic:
```typescript
// The buggy approach
const transformedPackages = useMemo(() => {
  const packageBuilds = targetNames.map(targetName => {
    // Always returning 'idle' because matching logic was wrong
    return { status: 'idle', ... };  // Oops, never found the build!
  });
});
```

**The Fix**: Use `state.builds` (the single source of truth) with the unified `findBuildForTarget` helper.

### Anti-Pattern: Event-Driven State Updates

**The Problem**: Build status disappeared after completion.

**Root Cause**: The `build:completed` event triggered removal from `activeBuilds`, but the backend's `/api/summary` was filtering to only return `queued`/`building` builds:

```python
# Backend only returned active builds
if build_info["status"] in ("queued", "building"):
    all_builds.append(...)
# Completed builds vanished!
```

**The Fix**: Backend returns ALL tracked builds. Frontend doesn't need to track which builds are "active" vs "completed" - it just renders whatever the backend sends.

### Checklist for New Features

When adding UI features, ask yourself:

- [ ] Can the backend pre-compute this value?
- [ ] Am I duplicating logic that exists elsewhere?
- [ ] Does the frontend need to "remember" anything, or can it just fetch?
- [ ] If an event arrives, do I need its data, or should I just re-fetch?
- [ ] Is there a single helper function for this logic?

If you're writing `filter()`, `sort()`, or `map()` with business logic in the frontend, consider moving it to the backend.

---

## Tips for Contributors

1. **Types live in one place** - `src/vscode-atopile/webviews/src/types/build.ts` is the source of truth for TypeScript types. Don't duplicate.

2. **Backend changes require restart** - The dev server auto-starts the backend, so restart `./dev.sh`.

3. **WebSocket debugging** - Add `console.log` in `dev-server.ts` message handlers. Backend logs to stdout.

4. **State batching** - `queueUpdate()` debounces state broadcasts to avoid overwhelming the UI.

5. **Build queue panel** - Shows `queuedBuilds` (queued + building only). Completed builds appear in the projects panel with their final status.

---

## Known Issues / Future Work

1. **WebSocket reconnection** - Frontend doesn't automatically reconnect if backend restarts.

2. **Log streaming during builds** - Logs appear after stages complete, not line-by-line during stage execution.

3. **VS Code integration** - Dev server is for browser testing; actual extension uses VS Code webview APIs directly.
