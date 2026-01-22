# VS Code Extension Debugging Investigation Summary

## Issues Reported

1. Builds not triggering - build counter starts briefly, targets added to queue, but build does not complete
2. Search for modules (entry point picker) shows no suggestions
3. Files and dependencies in packages not displayed
4. Delete build targets doesn't work
5. Add build button doesn't work
6. Open ato, kicad, layout, 3d buttons don't work
7. Install packages button doesn't work
8. Standard library items all expanded by default
9. Create project button doesn't work
10. Rename project doesn't work
11. Rename build target doesn't work

---

## Investigation Findings

### Issue 6: Open buttons (ato, kicad, layout, 3d) - ROOT CAUSE FOUND

**Problem**: The action handlers in `actions.py` call methods that don't exist:
```python
await server_state.set_open_file(file_path, line, column)
await server_state.set_open_layout(layout_path)
await server_state.set_open_kicad(kicad_path)
await server_state.set_open_3d(model_path)
```

These methods were missing from `state.py`, causing `AttributeError` when the actions were triggered.

**Fix Applied**:
- Added the missing methods to `src/atopile/server/state.py`
- Added corresponding fields to `AppState` in `src/atopile/dataclasses.py`
- Added signal handler in `src/vscode-atopile/src/common/appState-ws-standalone.ts` to listen for these state changes and open files/apps

### Issue 8: Standard library items expanded - ROOT CAUSE FOUND

**Problem**: The `StdLibCard` component always renders children regardless of selection state.

**Fix Applied**: Modified `src/ui-server/src/components/StandardLibraryPanel.tsx` to only show children, description, and usage when the card is selected (clicked).

### Issues 1-5, 7, 9-11: Action Flow Analysis

The action flow appears correct:

1. **Frontend** (`useSidebarHandlers.ts`) sends action via WebSocket:
   ```typescript
   action('addBuildTarget', { project_root, name, entry })
   ```

2. **Backend** (`actions.py`) receives and processes:
   ```python
   if action == "addBuildTarget":
       result = await asyncio.to_thread(
           projects_domain.handle_add_build_target,
           projects_domain.AddBuildTargetRequest(**data),
       )
   ```

3. **Domain handler** (`projects.py`) executes the operation

4. **State update** is broadcast to all connected clients

**Potential Issues**:
- Exceptions may be caught and returned as `{"success": False, "error": "..."}` but not logged
- State updates may not be triggering re-renders
- Event loop issues in async/thread interactions

---

## Files Changed

| File | Changes |
|------|---------|
| `src/atopile/server/state.py` | Added `set_open_file()`, `set_open_layout()`, `set_open_kicad()`, `set_open_3d()` methods |
| `src/atopile/dataclasses.py` | Added `open_file`, `open_file_line`, `open_file_column`, `open_layout`, `open_kicad`, `open_3d` fields to `AppState` |
| `src/vscode-atopile/src/common/appState-ws-standalone.ts` | Added `_handleOpenSignals()` method and updated `AppState` interface |
| `src/ui-server/src/components/StandardLibraryPanel.tsx` | Made StdLibCard children/details only show when selected |

---

## How to Test

1. **Restart the backend server**:
   ```bash
   # Kill existing server and restart
   ato serve backend
   ```

2. **Reload VS Code**:
   - Press `Cmd+Shift+P` → "Developer: Reload Window"
   - Or restart VS Code entirely

3. **Test each feature**:
   - Open buttons: Expand a build target, click ato/kicad/layout/3d buttons
   - Standard library: Expand the Standard Library section, verify items are collapsed
   - Build: Click play button on a build target
   - Add build: Expand a project, click the + button

---

## Debugging Steps If Still Not Working

### Step 1: Check Browser Console (DevTools)

In VS Code, open the webview DevTools:
1. Press `Cmd+Shift+P` → "Developer: Open Webview Developer Tools"
2. Check the Console tab for errors
3. Look for:
   - WebSocket connection errors
   - Action send/receive logs
   - JavaScript errors

