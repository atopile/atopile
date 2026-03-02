# Branch Review: `feature/deeppcb`

**Date:** 2026-03-02
**Scope:** 129 files changed, ~38,300 lines added, ~1,300 removed
**Goal:** Add autolayout (DeepPCB provider) and an LLM agent with tool use

---

## Executive Summary

The branch adds two major features: (1) a DeepPCB autolayout integration and (2) an LLM-powered chat agent. Both are **architecturally well-isolated** — they can be removed without cascading breakage. However, the branch also contains several **unrelated changes** (docstring traits, datasheet pipeline, build queue tuning, websocket action registry) that increase blast radius and should be separated. Individual files are often too large, and there is meaningful code duplication.

### Top-Level Concerns

| # | Severity | Issue |
|---|----------|-------|
| 1 | **HIGH** | `AgentChatPanel.tsx` is 3,282 lines — monolithic UI component |
| 2 | **HIGH** | `tools.py` is 2,599 lines with mixed concerns (OpenAI client, caches, 40+ handlers) |
| 3 | **HIGH** | `transformer.py` is 2,875 lines — reuse block logic (~640 lines) should be separate |
| 4 | **HIGH** | Unrelated changes bundled in branch (node.py docstrings, build_queue stale threshold, datasheets pipeline, WS action registry) |
| 5 | **MEDIUM** | DeepPCB conversion leaks into the provider-agnostic service layer |
| 6 | **MEDIUM** | Thread-unsafe global caches in agent tools |
| 7 | **MEDIUM** | 3 demo scripts and large artifact directories left untracked |
| 8 | **LOW** | Duplicated helper functions across 3+ locations |

---

## 1. Autolayout / DeepPCB Integration

### Architecture (Good)

The layering is clean and well-separated:

```
CLI (cli/autolayout.py)     REST Routes (routes/autolayout.py)
         \                        /
       AutolayoutService (domains/autolayout/service.py)
              |
       _AutolayoutProvider Protocol      ← provider abstraction
              |
       DeepPCBAutolayout (autolayout/deeppcb.py)  ← adapter
              |
       DeepPCBApiClient (libs/deeppcb.py)         ← raw HTTP
              |
       DeepPCB_Transformer (deeppcb/transformer.py) ← format conversion
```

The `_AutolayoutProvider` Protocol at `service.py:37-54` defines a clean provider interface. A different provider could be swapped in with moderate refactoring.

### Issues

**1.1 DeepPCB conversion leaks into service layer (MEDIUM)**
`service.py:432-468` — The service checks for `.deeppcb`/`.json` suffixes and calls `DeepPCB_Transformer` directly. This should be the provider's responsibility. A different provider returning `.kicad_pcb` directly wouldn't need this code.

**1.2 `transformer.py` is too large — 2,875 lines (HIGH)**
Single class handling: forward conversion, reverse conversion, coordinate scaling/flipping, padstack generation, edge-cuts chaining, outline serialization, reuse block collapse (~640 lines), and reuse block expansion. The reuse block logic should be a separate module. The coordinate transform pair (`_provider_scale_flip_coordinates` / `_reverse_provider_coordinates`, ~220 lines each) are structural mirrors and could be unified with a direction parameter.

**1.3 Duplicated `_extract_string` (LOW)**
`libs/deeppcb.py:335` (module function) vs `autolayout/deeppcb.py:1011` (instance method) — identical algorithm, one as module function, one as instance method.

**1.4 Duplicated option-parsing in confirm/resume (LOW)**
`autolayout/deeppcb.py:452-460` and `531-539` — identical timeout/maxBatchTimeout/timeToLive extraction. Extract to shared helper.

**1.5 Hardcoded board-exists endpoint (LOW)**
`autolayout/deeppcb.py:634` — `/api/v1/boards/{task_id}/details` is a literal string while all other endpoints are configurable via `DeepPCBConfig`.

**1.6 Default provider name scattered (LOW)**
`"deeppcb"` is hardcoded independently in `models.py:136` and `service.py:695`. Should be a single constant.

**1.7 CLI has DeepPCB-specific flags (LOW)**
`autolayout.py:181-225` — Options like `--webhook-url`, `--response-board-format` are provider-specific. A provider-agnostic CLI would accept `--option key=value` pairs.

**1.8 Module-global service singleton (LOW)**
`service.py:924` — `_AUTOLAYOUT_SERVICE = AutolayoutService()` instantiated at import time, creating the DeepPCB provider even when autolayout is unused. The lazy `__getattr__` in `__init__.py` mitigates this at the package level.

---

## 2. Agent Module

### Architecture (Good)

The agent module (~12,900 lines across 15 files, plus ~1,720 lines of routes) is well-isolated:
- Clean public API: only `AgentOrchestrator`, `AgentTurnResult`, `ToolTrace` exported
- Good separation of routes (HTTP concerns) vs logic (business logic)
- Tool registry with consistency validation at startup
- Safety guards: loop detection, failure streak limits, time budgets
- **Can be fully removed** without impacting the rest of the codebase

### Issues

