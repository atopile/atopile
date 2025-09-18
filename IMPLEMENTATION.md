# Telemetry Client Implementation Guide

This document captures the details required to replace the PostHog Python SDK while keeping the existing telemetry behaviour intact.

## Target Behaviour
- Maintain the public API exposed by `src/atopile/telemetry.py` (`capture`, `capture_exception`, `capture` context manager, module-level `client`, `client.disabled`, and `flush()` via the atexit hook).
- Events must be enqueued asynchronously and flushed via a worker thread so CLI commands never block on I/O.
- Flush pending events on interpreter shutdown (current semantics call `flush()` via `atexit`, and the new implementation must honour a timeout to avoid hanging the process).
- Respect opt-out controls (set `client.disabled = True` once telemetry is disabled in `TelemetryConfig.load`).

## PostHog API Summary
Consult https://posthog.com/docs/api for full context. Relevant endpoints:

### `/capture/`
- **Method**: `POST`
- **Payload** (`application/json`):
  ```json
  {
    "api_key": "<project_api_key>",
    "event": "<event name>",
    "distinct_id": "<uuid or identifier>",
    "properties": { ... },
    "timestamp": "<ISO-8601 string, optional>",
    "context": { ... optional ... }
  }
  ```
- **Response**: `200 OK` with `{"status": 1}` on success. Failure codes include:
  - `400` for invalid payload
  - `401/403` for invalid project key
  - `500/503` for server-side issues
- The endpoint accepts gzip-compressed bodies and additional metadata, but none are required for our use case.

### `/batch/`
- Allows batching multiple event payloads:
  ```json
  {
    "api_key": "<project_api_key>",
    "batch": [ { ...single capture payload... }, ... ],
    "sent_at": "<ISO-8601 timestamp>"
  }
  ```
- We can stick to single-event batches (`flush_at = 1`) while preserving the queue, so `/batch/` is optional. Using `/batch/` gives us flexibility if we later want to aggregate before sending.

### Exception Capture Convention
PostHog treats exceptions as events on `/capture/` with a reserved name `$exception`. The Python SDK sends payloads similar to:
```json
{
  "event": "$exception",
  "properties": {
    "$exception_message": "<str(exc)>",
    "$exception_type": "<exc.__class__.__name__>",
    "$exception_stack_trace": "<traceback string>",
    "$exception_person": "<distinct_id>",
    ...custom properties...
  }
}
```
We should mirror this so server-side dashboards continue to classify the events as exceptions.

## Client Design Notes

### Configuration
- Keep constants near the top of `telemetry.py` for readability:
  - `PH_API_HOST = "https://telemetry.atopileapi.com"`
  - `PH_API_ENDPOINT = "/capture/"`
  - `DEFAULT_QUEUE_SIZE = 256`
  - `WORKER_WAKE_INTERVAL = 0.1` seconds (matches the previous SDK `flush_interval`)
  - `FLUSH_TIMEOUT = 2.0` seconds (budget for atexit flush)

### Data Structures
- Introduce local `TypedDict`s to emulate `OptionalCaptureArgs`:
  ```python
  class CaptureArgs(TypedDict, total=False):
      distinct_id: str
      properties: dict[str, Any]
      timestamp: str
      context: dict[str, Any]
  ```
- Internal queue item can be an immutable `dataclass` storing the endpoint, payload dict, and retry counter.

### TelemetryClient Skeleton
```python
class TelemetryClient:
    disabled: bool

    def __init__(self, api_key: str, host: str, *, queue_size: int = DEFAULT_QUEUE_SIZE):
        self._api_key = api_key
        self._host = host.rstrip('/')
        self._queue: Queue[_Event] = Queue(maxsize=queue_size)
        self._worker = Thread(target=self._worker_loop, name="telemetry-worker", daemon=True)
        self._shutdown = Event()
        self.disabled = False
        self._worker.start()
```

- `capture()` and `capture_exception()` push events into the queue unless disabled or `_shutdown.is_set()`.
- `flush(timeout)` signals `_shutdown`, waits up to `timeout` for the queue to empty, and then joins the worker thread.
- Use `faebryk.libs.http.http_client` for HTTP interaction so we reuse truststore configuration and consistent headers. All POSTs should include:
  ```python
  headers = {
      "Content-Type": "application/json",
      "User-Agent": f"atopile/{importlib.metadata.version('atopile')}"
  }
  ```

### Worker Loop & HTTP Layer
- Worker waits on queue with timeout (`WORKER_WAKE_INTERVAL`).
- For each event:
  1. Build the final JSON payload. Ensure `api_key` is injected at send time.
  2. Perform `client.post(f"{self._host}{PH_API_ENDPOINT}", json=payload, timeout=5.0)` in a `with http_client(headers=headers) as client` block.
  3. Treat `>= 500` or network errors as transient: retry once after a short `time.sleep(0.5)`.
  4. Drop the event after the retry to prevent unbounded blocking; log at `DEBUG` with reason.
- If the queue is full, `capture` should drop the event immediately with a single debug log (mirrors SDK behaviour when the consumer is unhealthy).
- When `_shutdown` is set, drain any remaining items before exiting.

### Exception Serialization
- Use `traceback.format_exception` to build the stack trace string.
- Merge user-supplied `properties` into the standard `$exception_*` attributes (user data wins on key conflicts to remain backward-compatible).

### Flush-on-Exit
- `_flush_telemetry_on_exit()` should call `client.flush(timeout=FLUSH_TIMEOUT)` when telemetry is enabled. Wrap in try/except just like today to protect shutdown.
- After `flush`, set `client.disabled = True` or keep `_shutdown` set to prevent further enqueue attempts during interpreter teardown.

### Testing Hooks
- Update `test/conftest.py` to import `from atopile.telemetry import client` and set `client.disabled = True` to keep tests quiet.
- Unit tests can monkeypatch the HTTP sender and queue to assert:
  - Events are enqueued and drained by the worker.
  - `flush()` waits for in-flight events.
  - Opt-out toggles `disabled`.
  - Exception properties include the `$exception_*` fields.

## Implementation Checklist
1. Remove PostHog imports and dependency entries.
2. Introduce `TelemetryClient` in `telemetry.py` along with helper types and constants.
3. Replace `_get_posthog_client()` usage with `_get_telemetry_client()` returning the new class (falling back to a disabled `TelemetryClient` instance on failure).
4. Update capture helpers, context manager, and tests to reference the new client.
5. Add targeted unit tests in `test/` (e.g., `test/test_telemetry_client.py`).
6. Regenerate `uv.lock` and run `pytest` to confirm stability.

Adhering to this guide should make the swap from the PostHog SDK to the bespoke client predictable and maintainable.