### Step 2: Check Backend Server Logs

The server logs to the terminal where `ato serve backend` is running.

**Add more verbose logging** by setting environment variable:
```bash
ATOPILE_LOG_LEVEL=DEBUG ato serve backend
```

Look for:
- Action received messages
- Errors in action handlers
- Build queue status

### Step 3: Add Debug Logging to Actions

Edit `src/atopile/server/domains/actions.py` to add logging at key points:

```python
# At the start of handle_action:
log.info(f"=== ACTION RECEIVED: {action} ===")
log.info(f"Payload: {payload}")

# In each action handler, log before and after:
if action == "addBuildTarget":
    log.info("Processing addBuildTarget...")
    try:
        # ... existing code ...
        log.info(f"addBuildTarget result: {result}")
    except Exception as exc:
        log.error(f"addBuildTarget FAILED: {exc}", exc_info=True)
```

### Step 4: Check WebSocket Message Flow

In `src/ui-server/src/api/websocket.ts`, add logging:

```typescript
export function sendAction(name: string, data?: Record<string, unknown>) {
  console.log('[WS] Sending action:', name, data);
  // ... existing code ...
}

// In the message handler:
ws.onmessage = (event) => {
  console.log('[WS] Received:', event.data);
  // ... existing code ...
};
```

### Step 5: Verify State Updates Are Broadcasting

Check if state changes are being broadcast by adding to `state.py`:

```python
async def broadcast_state(self) -> None:
    log.info(f"Broadcasting state to {len(self._websockets)} clients")
    # ... existing code ...
```

### Step 6: Check for camelCase/snake_case Mismatches

The frontend uses camelCase, backend uses snake_case. Verify:

1. Frontend sends correct keys in action payload
2. Backend Pydantic models accept both (via aliases) or match expected format

Example check in `useSidebarHandlers.ts`:
```typescript
// This sends snake_case (correct):
sendActionWithResponse('addBuildTarget', {
  project_root: projectId,  // snake_case
  name: newName,
  entry: defaultEntry,
});
```

### Step 7: Build Queue Specific Debugging

For build issues, check:

1. **Is the build queue starting?**
   ```python
   # In build_queue.py, add logging in start():
   log.info("=== BUILD QUEUE STARTING ===")
   ```

2. **Is the event loop available?**
   ```python
   # In _sync_builds_to_state():
   loop = server_state._event_loop
   log.info(f"Event loop: {loop}, running: {loop.is_running() if loop else 'N/A'}")
   ```

3. **Is the build subprocess running?**
   ```python
   # In _run_build():
   log.info(f"Starting build subprocess for {build_id}")
   ```

---

## Architecture Quick Reference

```
┌─────────────────────────────────────────────────────────────┐
│                     VS Code Extension                        │
│  ┌─────────────────┐    ┌──────────────────────────────┐   │
│  │ SidebarProvider │────│ appState-ws-standalone.ts    │   │
│  │                 │    │ (WebSocket client)           │   │
│  └─────────────────┘    └──────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │ WebSocket
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     Python Backend                           │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────┐ │
│  │ server.py   │────│ actions.py  │────│ domains/*.py    │ │
│  │ (FastAPI)   │    │ (handlers)  │    │ (business logic)│ │
│  └─────────────┘    └─────────────┘    └─────────────────┘ │
│         │                                                    │
│         ▼                                                    │
│  ┌─────────────┐    ┌─────────────────────────────────────┐ │
│  │ state.py    │────│ Broadcasts state to all WS clients │ │
│  │ (AppState)  │    └─────────────────────────────────────┘ │
│  └─────────────┘                                            │
└─────────────────────────────────────────────────────────────┘
```

### Key Files:

