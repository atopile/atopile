# CLANKER UI Server Screenshot API

This UI dev server exposes a screenshot endpoint for automation/agents.

## Endpoint

- `POST /api/screenshot`

Request body (JSON):

- `name` (string, optional): base name for the screenshot file.
- `path` (string, optional): path on the dev server (default `/`).
- `url` (string, optional): full URL to capture (overrides `path`).
- `waitMs` (number, optional): delay before capture (default 1000 ms).
- `clickAgent` (boolean, optional): click an agent card before capture.
- `agentName` (string, optional): agent name to match when clicking.
- `scrollTop` (boolean, optional): scroll `.output-stream` to top.
- `scrollDown` (boolean, optional): scroll `.output-stream` to bottom.

Response (JSON):

- `ok` (boolean)
- `url` (string): relative URL to fetch the PNG
- `path` (string): absolute filesystem path to the PNG

Example:

```bash
curl -s -X POST http://127.0.0.1:5173/api/screenshot \
  -H 'content-type: application/json' \
  -d '{"name":"ui-main","path":"/","waitMs":500}'
```

Notes:
- The UI must be connected to the backend (no red "Disconnected from backend" banner) or panels will be empty.
- Ensure the backend WS URL is set (e.g., `VITE_WS_URL` or `window.__ATOPILE_WS_URL__`) and the backend is running.
- Some sandboxed environments block localhost network access; run the screenshot request with the necessary permissions in those cases.

Sample response:

```json
{"ok":true,"url":"/__screenshots/ui-main-<timestamp>.png","path":"/tmp/atopile-ui-screenshots/ui-main-<timestamp>.png"}
```

## Image URL

- `GET /__screenshots/<filename>` returns the PNG.

## Storage

- Default directory: `/tmp/atopile-ui-screenshots`
- Override with `ATOPILE_SCREENSHOT_DIR`.

## UI Navigation via Frontend API

You can drive the UI without clicking by sending WebSocket actions to the
backend. This lets you select projects/targets before capturing screenshots.

Open the browser devtools console and run:

```js
const ws = new WebSocket(window.__ATOPILE_WS_URL__ || import.meta.env.VITE_WS_URL);
ws.onopen = () => {
  ws.send(JSON.stringify({ type: 'action', action: 'selectProject', root: '/path/to/project' }));
  ws.send(JSON.stringify({ type: 'action', action: 'toggleTarget', targetName: 'default' }));
};
```

Notes:
- `selectProject` accepts a project root. The UI will switch panels accordingly.
- `toggleTarget` selects a build target; the BOM panel uses the first selected target.
- If you only need a different project, send `selectProject` and wait for the UI to refresh.

### UI Action Events

The Sidebar listens for UI action events that let you open/close sections
without DOM clicks (useful before taking screenshots):

```js
window.dispatchEvent(new CustomEvent('atopile:ui_action', {
  detail: { type: 'openSection', sectionId: 'bom' }
}));
```

Valid `type` values: `openSection`, `closeSection`, `toggleSection`.

## Frontend Crash Logs

The UI captures runtime errors and `console.error`/`console.warn` messages
and forwards them to the dev server.

- `GET /api/ui-logs` returns recent logs
- `POST /api/ui-logs` accepts `{ ts, level, message, stack }`
- Logs are also appended to `artifacts/ui-logs-<timestamp>.jsonl` (override with `ATOPILE_UI_LOG_PATH`)
- Latest log file symlink: `artifacts/ui-logs-latest.jsonl`

Example:

```bash
curl -s http://127.0.0.1:5173/api/ui-logs | jq
```

Tested:
- `POST /api/ui-logs` then `GET /api/ui-logs` returns the posted entry.

## Central SQLite Logging System

All build logs and server action logs are stored in a central SQLite database for unified access.

### Database Location

```
~/.local/share/atopile/build_logs.db
```

Access via: `from atopile.logging import BuildLogger`

### Database Schema

**`builds` table**: Tracks build/action sessions
- `build_id` (TEXT, PK): Unique ID from `project_path:target:timestamp`
- `project_path`, `target`, `timestamp`, `created_at`

