# Package Sub-Agent Plan

## Goal

Add a package-specialist sub-agent workflow so the main agent can delegate wrapper/package implementation work while continuing top-level integration work.

The package agent should:
- run the same base model as the main agent by default
- have access to the same tool surface, but scoped to the package project it owns
- focus on building a generic, reusable, self-contained package
- expose standard interfaces and minimal support circuitry
- validate its own package target(s) before handing control back
- accept optional guidance from the main agent about design-specific priorities

Hard constraints:
- maximum 3 concurrent package agents per parent run
- sub-agent context window capped at 240k tokens
- package agent should not become a second full planning/orchestration system for the whole design

## Current Architecture

### Single-agent runtime today

The current runtime is built around one active conversation chain per session:
- system prompt and skills are assembled in [`src/atopile/server/agent/context.py`](../src/atopile/server/agent/context.py)
- the main tool loop lives in [`src/atopile/server/agent/runner.py`](../src/atopile/server/agent/runner.py)
- the provider wrapper is [`src/atopile/server/agent/provider.py`](../src/atopile/server/agent/provider.py)
- tool execution is routed through [`src/atopile/server/agent/registry.py`](../src/atopile/server/agent/registry.py) into [`src/atopile/server/agent/tools.py`](../src/atopile/server/agent/tools.py)
- user/background run state is stored in [`src/atopile/server/routes/agent/models.py`](../src/atopile/server/routes/agent/models.py) and [`src/atopile/server/routes/agent/state.py`](../src/atopile/server/routes/agent/state.py)
- background execution is coordinated in [`src/atopile/server/routes/agent/utils.py`](../src/atopile/server/routes/agent/utils.py)

Important current properties:
- one `active_run_id` per session
- one `previous_response_id` chain per session
- one fixed set of required skills from `AgentConfig.fixed_skill_ids`
- no real multi-agent runtime yet

There is one notable extension point already present:
- `message_callback` is reserved in `AgentRunner.run_turn(...)` but currently unused and explicitly marked as future multi-agent support in [`runner.py`](../src/atopile/server/agent/runner.py)

### Why the current route/run model is not enough

The current `AgentRun` model is designed for user-visible top-level runs:
- it is tied to a session
- it reserves the session as busy
- stop/steer/interrupt semantics are user-facing

That is the wrong abstraction for package workers.

If we simply reused `AgentRun` directly for sub-agents:
- we would fight the existing `active_run_id` invariant
- package workers would look like competing top-level runs
- parent/child coordination would be awkward
- child lifecycle would leak into normal session semantics

### Tool surface today

The registry currently provides a flat tool surface from `tools.py`.
That is good news: package agents can reuse the same tool implementations if we change the project root they run under.

This is already how nested package builds work:
- `build_run(project_path=...)` already supports nested project roots
- `parts_install(project_path=...)` was recently added for nested package-local supporting parts

That means package specialists do not need a different tool implementation layer.
They need a different runtime scope.

## Product Shape

### First-class worker, not a special case

The package worker should be exposed through a normal tool/API surface.

That means:
- the main agent uses package workers the same way it uses any other tool
- the UI can later expose the same package worker operations directly to the user
- package workers are not implemented as a hidden side channel inside the runner

This is an important boundary:
- parent agent decides when to delegate
- tool/API layer creates and controls package workers
- runtime executes them like any other background worker

The package worker system should therefore be designed as a general-purpose internal service with:
- tool entrypoints for the main agent
- API/UI entrypoints for users later
- one shared worker state model underneath

### What the main agent should be able to do

The main agent needs a small package-worker tool family:

1. `package_agent_spawn`
- create a package-specialist worker for one package project
- returns immediately with a worker id
- arguments:
  - `project_path`: relative package project path, e.g. `packages/Raspberry_Pi_RP2350A`
  - `goal`: short instruction for what the package agent should complete
  - `comments`: optional notes from the main agent about priorities or constraints
  - `selected_targets`: optional package targets, default `['default']`

2. `package_agent_list`
- list active/recent child workers for the current parent run
- returns status, package path, current phase, summary, completion state

3. `package_agent_wait`
- wait for one or more child workers to finish
- optionally with timeout
- returns condensed results, changed files, builds run, failure summary

4. `package_agent_get`
- inspect a specific child worker result/log summary in detail

5. `package_agent_stop`
- graceful stop for one child worker