| Component | File |
|-----------|------|
| WebSocket client (extension) | `src/vscode-atopile/src/common/appState-ws-standalone.ts` |
| WebSocket client (React UI) | `src/ui-server/src/api/websocket.ts` |
| Action handlers | `src/atopile/server/domains/actions.py` |
| State management | `src/atopile/server/state.py` |
| Build queue | `src/atopile/server/build_queue.py` |
| Project operations | `src/atopile/server/domains/projects.py` |
| React sidebar | `src/ui-server/src/components/Sidebar.tsx` |
| Sidebar handlers | `src/ui-server/src/components/sidebar-modules/useSidebarHandlers.ts` |

---

## Common Issues Checklist

- [ ] Backend server is running (`ato serve backend`)
- [ ] WebSocket connection is established (check browser console)
- [ ] No Python exceptions in backend logs
- [ ] State broadcasts are being sent
- [ ] Frontend is receiving state updates
- [ ] Actions are being sent with correct payload format
- [ ] Event loop is set in server_state (check on_startup in server.py)

---

## UI Crash Robustness Improvements

The UI disappearing/crashing is unacceptable UX. Here are the improvements needed:

### 1. Add React Error Boundaries

The React app needs error boundaries to catch component crashes and show a fallback UI instead of a blank screen.

**Create `src/ui-server/src/components/ErrorBoundary.tsx`:**
```tsx
import React, { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('[ErrorBoundary] Caught error:', error, errorInfo);
    this.props.onError?.(error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <div className="error-boundary-fallback">
          <h3>Something went wrong</h3>
          <p>{this.state.error?.message}</p>
          <button onClick={() => this.setState({ hasError: false, error: null })}>
            Try Again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
```

**Wrap components in Sidebar.tsx:**
```tsx
<ErrorBoundary fallback={<div>Projects failed to load</div>}>
  <ProjectsPanel ... />
</ErrorBoundary>
```

### 2. Defensive State Access

Never trust that state properties exist. Always use optional chaining and defaults:

```tsx
// BAD - can crash if state.projects is undefined
const count = state.projects.length;

// GOOD - defensive access
const count = state?.projects?.length ?? 0;

// BAD - can crash on map of undefined
state.projects.map(p => ...)

// GOOD - defensive with fallback
(state?.projects ?? []).map(p => ...)
```

### 3. WebSocket Reconnection with Backoff

The WebSocket connection should auto-reconnect with exponential backoff:

**In `appState-ws-standalone.ts`:**
```typescript
class WebSocketAppStateManager {
  private _reconnectAttempts = 0;
  private _maxReconnectAttempts = 10;
  private _baseDelay = 1000;

  private _scheduleReconnect(): void {
    if (this._reconnectAttempts >= this._maxReconnectAttempts) {
      console.error('[WS] Max reconnect attempts reached');
      return;
    }

    const delay = Math.min(
      this._baseDelay * Math.pow(2, this._reconnectAttempts),
      30000 // Max 30 seconds
    );

    this._reconnectAttempts++;
    console.log(`[WS] Reconnecting in ${delay}ms (attempt ${this._reconnectAttempts})`);

    setTimeout(() => this.connect(), delay);
  }

  private _onConnected(): void {
    this._reconnectAttempts = 0; // Reset on successful connection
  }
}
```

### 4. Try/Catch in All Handlers

Every event handler should be wrapped in try/catch:

```typescript
// BAD - uncaught error crashes the component
const handleClick = () => {
  const result = riskyOperation();
  setState(result);
};

// GOOD - errors are caught and logged
const handleClick = () => {
  try {
    const result = riskyOperation();
    setState(result);
  } catch (error) {
    console.error('handleClick failed:', error);
    // Optionally show user feedback
  }
};
```

### 5. Validate Incoming State

Before applying state updates, validate the structure:

