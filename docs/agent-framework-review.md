# Agent Framework Branch Review

## Summary

This branch is a strong prototype pass, but it is not yet architecturally clean in the way the rest of atopile tends to be. The biggest issue is not "style"; it is that the branch currently ships multiple overlapping agent runtimes, partially wired features, and route/UI layers that assume capabilities the core runner does not actually provide.

The result is:

- correctness regressions are already visible in the current test suite
- the runtime boundary is still blurry between "new framework" and "legacy tools/orchestrator"
- the server route layer owns too much stateful orchestration logic
- the UI is carrying too much protocol/state logic inside one monolithic component

If the goal is a world-class agent framework for electrical design work, the next step should be to reduce the system to a smaller number of clear contracts:

1. one runtime
2. one tool contract
3. one session/run state model
4. one event protocol
5. thin route/UI adapters around that core

## Must-Fix Issues

### 1. Two orchestrator implementations are alive at once, and the old one is already broken

The branch introduces `AgentRunner`, but keeps `_orchestrator_old.py` in-tree and still has tests importing it directly. At the same time, tool definitions now include `design_questions`, while the legacy handler registry still rejects any schema without a registered tool handler.

Evidence:

- `src/atopile/server/agent/__init__.py:8`
- `src/atopile/server/agent/tools.py:576`
- `src/atopile/server/agent/tool_definitions_project.py:681`
- `test/server/agent/test_orchestrator_output.py:11`

Observed result:

- `pytest -q test/server/agent/test_agent_mediator.py test/server/agent/test_hashline_policy.py test/server/agent/test_orchestrator_output.py`
- 4 failures, including `RuntimeError: Tool registry/schema mismatch: schema without handler: design_questions`

Why this matters:

- the branch now has two incompatible truths about what the runtime is
- regressions in the old path are already in the repo
- the new path is not replacing the old path cleanly, so future changes will keep breaking one or the other

Recommendation:

- pick one runtime as the supported path now
- if `AgentRunner` is the new core, delete or hard-deprecate `_orchestrator_old.py`
- move compatibility tests onto the new runtime instead of keeping behavior split
- treat managed/intercepted tools as first-class in the tool contract so schema validation does not depend on legacy handler registration

### 2. Sync turns can race each other and corrupt session history / response chaining

`send_message()` checks for an active background run, but it never marks the session as busy for synchronous turns. Two overlapping HTTP requests against the same session can therefore both run, both read the same `history`/`last_response_id`, and both append conflicting results.

Evidence:

- `src/atopile/server/routes/agent/main.py:150`
- `src/atopile/server/routes/agent/main.py:195`
- `src/atopile/server/routes/agent/utils.py:441`

Why this matters:

- the agent runtime is stateful across turns via `history` and `last_response_id`
- concurrent sync calls can produce out-of-order history and broken response chaining
- this will be hard to debug because it only appears under duplicate submits / UI retries / multiple clients

Recommendation:

- treat sync turns as real runs with the same session locking model as background runs
- reserve `active_run_id` before invoking the runner, even for sync mode
- move the turn transition into a single session service so route handlers do not manually coordinate session/run state

### 3. Invalid project-root requests can wipe session state before validation fails

Route handlers switch/reset the session project scope before the new `project_root` is validated by the runtime. If the new scope is invalid, the request fails after the session has already been reset and persisted.

Evidence:

- `src/atopile/server/routes/agent/main.py:80`
- `src/atopile/server/routes/agent/main.py:157`
- `src/atopile/server/routes/agent/main.py:253`
- `src/atopile/server/routes/agent/utils.py:737`
- `src/atopile/server/agent/runner.py:320`

Why this matters:

- a bad request can destroy valid session history/tool memory
- persistence makes the damage survive process restarts
- this is a user-facing reliability problem, not just an internal detail

Recommendation:

- validate the requested scope first
- only mutate and persist session state after validation succeeds
- move project-scope transition into one transactional helper