This is better than one overloaded tool because the parent model needs both fire-and-forget delegation and later collection.

### What the main agent should pass

The main agent should not delegate with only an `lcsc_id` unless the child is responsible for package creation from scratch.

There are two distinct delegation modes:

1. `create from part`
- use when no package project exists yet
- inputs should include:
  - `lcsc_id`
  - desired package name if needed
  - package goal
  - main-agent comments

2. `refine existing package`
- use when `parts_install(create_package=true)` or `package_create_local` already created the package project
- inputs should include:
  - `project_path`
  - package goal
  - main-agent comments
  - optional target list

For this branch, the default flow should be:
- main agent creates or identifies the package project first
- then delegates by `project_path`

Reason:
- the package worker should be rooted in a concrete package project
- that gives it a stable filesystem scope
- it avoids mixing package creation and package refinement into one ambiguous instruction

So the tool family should likely look like:
- `package_agent_spawn(project_path=..., goal=..., comments=...)`
- optionally later:
  - `package_agent_spawn_from_part(lcsc_id=..., package_name=..., goal=..., comments=...)`

V1 recommendation:
- keep a single `package_agent_spawn`
- require `project_path`
- let the main agent do package creation explicitly before delegation

That keeps the first implementation much cleaner.

### What the package agent should do

The package agent should:
- treat the package project as its root
- read the generated wrapper/package files
- keep the wrapper generic and reusable
- use standard interfaces and simple stdlib compositions
- add only package-local supporting parts needed for the package itself
- validate package builds first, iteratively
- stop once the package is coherent, builds, and is minimally complete

It should not:
- redesign the full board
- edit top-level `main.ato` by default
- encode board-specific role names into the wrapper API
- wait for design-wide signoff loops

## Prompt / Skill Strategy

### New skill: `package-agent`

Add a new skill file:
- [`.claude/skills/package-agent/SKILL.md`](../.claude/skills/package-agent/SKILL.md)

This should be a focused subset of the main agent guidance, with extra package examples.

Recommended contents:
- package wrappers are generic, reusable abstractions
- prefer stdlib interfaces and simple arrays/compositions
- keep package-local supporting parts inside the package project
- build package targets incrementally and repeatedly
- start with a minimal viable wrapper, then extend only if needed
- do not invent top-level design structure
- do not create extra wrapper aggregation layers
- examples of good wrapper APIs for MCU, motor driver, regulator, sensor, connector

### Main-agent guidance for delegation

The main agent also needs explicit guidance for when and how to use package workers.

Update the main-agent skills/tool guidance so it knows:
- package workers are appropriate for wrapper/package implementation tasks
- the main agent should keep integration and top-level architecture work
- delegate by `project_path`, not just by naming the part vaguely
- include short comments when a package has specific priorities important to the top-level design
- wait on or inspect results before integrating assumptions from the child

Recommended guidance to add:
- Use `package_agent_spawn` when a package wrapper can be built mostly independently from the rest of the design.
- Create or identify the package project first, then delegate using its `project_path`.
- Pass concise comments about what matters most to the top-level design, but keep the child focused on building a generic reusable package.
- Use `package_agent_wait` or `package_agent_get` before wiring the package deeply into the main design.

Examples of good parent comments:
- `Prioritize SWD, USB, QSPI flash, and crystal support.`
- `Keep the wrapper generic; do not encode this board's motor-role names.`
- `Use standard interfaces and validate the package target before stopping.`

### Sub-agent fixed skills

Do not give package agents the full main-agent fixed skill set.

Recommended fixed skills for package workers:
- `agent`
- `ato`
- `package-agent`

Omit `planning` for package workers by default.

Reason:
- package workers should execute, not run full board-level planning loops
- this keeps the prompt smaller
- it matches the 240k context budget target

### Config changes

Add sub-agent config fields to [`src/atopile/server/agent/config.py`](../src/atopile/server/agent/config.py):
- `subagent_model: str = model`
- `subagent_max_concurrent: int = 3`
- `subagent_context_hard_max_tokens: int = 240_000`
- `subagent_fixed_skill_ids: list[str] = ['agent', 'ato', 'package-agent']`
- `subagent_fixed_skill_total_max_chars: int` tuned lower than main agent
- `subagent_prefix_max_chars: int` tuned lower than main agent
- maybe `subagent_timeout_s`, `subagent_max_turn_seconds`, `subagent_max_tool_loops`