```typescript
private _handleStateUpdate(newState: unknown): void {
  // Validate it's an object
  if (!newState || typeof newState !== 'object') {
    console.error('[WS] Invalid state received:', newState);
    return;
  }

  // Validate critical fields exist
  const state = newState as Partial<AppState>;

  // Apply with defaults for missing fields
  this._state = {
    ...DEFAULT_STATE,
    ...state,
    isConnected: true,
    // Ensure arrays are arrays
    projects: Array.isArray(state.projects) ? state.projects : [],
    packages: Array.isArray(state.packages) ? state.packages : [],
  };

  this._notifyListeners();
}
```

### 6. Graceful Degradation for Missing Data

Components should render something useful even with missing data:

```tsx
function ProjectsPanel({ projects }: Props) {
  // Handle loading state
  if (!projects) {
    return <div className="loading">Loading projects...</div>;
  }

  // Handle empty state
  if (projects.length === 0) {
    return <div className="empty">No projects found</div>;
  }

  // Handle error state
  if (projects.some(p => p === null || p === undefined)) {
    console.warn('Some projects are null/undefined, filtering...');
    projects = projects.filter(Boolean);
  }

  return (
    <div>
      {projects.map(project => (
        <ProjectNode key={project?.id ?? Math.random()} project={project} />
      ))}
    </div>
  );
}
```

### 7. Global Error Handler

Add a global error handler to catch uncaught errors:

**In `src/ui-server/src/main.tsx`:**
```typescript
window.onerror = (message, source, lineno, colno, error) => {
  console.error('[Global Error]', { message, source, lineno, colno, error });
  // Could send to error tracking service
  return false; // Let default handler also run
};

window.onunhandledrejection = (event) => {
  console.error('[Unhandled Promise Rejection]', event.reason);
};
```

### 8. Zustand Store Safety

If using Zustand, add middleware for safety:

```typescript
import { create } from 'zustand';
import { devtools } from 'zustand/middleware';

const useStore = create(
  devtools(
    (set, get) => ({
      // ... state

      // Safe setter that validates before updating
      safeUpdate: (partial: Partial<State>) => {
        try {
          set(partial);
        } catch (error) {
          console.error('Store update failed:', error);
        }
      },
    }),
    { name: 'AtopileStore' }
  )
);
```

### 9. Component-Level Loading States

Each section should handle its own loading/error states independently:

```tsx
function StandardLibraryPanel({ items, isLoading, error }) {
  if (error) {
    return (
      <div className="panel-error">
        <span>Failed to load: {error}</span>
        <button onClick={onRetry}>Retry</button>
      </div>
    );
  }

  if (isLoading) {
    return <div className="panel-loading">Loading...</div>;
  }

  if (!items || items.length === 0) {
    return <div className="panel-empty">No items</div>;
  }

  return <div>{/* render items */}</div>;
}
```

### 10. Crash Recovery State

Store minimal recovery state in localStorage:

```typescript
// On crash, save what section was open
window.onerror = () => {
  localStorage.setItem('atopile_crash_recovery', JSON.stringify({
    timestamp: Date.now(),
    lastSection: currentSection,
    selectedProject: selectedProjectRoot,
  }));
};

// On load, check for crash recovery
useEffect(() => {
  const recovery = localStorage.getItem('atopile_crash_recovery');
  if (recovery) {
    const data = JSON.parse(recovery);
    // If crash was recent (< 1 min ago), maybe start in safe mode
    if (Date.now() - data.timestamp < 60000) {
      console.warn('Recent crash detected, starting in safe mode');
      setCollapsedSections(new Set(['all'])); // Collapse everything
    }
    localStorage.removeItem('atopile_crash_recovery');
  }
}, []);
```

---

## Priority Robustness Fixes

**High Priority (implement first):**
1. Error boundaries around each major section
2. Try/catch in all handlers
3. Defensive state access with `?.` and `?? []`
4. WebSocket reconnection logic

**Medium Priority:**
1. Validate incoming state structure
2. Component-level loading/error states
3. Global error handler

**Lower Priority:**
1. Crash recovery state
2. Error tracking integration
3. Safe mode after repeated crashes