**`logs` table**: Individual log entries
- `id` (INTEGER, PK): Sequential ID
- `build_id` (FK): References builds table
- `timestamp` (TEXT): ISO format
- `stage` (TEXT): Build stage or action type (e.g., "compilation", "package-install")
- `level` (TEXT): DEBUG, INFO, WARNING, ERROR
- `audience` (TEXT): Who the message is for:
  - `"user"` - End-user facing (syntax errors, build failures, action results)
  - `"developer"` - Debugging info (parameter resolution, internal state)
  - `"agent"` - For AI agents consuming logs programmatically
- `message` (TEXT): Log content
- `ato_traceback` (TEXT): Source context from ato exceptions
- `python_traceback` (TEXT): Full Python traceback

### Writing Logs

Use `BuildLogger` for structured logging:

```python
from atopile.logging import (
    Audience,
    BuildLogger,
    Level,
    SQLiteLogWriter,
)

# Get or create a logger for an action
logger = BuildLogger.get(
    project_path=str(project_root),
    target="package-ops",  # or specific action ID
    timestamp=None,  # auto-generates
    stage="package-install"
)

# Ensure it writes to the central DB
logger.set_writer(SQLiteLogWriter.get_instance())

# Log with audience tags
logger.info("Installing package...", audience=Audience.USER)
logger.debug("Resolved version 1.2.3", audience=Audience.DEVELOPER)

# Log errors with tracebacks
try:
    do_something()
except Exception as exc:
    logger.exception(exc, audience=Audience.USER)

# Always flush when done
logger.flush()
```

### Audience Guidelines

Use `Audience.USER` for:
- Action start/complete messages ("Installing package X...")
- User-facing errors (syntax errors, missing files)
- Success confirmations ("Package installed successfully")

Use `Audience.DEVELOPER` for:
- Internal state changes
- Debugging information
- Verbose resolution steps

Use `Audience.AGENT` for:
- Structured data for AI consumption
- Machine-parseable status updates

### Querying Logs

**From Python:**
```python
from atopile.server.domains.logs import handle_query_logs

result = handle_query_logs({
    "project_path": "/path/to/project",
    "level": ["WARNING", "ERROR"],
    "audience": "user",
    "limit": 100,
})
# Returns: {"logs": [...], "total": int, "has_more": bool}
```

**Via API:**
```bash
# Query logs with filters
curl "$VITE_API_URL/api/logs/query?level=ERROR&audience=user"

# Get log counts by level
curl "$VITE_API_URL/api/logs/counts?build_id=abc123"
```

### Stage Naming Conventions

For builds: Use build stage names ("compilation", "linking", "export")

For server actions: Use action-type prefixes:
- `package-install` - Package installation
- `package-remove` - Package removal
- `project-create` - Project creation
- `build-queue` - Build queue operations

### Integration Pattern for Server Actions

When adding new server actions that should log to the central DB:

```python
async def handle_some_action(payload: dict, ctx: AppContext) -> dict:
    project_root = payload.get("projectRoot", "")

    # Create logger for this action
    from atopile.logging import Audience, BuildLogger, SQLiteLogWriter

    logger = BuildLogger.get(
        project_path=project_root,
        target="server-actions",
        stage="my-action"
    )
    logger.set_writer(SQLiteLogWriter.get_instance())

    try:
        logger.info("Starting action...", audience=Audience.USER)

        # Do the work
        result = do_action()

        logger.info("Action completed", audience=Audience.USER)
        return {"success": True}

    except Exception as exc:
        logger.exception(exc, audience=Audience.USER)
        return {"success": False, "error": str(exc)}

    finally:
        logger.flush()
```

### UI Integration

Logs with `audience="user"` and `level` of WARNING/ERROR/ALERT are:
1. Extracted by `problem_parser.py`
2. Displayed in the Problems panel
3. Shown with source location if `ato_traceback` is present

To display action status in the UI:
1. Log with `audience=Audience.USER`
2. Use appropriate level (INFO for progress, ERROR for failures)
3. Include relevant context in the message
4. The UI log viewer will show these entries
