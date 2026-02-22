# Branch Review: feature/deeppcb

## Scope
Reviewed agent/autolayout/deeppcb changes on `feature/deeppcb` with focus on fallback logic, fallback/compatibility regressions, and monolithic control flow.

## Verification run
- `pytest -q test/server/agent/test_agent_tools_hashline.py` → **4 failed / 34 passed**
- `pytest -q test/server/agent/test_hashline_policy.py` → **5 failed / 13 passed**
- `pytest -q test/server/agent/test_orchestrator_output.py` → **1 collection error**
- `pytest -q test/server/agent/test_agent_mediator.py` → **6 passed**
- `pytest -q test/test_autolayout.py` → **4 passed**
- `pytest -q test/test_autolayout_flow.py` → **8 passed**
- `pytest -q test/test_deeppcb_transformer.py` → **19 passed**
- `pytest -q test/test_autolayout_deeppcb_config.py` → **1 failed / 21 passed**

## Must-fix

1. **Restore public/legacy symbols moved out of `agent.policy`**
- `policy.py` now delegates datasheet logic to `policy_datasheet` but does not re-export previously exposed helpers.
- Breaks callers expecting:
  - `policy._detect_datasheet_format`
  - `policy._read_datasheet_bytes_from_url`
  - `policy.lcsc_wmsc_url`
  - `policy.urllib_request`
- Impact: API compatibility regression; test suite currently fails due missing attributes.
- References:
  - `src/atopile/server/agent/policy.py:14`
  - `src/atopile/server/agent/policy_datasheet.py:208`
  - `src/atopile/server/agent/policy_datasheet.py:208-211`
  - `src/atopile/server/agent/policy_datasheet.py:331-347`

2. **`web_search` blocks valid include+exclude domain filters**
- `tools._tool_web_search` rejects calls with both `include_domains` and `exclude_domains` set.
- `_normalize_domain_filters` plus `_exa_web_search` already supports both simultaneously, and tests expect both to pass through.
- References:
  - `src/atopile/server/agent/tools.py:541-550`
  - `src/atopile/server/agent/tool_autolayout_web_helpers.py:526-621`

3. **`_load_layout_component_index` regression breaks monkeypatch/test contract**
- `tools.py` no longer exposes `_load_layout_component_index`, but tests and tool wrappers rely on that module-level helper name for monkeypatching and potential external callers.
- This is now moved to `tool_layout.py` without compatibility forwarding, and tests fail with missing attribute.
- References:
  - `src/atopile/server/agent/tools.py:70` (removed helper export)
  - `src/atopile/server/agent/tool_layout.py:450`
  - `test/server/agent/test_agent_tools_hashline.py:2218`

4. **Missing `_SYSTEM_PROMPT` compatibility export in orchestrator**
- `orchestrator.py` now imports `SYSTEM_PROMPT` from `orchestrator_prompt.py`, but no `_SYSTEM_PROMPT` alias exists.
- Existing tests import `_SYSTEM_PROMPT` from `orchestrator`.
- References:
  - `src/atopile/server/agent/orchestrator.py:56`
  - `src/atopile/server/agent/orchestrator_prompt.py:5`
  - `test/server/agent/test_orchestrator_output.py:13`

5. **Package import cycle in autolayout domain when importing DeepPCB adapter**
- `atopile/server/domains/autolayout/__init__.py` imports `autolayout.service` eagerly.
- `service.py` imports `faebryk.exporters.pcb.autolayout.deeppcb` (provider adapter).
- Importing the provider module via tests triggers circular initialization and `ImportError`.
- References:
  - `src/atopile/server/domains/autolayout/__init__.py:3-6`
  - `src/atopile/server/domains/autolayout/service.py:30-31`
  - `src/faebryk/exporters/pcb/autolayout/deeppcb.py:18`
  - `test/test_autolayout_deeppcb_config.py:18`

6. **`_detect_datasheet_format` misclassifies HTML content when source hints PDF**
- Head/body HTML detection exists first, then raw type/suffix fallback returns `text` for PDF-like content-type/url.
- This makes HTML bytes with `.pdf` or `application/pdf` treated as non-HTML text format.
- The existing unit coverage expects html semantics for this case.
- References:
  - `src/atopile/server/agent/policy_datasheet.py:331-350`

## Should-fix / sketchy areas

1. **Reachable dead branch in DeepPCB padstack conversion**
- In `DeepPCB_Transformer._padstack_from_pad`, the first `if shape in {"circle", "oval"}` branch preempts later `elif provider_strict and shape in {"oval"}` and `elif provider_strict and shape in {"circle", "oval"} and drill_payload...`.
- This means strict oval-specific path is never taken.
- References:
  - `src/faebryk/exporters/pcb/deeppcb/transformer.py:1193-1254`

2. **Monolithic control surfaces need decomposition for maintainability risk**
- Several files now contain very large orchestration/dispatch/control functions with many fallback/guard branches and state transitions in a single method:
  - `src/atopile/server/agent/orchestrator.py` (`AgentOrchestrator._run_worker_turn`, ~450-1120)
  - `src/atopile/server/agent/tools.py` (large handler surface, 2600+ lines)
  - `src/faebryk/exporters/pcb/deeppcb/transformer.py` (large conversion matrix, dense conditionals)
- These are not immediate crashes now, but they are difficult to test/fuzz and easy to regress on fallback logic.

## Positives

- Most end-to-end autolayout/deeppcb transform tests still pass.
- The refactor shows good intent toward module separation and typed tool/scope abstractions.
- Failure signal is concentrated in compatibility and branching edge handling, so fixes should be tractable.
