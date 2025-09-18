# Telemetry Client Replacement Plan

## Goals
- Remove the dependency on the third-party `posthog` Python SDK.
- Re-implement the handful of PostHog REST endpoints we rely on so telemetry keeps flowing to `https://telemetry.atopileapi.com`.
- Maintain end-user behaviour: opt-out still works, events queue asynchronously, and buffered events flush on exit.

## Constraints & Requirements
- Only `capture`, `capture_exception`, `flush`, and a module-level `disabled` flag are required externally.
- Continue using the PostHog public ingestion API (see https://posthog.com/docs/api) with the existing public project key.
- Match existing async semantics: non-blocking enqueue during command execution, `flush()` drains the queue at exit within a timeout.
- Respect current opt-out configuration stored in `~/atopile/telemetry.yaml`.
- Keep the implementation self-contained in `src/atopile/telemetry.py`; avoid adding new modules.
- Use repo-standard HTTP utilities (`faebryk.libs.http.http_client`) and logging patterns.

## Architecture Overview
- Introduce `TelemetryClient` inside `telemetry.py`.
  - Constructor accepts API key, host, queue size, worker flush interval, and timeout.
  - Maintain `disabled` attribute and `_shutdown` flag mirroring prior behaviour.
  - Background worker thread reads from `queue.Queue` and POSTs batched events.
  - `flush(timeout)` joins the worker long enough to drain the queue, then performs a final POST.
- Requests
  - `capture` posts to `/capture/` with payload `{api_key, event, distinct_id, properties, timestamp}`.
  - `capture_exception` uses the same endpoint with an `event` such as `$exception` plus serialized stack info.
  - Include standard headers (`Content-Type: application/json`, `User-Agent` mirroring other clients).
  - Use `http_client()` for connection handling and TLS truststore.
- Error Handling
  - Log failures at debug level; drop events after configurable retry attempts to avoid blocking CLI usage.
  - On fatal worker errors, set `disabled = True` to stop queuing.

## Implementation Steps
1. **Define Support Types**
   - Replace `OptionalCaptureArgs` import with local `TypedDict` describing optional fields (`distinct_id`, `properties`, etc.).
   - Declare small dataclasses or helper functions to format payloads for PostHog.
2. **Build TelemetryClient**
   - Implement queue, worker thread, `_send_event` helper, and `flush(timeout)`.
   - Ensure `capture`/`capture_exception` short-circuit when disabled or opt-out.
   - Keep `_MockClient` for init failures.
3. **Wire Into Existing Flow**
   - Swap `_get_posthog_client()` for `_get_telemetry_client()` returning the new class.
   - Update module-level `client` usage, atexit hook, and decorators to use the new interface with minimal changes.
4. **Remove SDK Usage**
   - Drop `posthog` imports, update `test/conftest.py` to import the module-level client and set `client.disabled = True` during tests.
   - Remove the dependency from `pyproject.toml` and regenerate `uv.lock`.
5. **Testing & Validation**
   - Add unit tests for queueing, flush timeout, and opt-out behaviour.
   - Run targeted manual checks (e.g., triggering `capture` within CLI commands) to confirm events enqueue without raising.

## Decisions / Follow-ups
- **Exception Event Schema**: Use the standard `/capture/` endpoint with the `$exception` event name and include `$exception_message`, `$exception_type`, `$exception_stack_trace`, and optional `$exception_person` fields matching PostHog docs.
- **Queue & Flush Behaviour**: Keep a background worker with an immediate flush policy (`flush_at=1`) but retain the async queue so the CLI remains non-blocking; set `max_queue_size=256` and a worker wake interval of 100ms to mirror the SDK defaults.
- **Retries**: Attempt to send each payload once and retry a single time on transient HTTP/network failures with a short (500ms) sleep; drop the event thereafter to avoid blocking the process.
