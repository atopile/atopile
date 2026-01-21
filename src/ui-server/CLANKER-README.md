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

Sample response:

```json
{"ok":true,"url":"/__screenshots/ui-main-<timestamp>.png","path":"/tmp/atopile-ui-screenshots/ui-main-<timestamp>.png"}
```

## Image URL

- `GET /__screenshots/<filename>` returns the PNG.

## Storage

- Default directory: `/tmp/atopile-ui-screenshots`
- Override with `ATOPILE_SCREENSHOT_DIR`.
