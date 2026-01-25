# Merge Plan: feature/fabll_part2 → feature/extension-websocket-refactor

## Summary

The two branches have diverged significantly with different architectural directions:

- **feature/fabll_part2**: Simplified architecture, centralized logging DB, per-target build summaries, stripped-down UI
- **feature/extension-websocket-refactor** (ours): Rich UI with WebSocket real-time updates, build queue, parallel builds from dashboard, file explorer

## Key Changes in feature/fabll_part2

### 1. Logging Architecture (TAKE THEIRS)
- Centralized log database via `get_central_log_db()`
- Per-target build summaries in `{project}/build/builds/{target}/build_summary.json`
- Removed archive/timestamp-based log directories
- Console configuration moved from `cli/console.py` into `logging.py`
- Files: `src/atopile/logging.py`, `src/atopile/cli/build.py`

### 2. CLI Changes (TAKE THEIRS)
- Removed `log_dir` parameter from `BuildProcess` and `ParallelBuildManager`
- Exception handling centralized
- Files: `src/atopile/cli/build.py`, `src/atopile/cli/excepthook.py`

### 3. Server Simplification (KEEP OURS + ADAPT)
- Their server.py is only 344 lines (minimal API)
- Our server.py has WebSocket, build queue, parallel builds (~2500 lines)
- **Strategy**: Keep our server.py but adapt to new logging paths

### 4. Webview Components (KEEP OURS)
- They deleted most webview components (ProjectsPanel, CollapsibleSection, etc.)
- We have rich UI with file explorer, build queue, variables panel, etc.
- **Strategy**: Keep our components

### 5. Other Backend Changes (TAKE THEIRS)
- `src/faebryk/library/Literals.py` - type changes
- `src/faebryk/library/Units.py` - unit handling
- Various small fixes across codebase

## Files to Handle

### Take from feature/fabll_part2 (theirs):
| File | Reason |
|------|--------|
| `src/atopile/logging.py` | Central log DB, better architecture |
| `src/atopile/cli/build.py` | Adapted to new logging |
| `src/atopile/cli/excepthook.py` | Centralized exception handling |
| `src/atopile/cli/cli.py` | Minor fixes |
| `src/atopile/config.py` | Config improvements |
| `src/atopile/errors.py` | Error handling |
| `src/atopile/exceptions.py` | New exception module |
| `src/faebryk/library/*` | Library improvements |
| `src/faebryk/libs/*` | Lib improvements |
| Delete: `src/atopile/cli/console.py` | Merged into logging.py |
| Delete: `src/atopile/dashboard/__main__.py` | Not needed |
| Delete: `src/atopile/dashboard/stdlib.py` | Not needed |
| Delete: `src/faebryk/exporters/bom/json_bom.py` | Removed |
| Delete: `src/faebryk/exporters/parameters/json_parameters.py` | Removed |

### Keep ours (resolve conflicts):
| File | Reason |
|------|--------|
| `src/atopile/dashboard/server.py` | Our rich API with WebSocket/build queue |
| `src/vscode-atopile/webviews/src/components/*` | Our rich UI components |
| `src/vscode-atopile/webviews/src/styles.css` | Our styling |
| `src/vscode-atopile/src/common/appState.ts` | Our state management |
| `src/vscode-atopile/src/ui/vscode-panels.ts` | Our panel integration |
| `src/vscode-atopile/webviews/server/dev-server.ts` | Our dev environment |

### Merge carefully (manual conflict resolution):
| File | Strategy |
|------|----------|
| `src/atopile/dashboard/server.py` | Adapt our code to use new log paths |
| `src/vscode-atopile/webviews/src/types/build.ts` | Keep our types, check for new fields |

## Implementation Steps

### Phase 1: Backup and Prepare
1. Create backup branch of current state
2. Stash any uncommitted changes

### Phase 2: Cherry-pick Non-Conflicting Changes
1. Take their logging.py changes
2. Take their cli/build.py changes (remove log_dir)
3. Take library improvements
4. Delete removed files

### Phase 3: Adapt Our Server
1. Update server.py to use `get_central_log_db()` for log queries
2. Update build summary reading to use per-target paths
3. Keep WebSocket, build queue, and all our API endpoints

### Phase 4: Verify and Test
1. Run builds to verify logging works
2. Test WebSocket connections
3. Test file explorer
4. Verify build queue functionality

## Risk Assessment

- **High Risk**: server.py adaptation - needs careful integration of new log paths
- **Medium Risk**: Build process changes - ensure subprocess builds work with new logging
- **Low Risk**: Library changes - mostly independent improvements

## Recommended Approach

Given the significant divergence, I recommend a **staged merge**:

1. First merge the backend changes (logging, CLI)
2. Then adapt our server.py to the new logging architecture
3. Keep all our webview work intact

This preserves the valuable WebSocket/build queue work while adopting the improved logging architecture.
