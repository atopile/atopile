# Branch Review: feature/deeppcb

Full code review of the `feature/deeppcb` branch (100% Codex-authored).
Focus: identifying AI-generated defensive code, unnecessary fallbacks, smoke tests, monkeypatching, and general code quality issues.

---

## Fixed Issues

### 1. FIXED: Bizarre Test Structure (underscore-prefixed functions + staticmethod class)

All 4 agent test files had every test written as `_test_*()` then re-exposed via a class with `staticmethod`. Converted to normal pytest `test_*` functions. Removed the class wrappers entirely.

- `test/server/agent/test_agent_mediator.py` - 19 tests, removed class + unused `import pytest`
- `test/server/agent/test_agent_tools_hashline.py` - 37 tests, removed 126 lines of class boilerplate
- `test/server/agent/test_hashline_policy.py` - 19 tests, removed class
- `test/server/agent/test_orchestrator_output.py` - 13 tests, removed class

All 89 agent tests pass after restructuring.

### 2. FIXED: Regex Pattern Duplication

Extracted shared patterns from `mediator.py` and `mediator_inference.py` into `mediator_patterns.py`. Both files now import from the shared module.

### 3. FIXED: Phantom Key in `_extract_context_id`

Removed `"fallback_job_id"` from the key lookup list in `mediator_inference.py` - it doesn't exist in any tool result schema.

### 4. FIXED: Dead Tool Names in Worker Set

Removed `project_write_file` and `project_replace_text` from `_worker_execution_tool_names()` in `orchestrator_helpers.py`. Updated `orchestrator_prompt.py` to say "Do not use" instead of "Avoid unless asked for compatibility".

### 5. FIXED: Pydantic v1/v2 Compatibility Shim

Simplified `_response_model_to_dict` in `orchestrator_helpers.py` to call `response.model_dump()` directly instead of duck-typing through `getattr` fallbacks.

### 6. FIXED: Bare Exception Silencing (agent code)

- `orchestrator_helpers.py:_consume_steering_updates` - added `log.warning` with traceback
- `orchestrator.py:_count_input_tokens` - added `log.debug` with traceback

### 7. FIXED: Bare Exception Silencing (DeepPCB provider)

Added `log.debug` with traceback to three bare `except Exception` blocks in `deeppcb.py`:
- `_resolve_board_ids_single`
- `_board_exists`
- `_wait_for_board_not_running`

### 8. FIXED: Unused `target_layout_path` Parameter

Removed from `_persist_downloaded_layout` in `deeppcb.py` and updated all callers (including test).

### 9. FIXED: TypeScript Unnecessary Fallbacks

- `websocket.ts`: Cleaned up `normalizeBuild()` - removed redundant 3rd/4th field name variants, added doc comment
- `websocket.ts`: Removed unnecessary `openFileLine`/`openFileColumn` fallbacks in open_file handler (backend only sends `line`/`column`)
- `websocket.ts`: Removed unnecessary `projectRoot`/`targetName` camelCase fallbacks in OpenLayout handler (backend sends snake_case)
- `ManufacturingPanel.tsx`: Removed all camelCase fallbacks from `normalizeAutolayoutCandidate()` and `normalizeAutolayoutJob()` - backend Pydantic models serialize to snake_case
- `config.ts`: Removed silent catch fallback in `httpToWsUrl()` - let invalid URLs fail loudly
- `3dmodel.ts`: Removed redundant `isFile = false` in catch block

---

## Remaining Issues (not fixed in this pass)

### Smoke Tests (Quality)

The agent tests still mostly check "does tool X exist in the set" rather than testing real behavior. This is a test quality issue that requires writing new tests, not just refactoring existing ones.

### Dual camelCase/snake_case in Python Options

`autolayout/service.py`, `deeppcb.py`, and `actions.py` still check both `auto_apply`/`autoApply`, `force_new_job`/`forceNewJob`, etc. This is a deeper issue: the option dicts come from different callers (REST API, WebSocket, CLI) that may use different conventions. Fixing this requires establishing a canonical format at the API boundary and normalizing there.

### Bare `except Exception` in Server/Routes

Several locations in `server.py`, `actions.py`, and `routes/agent/utils.py` still have bare exception blocks. These are in cleanup/shutdown code and session persistence where silently continuing may be intentional. These should be evaluated case-by-case.

### `_padstack_from_pad` Complexity

The 140-line if/elif chain in `transformer.py` mixing `provider_strict` with shape type is still present. This is a correctness-sensitive code path where splitting into two methods needs careful testing to avoid subtle behavior changes.

### Multi-Endpoint Retry Chains in DeepPCB

The DeepPCB provider still tries multiple API endpoint templates. This may be required by the actual DeepPCB API versioning. Needs confirmation from the API docs before consolidating.

### AgentChatPanel.tsx Snapshot Validation

The 80-line hand-written typeof validation for localStorage persistence is still present. This is functional and correct, but verbose. A zod schema would be cleaner.

---

## Test Results

All 152 relevant tests pass after cleanup:
- 89 agent tests (4 files)
- 63 autolayout/deeppcb tests (4 files)

TypeScript compilation passes with no errors.