### 4. The new "agent messaging" surface is mostly dead code

The route layer, run state, and UI all support agent-to-agent messages, inbox cursors, and `/runs/{run_id}/messages`, but the actual runtime ignores `message_callback`, and `AgentTurnResult` has no `agent_messages` field.

Evidence:

- `src/atopile/server/agent/runner.py:204`
- `src/atopile/server/agent/runner.py:317`
- `src/atopile/server/routes/agent/utils.py:473`
- `src/atopile/server/routes/agent/utils.py:551`
- `src/atopile/server/routes/agent/main.py:324`

Why this matters:

- the API advertises a feature the core does not emit
- the route and UI complexity is paying maintenance cost for a capability that does not exist yet
- this is exactly the kind of prototype drift that makes architecture feel "framework-y" instead of clean

Recommendation:

- either remove agent-message routes/state until real multi-agent behavior exists
- or make messages a first-class runtime output with typed events and tests

### 5. Datasheet file attachment behavior regressed

The helper now emits only an `input_text` reminder after `datasheet_read`, but the test suite expects the uploaded PDF to be attached as an `input_file`. That means the model loses the direct file attachment path that the tests were asserting.

Evidence:

- `src/atopile/server/agent/orchestrator_helpers.py:682`
- `src/atopile/server/agent/orchestrator_helpers.py:750`
- `test/server/agent/test_orchestrator_output.py:52`

Observed result:

- `test_build_function_call_outputs_attaches_datasheet_file` fails with `IndexError`

Why this matters:

- this is a behavior regression in a core "research/design verification" tool flow
- datasheet reasoning is central to the product goal

Recommendation:

- decide the intended contract explicitly:
  - either restore `input_file` attachment support
  - or update the runtime/tests/UI to consistently use `file_id` references without pretending the old behavior still exists

## Should-Fix Architectural Problems

### 6. Runtime behavior depends on repo-local `.claude/skills` docs

The production runtime loads full skill bodies from `.claude/skills` on every turn and fails hard if those docs are missing.

Evidence:

- `src/atopile/server/agent/config.py:52`
- `src/atopile/server/agent/context.py:31`
- `src/atopile/server/agent/context.py:121`

Why this is a problem:

- developer prompt assets are being treated as runtime application data
- packaging/deployment becomes fragile
- prompt iteration is coupled to repo layout instead of a versioned runtime contract

Recommendation:

- move runtime prompts/skills into explicit packaged assets
- separate "developer review guidance" from "runtime operating prompt"
- compile the runtime prompt from smaller typed fragments, not raw full markdown docs

### 7. The route layer owns too much orchestration state

`routes/agent/utils.py` is effectively a stateful application service, persistence layer, event bridge, run manager, and logging adapter combined into one file with module-level globals.

Evidence:

- `src/atopile/server/routes/agent/utils.py:62`
- `src/atopile/server/routes/agent/utils.py:68`
- `src/atopile/server/routes/agent/utils.py:213`
- `src/atopile/server/routes/agent/utils.py:764`

Why this is a problem:

- hard to test in isolation
- hard to reason about concurrency and lifecycle
- route handlers are not thin adapters anymore

Recommendation:

- introduce a dedicated `AgentSessionService` / `AgentRunService`
- keep FastAPI modules thin: validate request, call service, return DTO
- keep persistence behind an interface rather than module globals

### 8. Core modules are already too large to stay maintainable

The biggest new files are beyond the point where local cleanliness inside the file matters; the unit of decomposition is wrong.

Current sizes:

- `src/ui-server/src/components/AgentChatPanel.tsx`: 3579 lines
- `src/atopile/server/agent/tools.py`: 2861 lines
- `src/atopile/server/agent/runner.py`: 1479 lines
- `src/atopile/server/routes/agent/utils.py`: 985 lines

Why this is a problem:

