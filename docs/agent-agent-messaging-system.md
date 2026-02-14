# Agent-Agent Messaging System Design

## Goal

Design a reliable internal messaging layer between two agents:

- `manager` (user-facing conversational agent)
- `worker` (execution specialist agent)

The system must support:

- free back-and-forth agent collaboration
- strict user intent tracking by `manager`
- full visibility of tool/build execution in UI
- clean extension path to additional specialists later

## Existing Foundation

Current implementation already provides pieces we can build on:

- Run lifecycle and steering queue:
  - `src/atopile/server/routes/agent.py`
  - `AgentRun.steer_messages` and `steer_run(...)`
- Streaming progress transport:
  - backend emits `agent_progress`
  - frontend receives `atopile:agent_progress`
  - `src/ui-server/src/api/websocket.ts`
  - `src/ui-server/src/components/AgentChatPanel.tsx`
- Tool traces and build status rendering:
  - `src/ui-server/src/components/AgentChatPanel.tsx`

Today, these are single-agent semantics. We need explicit agent-to-agent message semantics.

## Core Model

Use an append-only message log per run plus per-agent inbox cursors.

### Message Envelope

```python
@dataclass
class AgentMessageEnvelope:
    message_id: str
    run_id: str
    session_id: str
    thread_id: str
    from_agent: str  # "manager" | "worker" | "specialist:<name>"
    to_agent: str    # "manager" | "worker" | "specialist:<name>" | "broadcast"
    kind: str
    summary: str
    payload: dict[str, Any]
    visibility: str  # "internal" | "user_visible" | "user_redacted"
    priority: str    # "low" | "normal" | "high" | "urgent"
    requires_ack: bool
    correlation_id: str | None
    parent_id: str | None
    created_at: float
```

### Run State Additions

Add to `AgentRun`:

- `message_log: list[AgentMessageEnvelope]`
- `inbox_cursor: dict[str, int]` (index cursor per agent)
- `pending_acks: set[str]`
- `intent_snapshot: dict[str, Any]`

`intent_snapshot` is manager-owned and stores user request contract:

- objective
- constraints
- acceptance criteria
- selected project/targets
- approvals/decisions

## Message Kinds

Define a small typed set first:

- `intent_brief`: manager -> worker initial task contract
- `clarification_request`: worker -> manager
- `clarification_reply`: manager -> worker
- `plan_update`: worker -> manager
- `tool_intent`: worker -> manager/user-visible
- `tool_result`: worker -> manager/user-visible
- `build_update`: worker -> manager/user-visible
- `blocker`: worker -> manager/user-visible
- `decision`: manager -> worker (approve/deny/change scope)
- `status_check`: manager -> worker
- `status_reply`: worker -> manager
- `result_bundle`: worker -> manager
- `final_response`: manager -> user-visible
- `cancel`: manager -> worker
- `ack`: receiver -> sender

## Transport and API

## In-Process Bus

Add an internal API in `src/atopile/server/routes/agent.py` (or new module):

- `post_agent_message(run_id, envelope)`
- `pull_agent_messages(run_id, agent_id, max_items=...)`
- `ack_agent_message(run_id, agent_id, message_id)`

## WebSocket Event

Add event emission:

- event name: `agent_message`
- payload: serialized `AgentMessageEnvelope`

Frontend can subscribe similarly to current `agent_progress`.

## Persistence

Persist selected fields in run/session logs:

- always persist `message_log` metadata (without large payload blobs)
- persist `intent_snapshot`
- persist terminal summaries

Do not persist unbounded tool payloads in full. Keep pointer IDs or compact summaries.

## Manager/Worker Protocol

1. User message arrives.
2. Manager creates `intent_snapshot`.
3. Manager emits `intent_brief` to worker.
4. Worker executes tools and emits `tool_intent`/`tool_result`/`build_update`.
5. Worker emits `blocker` when blocked.
6. Manager either resolves via user clarification or sends decision.
7. Worker emits `result_bundle`.
8. Manager validates against `intent_snapshot.acceptance_criteria`.
9. Manager emits `final_response` to user.

## UI/UX Mapping

`AgentChatPanel` should render two logical streams:

- user-visible timeline
- internal agent thread

Recommended UX behavior:

- default: show user-visible timeline and execution cards
- collapsed pill: `Internal agent messages (N)`
- toggle to inspect manager<->worker conversation
- keep current tool trace and build status cards visible in main timeline

### Visibility Rules

- `user_visible`: always shown in main timeline
- `user_redacted`: shown with compact text, expandable on demand
- `internal`: hidden unless user opens internal thread

## Tool and Permission Enforcement

Enforce actor-based tool access server-side:

- `manager`: read/status/report tools only
- `worker`: full execution/mutating tools

This must be validated in backend execution path, not prompt-only.

## Reliability Controls

- message idempotency via `message_id`
- ordered delivery within run by append index
- ack timeout watchdog for `requires_ack`
- dead-letter capture for malformed payloads
- loop guard:
  - max internal-only exchanges without user-visible progress
  - max repeated clarification ping-pong count

## Rollout Plan

## Phase 1 (low-risk)

- introduce `AgentMessageEnvelope`
- emit `agent_message` events from existing progress/tool points
- no behavioral split yet (single orchestrator still running)

## Phase 2

- split runtime into `manager_turn(...)` and `worker_turn(...)`
- move steering into manager->worker `decision` / `clarification_reply`
- add tool allowlist by actor

## Phase 3

- UI dual-stream rendering
- internal thread controls
- intent tracking card in chat header

## Phase 4

- add specialist routing:
  - `specialist:pcb`
  - `specialist:library`
  - `specialist:diagnostics`
- keep manager as the only user-facing narrator

## Testing Strategy

Add tests under `test/server/agent/`:

- envelope serialization/deserialization
- order and cursor semantics
- manager/worker protocol happy path
- blocker -> clarification -> resume path
- visibility mapping to UI event payload
- actor-based tool deny/allow checks

Add UI tests under `src/ui-server/src/__tests__/`:

- internal thread collapsed/expanded behavior
- tool/build visibility unaffected by internal thread toggle
- status check-in cards appear when worker is active