Implementation detail:
- do not mutate the global `orchestrator` config in place
- derive a dedicated `AgentConfig` clone for package workers

## Runtime Architecture

### Recommendation: dedicated package worker control layer

Add a new internal service, e.g.:
- [`src/atopile/server/agent/package_workers.py`](../src/atopile/server/agent/package_workers.py)

This service should own:
- child run records
- parent/child mapping
- concurrency limits
- background task creation
- child status and result summaries
- completion callbacks back into the parent run/session

Do not overload `routes/agent/state.py` session active-run state for this.

### Proposed worker model

A child package worker needs its own state model, separate from `AgentRun`:

```python
@dataclass
class PackageWorkerRun:
    worker_id: str
    parent_run_id: str
    parent_session_id: str
    project_root: str
    package_project_path: str
    status: Literal['running', 'completed', 'failed', 'stopped']
    goal: str
    comments: str | None
    selected_targets: list[str]
    created_at: float
    updated_at: float
    response_id: str | None
    result_summary: str | None
    changed_files: list[str]
    build_summaries: list[dict[str, Any]]
    tool_traces: list[ToolTrace]
    error: str | None
    task: asyncio.Task | None
```

Important:
- each sub-agent has its own provider response chain
- sub-agent `previous_response_id` must never share the parent session chain
- child state can remain in memory first; no need to persist to disk in v1

### How a package agent runs

When the main agent calls `package_agent_spawn`:
1. validate the requested `project_path`
2. ensure it resolves to a nested package project with its own `ato.yaml`
3. ensure the parent run has fewer than 3 active children
4. create a `PackageAgentRun`
5. start a background task that invokes `AgentRunner.run_turn(...)`
6. use the nested package root as `project_root`
7. pass a child-specific config and skill set
8. return immediately to the parent with the `worker_id`

### Child initial message

The child initial user request should be synthesized, not copied verbatim from the parent.

Recommended structure:
- package project path
- package identifier if available
- package build targets
- the main agent's explicit goal
- optional main-agent comments/priorities
- a short parent design context summary
- strict instruction that the child owns only this package

Example shape:

```text
You are responsible for the package project at packages/Raspberry_Pi_RP2350A.
Build a generic, reusable package wrapper that exposes standard interfaces and validates cleanly.

Main-agent goal:
- Finish the RP2350 package wrapper and validate its package build.

Main-agent comments:
- Prioritize USB, SWD, QSPI flash, power pins, and crystal support.
- Keep board-specific role names out of the wrapper.

Constraints:
- Do not edit the top-level design unless absolutely necessary.
- Keep the wrapper generic.
- Build package targets incrementally until green.
```

## Tool Scoping

### Same tools, narrower root

The cleanest way to satisfy “same tools” is:
- reuse the same `ToolRegistry`
- run the child with `project_root=<nested package root>`

That means the package agent naturally gets:
- `project_read_file`, `project_edit_file`, `project_list_files`
- `build_run`
- `parts_search`, `parts_install`
- `web_search`
- etc.

But those tools operate inside the package project by default.

This is the correct isolation boundary.

### Package-local supporting parts

This is already partly solved by the recent `parts_install(project_path=...)` work.

For package workers:
- default `project_root` should already be the package root
- `parts_install(...)` inside the child should therefore land in the package project without extra arguments

This is exactly why the package worker should be rooted at the package project, not the top-level design.

## Parent / Child Coordination

### Completion handoff

When a child finishes, the parent run needs to learn that without constantly polling.

Use the same pattern already used for build-completion steering in [`routes/agent/utils.py`](../src/atopile/server/routes/agent/utils.py):
- inject a steering message into the parent run when a child completes

Example injected message:

```text
[package agent completed] package=packages/Raspberry_Pi_RP2350A status=completed changed_files=3 builds=2 summary=Wrapped RP2350 power, SWD, USB, and crystal support; package target now builds.
```

This gives the main agent asynchronous awareness while still allowing explicit `package_agent_wait` / `package_agent_get` tools.

### Stop behavior

Parent stop should not hard-cancel running package workers by default.

Recommended behavior:
- stopping the parent run stops the parent gracefully
- already spawned child runs continue in background unless explicitly stopped
- the parent handoff should mention active child workers

Reason:
- user may want the delegated package work to continue while the main run yields

### Failure behavior

If a child fails:
- its failure summary should be injected to the parent as steering
- `package_agent_wait` / `package_agent_get` should expose the error and final traces
- the parent can decide whether to respawn a new worker with revised comments or take over manually