**2.1 `tools.py` is 2,599 lines — too large (HIGH)**
Contains ~40 tool handlers, OpenAI file upload client, LRU cache infrastructure, datasheet resolution, build artifact summarization, web search arg parsing. The infrastructure code should be extracted.

**2.2 Thread-unsafe global caches (MEDIUM)**
`tools.py:111-112` — `_openai_file_cache` and `_datasheet_read_cache` are `OrderedDict` with no locking. In an async server with `asyncio.to_thread`, concurrent access can corrupt them.

**2.3 `_infer_prefilled_args` is 470 lines (MEDIUM)**
`mediator_inference.py:205-673` — Single function with a long chain of `if tool_name == "..."` blocks. Should be table-driven or split per-tool.

**2.4 `suggest_tools` is 330 lines (MEDIUM)**
`mediator.py:133-466` — Sequential `if` blocks with identical structure (define keywords, check membership, boost score). Should be a data-driven scoring table.

**2.5 Private member import (MEDIUM)**
`tool_build_helpers.py:9` — `from atopile.model.build_queue import _build_queue`. Imports a private member from another module.

**2.6 Duplicated helpers across modules (LOW)**
- `_resolve_build_target` — identical in `tools.py:488` and `tool_layout.py:15`
- `_trim_message` — identical in `tool_build_helpers.py:66` and `tool_autolayout_web_helpers.py:26`
- `_normalize_newlines` — identical in `policy.py:586` and `policy_datasheet.py:472`

**2.7 `_` prefix on cross-module functions (LOW)**
Functions like `_exa_web_search`, `_footprint_reference` are imported across module boundaries but named as private.

**2.8 `.feedback.md` checked into source (LOW)**
`agent/.feedback.md` — internal development notes shouldn't be in the package.

---

## 3. Frontend / UI

### Issues

**3.1 `AgentChatPanel.tsx` is 3,282 lines — monolithic (HIGH)**
Single React component handling: message rendering, tool call visualization, markdown rendering, file editing UI, autolayout status, datasheet previews, build log display, and more. Should be decomposed into sub-components. The helpers were already extracted to `AgentChatPanel.helpers.ts` (77 lines) — the same pattern should apply to the component itself.

**3.2 `AgentChatPanel.css` is 1,354 lines (MEDIUM)**
Massive CSS file co-located with the monolithic component. Would naturally shrink if the component is decomposed.

**3.3 Generated types checked in (MEDIUM)**
`src/ui-server/src/types/gen/generated.ts` (1,059 lines) and `schema.json` (1,595 lines) appear to be auto-generated. Verify these are regenerated by CI. If manually maintained, they risk drifting from the API.

**3.4 `eventHandler.ts` deleted (LOW)**
`src/ui-server/src/api/eventHandler.ts` (286 lines removed). Websocket event handling moved to the new action registry pattern. Verify no remaining references.

---

## 4. Changes to Existing Files — Blast Radius

### High Risk

| File | Change | Concern |
|------|--------|---------|
| `build_steps.py` | Split `update_pcb` into `apply_board_shape` + `update_pcb`; changed `original_pcb` from `kicad.copy()` to `kicad.loads()` | Changes build DAG structure and baseline semantics for frozen diff check |
| `build_steps.py` | Removed `datasheets` build step entirely | **Breaking** for anyone running `ato build datasheets` |
| `model/build_queue.py` | Stale threshold changed from 3600s to 600s | Builds >10 min now marked failed (was 1 hour) |

### Medium Risk

| File | Change | Concern |
|------|--------|---------|
| `server/domains/actions.py` | Refactored 4 handlers to registry pattern; added 7 autolayout handlers | Registry dispatch runs before if/elif chain — priority inversion risk |
| `faebryk/core/node.py` | Added `_add_module_docstring_trait()` to `_build_type_graph` | **Unrelated to autolayout.** Runs on every type graph construction. Should be separate PR. |
| `lsp/lsp_server.py` | Datasheet path changed | No migration for existing projects |

### Low Risk (Clean Changes)

| File | Change |
|------|--------|
| `config.py` | Additive `AutolayoutConfig` field (optional, defaults `None`) |
| `dataclasses.py` | 3 additive enum values |
| `server/server.py` | Feature flag + router registration |
| `routes/__init__.py` | Additive imports |
| `cli/cli.py` | 2-line subcommand registration |
| `compiler/ast_visitor.py` | `RectangularBoardShape` added to stdlib allowlist |
| `libs/kicad/ipc.py` | Lazy import of kipy (startup optimization) |
| `exporters/pcb/kicad/artifacts.py` | Optional `layers` parameter (backwards-compatible) |
| `server/domains/layout.py` | Handle missing-file case in watcher |
| `libs/picker/lcsc.py` | Removed unused datasheet crawling (was behind disabled flag) |

---

## 5. Unrelated Changes That Should Be Separate PRs

These changes are bundled in the branch but have nothing to do with autolayout or the agent:

