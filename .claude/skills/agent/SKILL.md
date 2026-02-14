---
name: agent
description: "Source-of-truth for the atopile sidebar agent: tool contracts, execution order, safety rules, and validated behavior for all advertised agent tools."
---

# Agent Module

This is the canonical skill for the atopile server-side agent (`/api/agent`).
Use this when changing agent tool behavior, orchestrator prompts, tool policies, or UI expectations tied to tool traces.

## Quick Start

1. Inspect tool schemas in `src/atopile/server/agent/tools.py` (`get_tool_definitions`).
2. Confirm UI-facing metadata in `src/atopile/server/agent/mediator.py`.
3. Validate orchestration rules in `src/atopile/server/agent/orchestrator.py`.
4. Validate scope/edit invariants in `src/atopile/server/agent/policy.py`.
5. Run focused tests:
   - `ato dev test --llm test/server/agent -q`

## Source of Truth Files

- `src/atopile/server/agent/tools.py` (tool schemas + execution behavior)
- `src/atopile/server/agent/orchestrator.py` (system prompt + tool loop behavior)
- `src/atopile/server/agent/policy.py` (scope, hashline editing, path safety)
- `src/atopile/server/agent/mediator.py` (tool directory, suggestions, stale memory)
- `src/atopile/server/routes/agent.py` (session/run APIs and event emission)
- `src/ui-server/src/components/AgentChatPanel.tsx` (tool-trace rendering semantics)

## Tool Catalog (Advertised)

### Project Inspection

- `project_list_files`
- `project_read_file`
- `project_search`
- `project_list_modules`
- `project_module_children`

### Reference Examples

- `examples_list`
- `examples_search`
- `examples_read_ato`

### Stdlib Discovery

- `stdlib_list`
- `stdlib_get_item`

### Scoped Edits

- `project_edit_file`
- `project_rename_path`
- `project_delete_path`

### Parts and Datasheets

- `parts_search`
- `parts_install`
- `datasheet_read`

### Packages

- `packages_search`
- `packages_install`

### Builds and Diagnostics

- `build_run`
- `build_create`
- `build_rename`
- `build_logs_search`
- `design_diagnostics`

### Reports and Manufacturing

- `report_bom`
- `report_variables`
- `manufacturing_generate`
- `manufacturing_summary`

## Manual Validation (2026-02-14)

All advertised tools were manually invoked through `execute_tool(...)` against a real project copy (`examples/quickstart` in a temp workspace), with real network/tool behavior enabled.

Validated: 27/27 advertised tools executed successfully (plus an extra `project_read_file` used for edit-anchor prep).

- PASS `project_list_files`
- PASS `project_read_file`
- PASS `project_search`
- PASS `examples_list`
- PASS `examples_search`
- PASS `examples_read_ato`
- PASS `project_list_modules`
- PASS `project_module_children`
- PASS `stdlib_list`
- PASS `stdlib_get_item`
- PASS `project_edit_file`
- PASS `project_rename_path`
- PASS `project_delete_path`
- PASS `parts_search`
- PASS `parts_install`
- PASS `datasheet_read`
- PASS `packages_search`
- PASS `packages_install`
- PASS `build_run`
- PASS `build_create`
- PASS `build_rename`
- PASS `build_logs_search`
- PASS `design_diagnostics`
- PASS `report_bom`
- PASS `report_variables`
- PASS `manufacturing_generate`
- PASS `manufacturing_summary`

## Behavior Notes (Important)

- `build_run` and `manufacturing_generate` returning success means the build was queued, not necessarily completed successfully.
- `build_logs_search` can return a synthetic diagnostic log entry when no real logs were captured.
- `report_bom` / `report_variables` return `found=false` with actionable guidance when artifacts are missing.
- `datasheet_read` uses graph-first datasheet resolution, then falls back to part API URL lookup, and uploads the PDF as an OpenAI file.
- `project_edit_file` is the primary write path; use anchors from `project_read_file` exactly (`LINE:HASH`).
- `build_create` + `build_rename` can create config states that later fail build-time validation if entrypoint constraints are violated; always verify with `build_run` and `build_logs_search`.

## Timing Expectations

- `project_*`, `stdlib_*`, and metadata tools are typically fast (sub-second to a few seconds).
- `parts_search`, `packages_search`, and `datasheet_read` depend on network/API latency and can take several seconds.
- `parts_install` and `packages_install` can take seconds to tens of seconds depending on dependency resolution and downloads.
- `build_run` and `manufacturing_generate` are async queue operations:
  - the tool call usually returns quickly (queue acknowledged),
  - the actual build can take a few seconds to a few minutes for complex designs.
- `manufacturing_summary` is usually quick once artifacts exist, but can be slower when cost estimation needs additional analysis.

Recommended pattern:

1. Queue build (`build_run` or `manufacturing_generate`).
2. Poll/inspect via `build_logs_search`.
3. Read outputs/reports (`report_bom`, `report_variables`, `manufacturing_summary`) only after build completion.

## Writing `.ato` Code: Example Discovery Guidance

The agent has dedicated tools for curated reference examples.

Use this sequence:

1. `examples_list` to discover curated examples and available `.ato` files.
2. `examples_search` to find matching patterns/snippets across all examples.
3. `examples_read_ato` to pull exact code from one example file.
4. `project_list_modules` / `project_module_children` to align patterns to the current project structure.
5. `stdlib_list` / `stdlib_get_item` to map examples to canonical building blocks.
6. `packages_search` + `packages_install` when a reusable dependency is better than custom code.

Practical implication:

- Yes, the agent can retrieve relevant `.ato` examples/patterns from curated examples, local project structure, and stdlib metadata.

## Reference Examples (Atopile)

Use repo examples as canonical pattern references when authoring `.ato`:

- `examples/quickstart/quickstart.ato`
  - Minimal module/component/parameter assignment.
- `examples/passives/passives.ato`
  - Passive parts, constraints, and simple connectivity.
- `examples/equations/equations.ato`
  - Parameter equations, symbolic constraints, solver-friendly formulations.
- `examples/pick_parts/pick_parts.ato`
  - Auto-picking and explicit part selection (`lcsc_id`, `manufacturer`, `mpn`).
- `examples/i2c/i2c.ato`
  - Module templating, loops, address configuration, and multi-interface wiring.
- `examples/esp32_minimal/esp32_minimal.ato`
  - Package imports, USB/power rails, realistic subsystem composition.
- `examples/layout_reuse/layout_reuse.ato`
  - Reuse of pre-existing layout via sub-module composition.
- `examples/led_badge/led_badge.ato`
  - Larger mixed-signal style design with chained submodules and net naming.

How to use current tools for examples:

1. Use `examples_list` to see available example projects and `.ato` files.
2. Use `examples_search` to locate relevant syntax/constraint patterns.
3. Use `examples_read_ato` to fetch exact code chunks.

## Invariants

- Never edit files outside scoped project root.
- Prefer `project_edit_file` over any non-hashline edit path.
- Treat tool outputs as typed contracts; do not infer missing fields.
- For diagnostics and manufacturing flows, always check logs after queueing builds.