- boundaries are implicit instead of enforced
- testing naturally becomes sparse
- "framework" behavior gets buried in giant files instead of reusable domain units

Recommendation:

- split `tools.py` by capability family: project, research, build, layout, manufacturing, workflow
- split `runner.py` into turn state, loop policy, managed tools, and provider interaction
- split `AgentChatPanel.tsx` into:
  - session state hook
  - transport/event hook
  - transcript view
  - composer
  - trace/checklist panels

### 9. The UI component is acting as both view and protocol runtime

`AgentChatPanel.tsx` is not just rendering. It parses transport payloads, persists chats, manages run state, derives protocol semantics, and owns tool-trace/checklist/design-question logic.

Evidence:

- `src/ui-server/src/components/AgentChatPanel.tsx:1`
- `src/ui-server/src/components/AgentChatPanel.tsx:223`
- `src/ui-server/src/components/AgentChatPanel.tsx:552`
- `src/ui-server/src/components/AgentChatPanel.tsx:2423`

Why this is a problem:

- protocol changes will force risky UI edits
- view testing becomes expensive
- reusable agent state cannot be shared elsewhere in the app

Recommendation:

- move protocol parsing/state transitions into a dedicated hook or store slice
- keep the component tree focused on rendering and user interactions
- add component tests around transcript rendering separately from transport/state tests

### 10. Test coverage is pointed at the wrong layer

The branch adds many new server/UI surfaces, but the targeted tests currently exercise mostly helper logic and the old orchestrator path. I could not find route-level tests for `/api/agent` or frontend tests for the new agent panel/event protocol.

Evidence:

- `test/server/agent/test_orchestrator_output.py:11`
- no route tests found for `src/atopile/server/routes/agent/main.py`
- no UI tests found for `src/ui-server/src/components/AgentChatPanel.tsx`

Recommendation:

- add tests at the actual product seams:
  - route tests for session/run lifecycle
  - runner tests for managed tools and turn continuation
  - UI tests for progress-event reduction and trace rendering

## Suggested Target Architecture

If this is meant to become the permanent agent framework, I would aim for this shape:

### 1. Core runtime

Owns:

- turn loop
- tool-call execution contract
- managed-tool handling
- continuation/stop policy
- typed runtime outputs

Does not own:

- HTTP
- websocket transport
- persistence
- UI event formatting

### 2. Session/run service

Owns:

- session state
- run lifecycle
- concurrency control
- persistence
- event fanout

Does not own:

- model prompting details
- raw FastAPI request/response handling

### 3. Tool registry

Owns:

- tool metadata
- tool handler registration
- managed-tool declarations
- validation of handler/schema parity

Does not encode:

- UI suggestion heuristics
- route behavior

### 4. Event protocol

Create a small typed event model shared by backend and frontend:

- `turn.started`
- `turn.progress`
- `tool.started`
- `tool.finished`
- `turn.questions_requested`
- `turn.completed`
- `turn.failed`

Keep websocket/custom-event translation outside the domain model.

### 5. Frontend agent client

Split into:

- transport client
- state reducer/store
- pure presentational components

That will make the UI much easier to evolve without turning the chat panel into a second runtime.

## Concrete Next Steps

1. Collapse to one orchestrator/runtime path.
2. Fix the red tests and add coverage for the new runner.
3. Introduce a real session/run service and move state out of route utils.
4. Remove dead multi-agent surfaces until they are backed by real runtime behavior.
5. Break up the server and UI monolith files before adding more capability.
6. Turn runtime prompts/skills into packaged application assets instead of `.claude` dependencies.

## Verification Notes

I ran:

```bash
pytest -q test/server/agent/test_agent_mediator.py test/server/agent/test_hashline_policy.py test/server/agent/test_orchestrator_output.py
```

Result:

- 50 passed
- 4 failed

The failures were concentrated in `test/server/agent/test_orchestrator_output.py` and directly support the compatibility/correctness issues described above.