1. **`faebryk/core/node.py` — docstring trait attachment.** Independent feature affecting the type graph construction hot path.
2. **`model/build_queue.py` — stale threshold tuning and cleanup.** Behavioral change to build lifecycle.
3. **`server/domains/actions.py` — websocket action registry refactor.** Architectural change to action dispatch.
4. **`faebryk/exporters/documentation/datasheets.py` — deletion** and replacement with `faebryk/libs/datasheets.py`. Datasheet pipeline migration.
5. **`libs/picker/lcsc.py` — datasheet crawling removal.** Part of the datasheets pipeline change.
6. **`faebryk/libs/part_lifecycle.py` — new module.** Part lifecycle management, tangential to autolayout.
7. **`scripts/generate_types.py` — type generation changes.** Should ship with the types PR.

---

## 6. Test Coverage Assessment

### Strengths

- **Transformer roundtrip tests** (`test_deeppcb_transformer.py`) are excellent — parametrized against real PCB files, with controlled inline fixtures for pad fidelity.
- **Reuse block tests** (`test_deeppcb_reuse_blocks.py`, 756 lines, untracked) are comprehensive — 14 focused tests covering all primitive types with self-contained fixtures.
- **Service lifecycle tests** (`test_autolayout.py`) use a proper mock provider and exercise real config parsing.
- **Hashline policy tests** (`test_hashline_policy.py`) validate the critical agent editing mechanism with real filesystem operations.

### Gaps

- **No integration test for the JSON download → convert → expand path** in `service.py:432-468`. This is the new production flow. The `apply_candidate` reuse-block expansion catches all exceptions silently.
- **`test_agent_tools_hashline.py` is 2,234 lines** — could be split into 3-4 focused files.
- **`test_autolayout_flow.py` is minimal** (49 lines, 4 tests) — missing tests for the approval case and score edge cases.
- **No frontend tests** for the 3,282-line `AgentChatPanel.tsx`.

---

## 7. Untracked Files — Cleanup Needed

The following untracked files should not be committed:

**Demo scripts (development artifacts):**
- `demo_deeppcb_e2e.py` (9KB)
- `demo_deeppcb_reuse.py` (8KB)
- `demo_sensor_board.py` (14KB)

**Generated/downloaded artifacts:**
- `examples/esp32_minimal/.autolayout_demo/` — `.deeppcb` files, metadata, zip artifacts
- `examples/esp32_minimal/.autolayout_e2e/` — 20+ debug/test `.deeppcb` files
- `examples/sensor_board/` — new example directory

These should be `.gitignore`d or cleaned up before merge.

---

## 8. Recommendations

### Before Merge

1. **Split unrelated changes** into separate PRs: node.py docstrings, build_queue tuning, datasheets pipeline, WS action registry
2. **Add `.gitignore` entries** for `demo_*.py`, `.autolayout_demo/`, `.autolayout_e2e/`, `*.deeppcb` artifacts
3. **Add integration test** for the JSON download → convert → expand → apply path in `service.py`
4. **Remove `agent/.feedback.md`** from source
5. **Review the `build_queue.py` stale threshold** change from 3600s→600s — could cause false build failures

### Post-Merge / Follow-Up

6. **Decompose `AgentChatPanel.tsx`** into sub-components (message list, tool call renderer, file editor, status indicators)
7. **Split `tools.py`** — extract OpenAI client, cache infrastructure, and arg parsing
8. **Extract reuse block logic** from `transformer.py` into a dedicated module
9. **Move DeepPCB conversion** out of `service.py:apply_candidate` into the provider adapter
10. **Add thread safety** to global caches in `tools.py` (or convert to instance state on the orchestrator)
11. **Refactor `_infer_prefilled_args`** and `suggest_tools` to be data-driven
12. **Deduplicate** `_resolve_build_target`, `_trim_message`, `_normalize_newlines`, `_extract_string`

---

## File Size Summary (New files >500 lines)

| File | Lines | Assessment |
|------|-------|------------|
| `AgentChatPanel.tsx` | 3,282 | **Split into sub-components** |
| `transformer.py` | 2,875 | **Extract reuse block module** |
| `tools.py` | 2,599 | **Extract infrastructure** |
| `orchestrator.py` | 1,885 | Acceptable (helpers already extracted) |
| `AgentChatPanel.css` | 1,354 | Will shrink with component decomposition |
| `autolayout/deeppcb.py` | 1,262 | Acceptable for full provider adapter |
| `orchestrator_helpers.py` | 973 | Acceptable |
| `policy.py` | 953 | Acceptable |
| `service.py` | 931 | Acceptable, but move conversion out |
| `routes/agent/utils.py` | 922 | Borderline — could extract persistence |
| `tool_layout.py` | 807 | Acceptable |
| `mediator_catalog.py` | 731 | Static data — acceptable |
| `mediator_inference.py` | 717 | Refactor: 470-line function |
| `tool_autolayout_web_helpers.py` | 709 | Acceptable |
| `tool_definitions.py` | 560 | Pure schema — acceptable |
| `autolayout.py` (CLI) | 549 | Acceptable |
| `routes/agent/main.py` | 540 | Acceptable |
| `tool_references.py` | 511 | Acceptable |
| `tool_definitions_project.py` | 470 | Pure schema — acceptable |
