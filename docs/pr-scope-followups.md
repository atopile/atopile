# PR Scope Follow-up Issues

Purpose: capture behavior that appears out-of-scope for the current agent/autolayout PR so it can be split into separate issues.

## Already removed in this branch

1. Removed planning markdown artifacts from PR scope.
   - Commit: `15f2a804`
2. Removed board outline demo example files.
   - Commit: `7e11fc09`
3. Removed `include_targets` / `exclude_targets` passthrough from `handle_start_build`.
   - Commit: `aa900a9b`

## Candidate follow-up issues

## 1) Build queue stale-timeout behavior changed (likely unrelated)

Issue title:
- `BuildQueue: split stale-timeout + stale_failed event behavior into dedicated reliability change`

Why this is out-of-scope:
- This changes global build lifecycle semantics (timeout/failure persistence), not agent/autolayout feature behavior.

Files:
- `src/atopile/model/build_queue.py:70`
- `src/atopile/model/build_queue.py:73`
- `src/atopile/model/build_queue.py:690`
- `src/atopile/model/build_queue.py:974`
- `src/atopile/model/build_queue.py:1046`

Observed changes:
- New env-configurable retention/timeout constants (`ATO_BUILD_COMPLETED_RETENTION_S`, `ATO_BUILD_STALE_SECONDS`).
- `_cleanup_completed_builds()` now runs in every orchestrator loop iteration.
- Stale `BUILDING` jobs are force-marked `FAILED`, persisted to `BuildHistory`, removed from queue, and emit `stale_failed`.

Risk:
- Unexpected failure state transitions for long builds.
- New event type semantics without explicit product/API contract.

Acceptance criteria for follow-up:
- Explicitly document stale-timeout policy and event contract.
- Add tests for stale timeout + persistence + emitted events.
- Decide whether this should be default behavior or feature-flagged.

## 2) Include/exclude target behavior is currently inconsistent across build entry points

Issue title:
- `Unify include/exclude target semantics across REST, WS, and agent build paths`

Why this is out-of-scope:
- This is cross-cutting build API behavior, not core agent/autolayout functionality.

Files:
- `src/atopile/server/domains/actions.py:47`
- `src/atopile/server/domains/actions.py:50`
- `src/atopile/model/build_queue.py:119`
- `src/atopile/model/build_queue.py:121`
- `src/atopile/server/agent/tool_definitions.py:113`
- `src/atopile/server/agent/tool_definitions.py:118`
- `src/atopile/server/agent/tools.py:1771`
- `src/atopile/server/agent/tools.py:2950`

Current behavior snapshot:
- WS build path still accepts/passes include/exclude targets.
- Queue worker still exports include/exclude env vars.
- Agent tools expose include/exclude fields.
- `handle_start_build` passthrough was removed in this branch (`aa900a9b`).

Risk:
- Different behavior depending on code path (REST vs WS vs agent).
- Hard to reason about build reproducibility.

Acceptance criteria for follow-up:
- Choose one canonical behavior (support everywhere or nowhere).
- Align dataclasses/schema/tools/routes accordingly.
- Add integration tests that assert parity across entry points.

## 3) WebSocket action registry refactor is a large architectural move and should be isolated

Issue title:
- `Split WebSocket action-registry refactor into dedicated PR with regression tests`

Why this is out-of-scope:
- This is broad infra refactoring of action dispatch and handler ownership, beyond agent/autolayout delivery.

Files:
- `src/atopile/server/domains/actions.py:30`
- `src/atopile/server/domains/actions.py:295`
- `src/atopile/server/ws/actions/registry.py`
- `src/atopile/server/ws/actions/core.py`
- `src/atopile/server/ws/actions/ui.py`

Observed changes:
- `handle_data_action` now delegates to `dispatch_registered_action` first.
- Multiple legacy handlers were moved out of `actions.py` into registry modules.

Risk:
- Behavior parity regressions for existing UI actions (`openFile`, `refreshProjects`, config actions).
- Harder to isolate defects while reviewing agent/autolayout changes.

Acceptance criteria for follow-up:
- Add parity matrix old vs new handlers.
- Add smoke tests for all moved actions.
- Keep this refactor in a standalone PR with focused review.

## 4) Optional: generated artifact churn should be isolated

Issue title:
- `Isolate generated schema/lockfile churn from feature PR`

Why this is out-of-scope:
- Review noise increases and obscures functional changes.

Typical files in this branch to review separately:
- `src/ui-server/src/types/gen/generated.ts`
- `src/ui-server/src/types/gen/schema.json`
- `src/vscode-atopile/package-lock.json`
- `uv.lock`

Acceptance criteria for follow-up:
- Regenerate from a pinned toolchain and commit separately.
- Include exact regeneration command in commit message.