## UI / Trace UX

Package workers should be represented in the UI as first-class worker cards, even if V1 keeps the rendering minimal.

### V1 UI

Add a `Package Workers` section in the agent panel when any workers exist.

Each worker row/card should show:
- package name or `project_path`
- status
- latest activity summary
- changed files count
- latest build status
- created/completed timestamps

Actions:
- `View`
- `Wait`
- `Stop`

The parent transcript/tool trace should still show:
- when a worker was spawned
- completion/failure summaries

### V2 UI

Optionally add:
- expandable worker trace cards
- inline child tool summary
- per-worker changed-files summary
- explicit user-launched package workers from the UI, not just agent-launched ones

### Why this matters now

Even if package workers are first used only by the main agent, the state model should already support direct UI exposure.

That means the backend should return structured worker records suitable for:
- tool results
- API polling
- event-bus progress updates
- future user-launched package worker flows

## Context Budget Strategy

The requested 240k-token cap is reasonable, but it should not only be enforced at the provider hard limit.

For package workers:
- reduce fixed skill set
- reduce context summary breadth
- list fewer context files
- keep user/request synthesis tight
- keep tool-output truncation aggressive enough to avoid ballooning

Recommended initial tuning:
- `context_hard_max_tokens = 240_000`
- `fixed_skill_total_max_chars` around 80k-120k
- `prefix_max_chars` around 120k
- smaller project context file count than the main agent

Because package workers are package-local, they do not need the same broad top-level design context.

## Implementation Plan

### Phase 1: Prompt and config groundwork

1. Add `package-agent` skill.
2. Add sub-agent config fields to `AgentConfig`.
3. Add helper for building a child-specific `AgentConfig` and system prompt.

### Phase 2: Internal package worker control layer

1. Add `package_workers.py` service and worker run model.
2. Add in-memory child run store and concurrency guard.
3. Add helper to synthesize the package-agent initial request.
4. Reuse `AgentRunner.run_turn(...)` in a background task with child config.

### Phase 3: Tool family

1. Add tool definitions:
   - `package_agent_spawn`
   - `package_agent_list`
   - `package_agent_wait`
   - `package_agent_get`
   - `package_agent_stop`
2. Register implementations in `tools.py`.
3. Add mediator catalog descriptions so the main agent discovers them naturally.
4. Add/update main-agent skill guidance describing when to delegate and what to pass.

### Phase 4: Parent coordination

1. Inject child completion/failure steering into parent runs.
2. Include active child summaries in graceful-stop handoff.
3. Make `package_agent_wait` robust enough for the main agent to block until completion when needed.
4. Add event payloads/API shape for package worker status so the UI can render worker cards.

### Phase 5: Testing

Add focused tests for:
- max 3 concurrent child workers
- child rooted at nested package path
- child gets package-agent skill set, not main planning stack
- child does not create `.ato/modules/local/...` mirrors
- parent receives completion steering
- stop behavior does not destroy child runs by default
- `package_agent_wait` returns coherent changed-files/build summaries
- context cap/config override for child runner is applied
- main-agent guidance/examples prefer delegation by `project_path`
- worker API payload is sufficient for both tool results and direct UI rendering

## Risks and Mitigations

### Risk: package agent edits outside its package
Mitigation:
- run child with package root as `project_root`
- reinforce scope in `package-agent` skill
- keep top-level edits as an exceptional path

### Risk: parent spawns children and never collects results
Mitigation:
- inject completion steering automatically
- add checklist guidance in main skills for delegation follow-up

### Risk: child context still too large
Mitigation:
- smaller skill set
- smaller project context build
- explicit 240k hard cap
- tighter output truncation

### Risk: duplicated runtime logic
Mitigation:
- reuse `AgentRunner`, `OpenAIProvider`, `ToolRegistry`
- isolate only child-run state/scheduling in a new manager

## Recommendation

Build this as a first-class internal worker system, not as a UI-level hack and not by overloading the top-level `AgentRun` state.

The right architectural split is:
- parent agent remains the user-facing orchestrator
- package agents are internal background workers with their own response chains
- all workers reuse the same runner/provider/tool stack
- package workers are scoped by project root and prompted with a package-specialist skill
- package workers are exposed through a normal tool/API boundary so they can later be launched directly from the UI as well

That will give you real delegation without corrupting the current session/run semantics.
