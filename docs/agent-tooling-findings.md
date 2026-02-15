# Atopile Agent Tooling Findings (CLI + Server Review)

## Scope

This document reviews the current atopile CLI and server capabilities against the requested agent use cases, with a focus on **tool-first integration** (not shell/Bash-driven behavior).

Requested capabilities:

1. Search + install parts
2. Search + install packages
3. Run builds
4. Create builds
5. Rename builds
6. Search build logs (including build-id discovery)
7. Inspect variable report and BOM
8. Generate manufacturing output with an LLM review flow matching current human review quality

---

## Executive Summary

The backend already exposes most of what an agent needs through typed APIs and websocket actions. The major blockers for high-quality tool use are:

1. No dedicated **build log search API** (text search/filtering over log messages).
2. Build-id discovery is somewhat fragmented; client expects `/api/logs/build-ids` but no such route is currently present in server routes.
3. Manufacturing review data exists, but there is no single aggregated "readiness/review summary" endpoint for agent consumption.
4. Tool surface is broad and inconsistent between REST and websocket action names/response shapes.

These are fixable with a thin "agent tool gateway" plus 2-3 targeted API additions.

---

## Capability Matrix (Current State)

## 1) Search + install parts

- Server routes:
  - `GET /api/parts/search` (`src/atopile/server/routes/parts_search.py:77`)
  - `POST /api/parts/install` (`src/atopile/server/routes/parts_search.py:164`)
  - `POST /api/parts/uninstall` (`src/atopile/server/routes/parts_search.py:192`)
  - `GET /api/parts/{lcsc_id}/details` (`src/atopile/server/routes/parts_search.py:97`)
  - `POST /api/parts/lcsc` for stock/pricing (`src/atopile/server/routes/parts.py:21`)
- Domain:
  - Search/install implementation in `src/atopile/server/domains/parts_search.py:138` and `src/atopile/server/domains/parts_search.py:187`.
- CLI:
  - Part creation/install flow via `ato create part` (`src/atopile/cli/create.py:743`).

Status: **Supported now** (good candidate for direct tool mapping).

Notes:

- Search behavior depends on provider config (`ATOPILE_PARTS_SEARCH_PROVIDER`) and may behave differently across environments (`src/atopile/server/domains/parts_search.py:141`).

## 2) Search + install packages

- Server routes:
  - `GET /api/registry/search` (`src/atopile/server/routes/packages.py:76`)
  - `POST /api/packages/install` (`src/atopile/server/routes/packages.py:206`)
  - `POST /api/packages/remove` (`src/atopile/server/routes/packages.py:216`)
  - `POST /api/packages/sync` (`src/atopile/server/routes/packages.py:226`)
- Websocket actions:
  - `searchPackages`, `installPackage`, `removePackage`, `syncPackages` (`src/atopile/server/domains/actions.py:360`, `src/atopile/server/domains/actions.py:596`, `src/atopile/server/domains/actions.py:853`, `src/atopile/server/domains/actions.py:1294`).
- CLI:
  - `ato add`, `ato remove`, `ato sync` (`src/atopile/cli/install.py:138`, `src/atopile/cli/install.py:187`, `src/atopile/cli/install.py:83`).

Status: **Supported now**.

Notes:

- REST package actions are async-like but return generic messages.
- Websocket actions are richer for UI/event workflows (e.g., include operation/build IDs and emit events).

## 3) Run builds

- Server routes:
  - `POST /api/build` (`src/atopile/server/routes/builds.py:34`)
  - `GET /api/build/{build_id}/status` (`src/atopile/server/routes/builds.py:44`)
  - `POST /api/build/{build_id}/cancel` (`src/atopile/server/routes/builds.py:53`)
  - `GET /api/builds/active` (`src/atopile/server/routes/builds.py:62`)
  - `GET /api/builds/history` (`src/atopile/server/routes/builds.py:91`)
  - `GET /api/builds` (project/target filtered lookup) (`src/atopile/server/routes/builds.py:120`)
- Websocket action:
  - `build` (`src/atopile/server/domains/actions.py:390`)
- CLI:
  - `ato build` (`src/atopile/cli/build.py:316`)

Status: **Supported now**.

## 4) Create builds (build targets)

- Server route:
  - `POST /api/build-target/add` (`src/atopile/server/routes/projects.py:111`)
- Websocket action:
  - `addBuildTarget` (`src/atopile/server/domains/actions.py:1154`)
- CLI:
  - `ato create build-target` (`src/atopile/cli/create.py:582`)

Status: **Supported now**.

## 5) Rename builds (build targets)

- Server route:
  - `POST /api/build-target/update` (`src/atopile/server/routes/projects.py:129`)
- Websocket action:
  - `updateBuildTarget` (`src/atopile/server/domains/actions.py:1165`)
- Domain implementation supports rename and entry update:
  - `update_build_target(...)` (`src/atopile/server/domains/projects.py:404`)
- CLI:
  - No dedicated rename command found; CLI primarily supports creation. Rename capability is currently server/API-first.

Status: **Supported in server/api; CLI gap**.

## 6) Search build logs + build-id discovery

- Current log retrieval:
  - `WS /ws/logs` supports:
    - build-id scoped query
    - stage filter
    - level filter
    - streaming via `after_id`
  - (`src/atopile/server/routes/logs.py:94`)
- Current DB query support:
  - Build logs query currently filters by `build_id`, `stage`, `level`, `audience`; no message text filter (`src/atopile/model/sqlite.py:346`).
- Build-id discovery options today:
  - `GET /api/builds/history`, `GET /api/builds`, `GET /api/builds/active` (build IDs included).
- Gap:
  - UI client contains `api.logs.buildIds()` calling `/api/logs/build-ids` (`src/ui-server/src/api/client.ts:196`), but corresponding server route is not present in reviewed routes.

Status: **Partially supported**. Core log access exists; text search and dedicated build-id list API are missing/inconsistent.

## 7) Inspect variable report and BOM

- Server routes:
  - `GET /api/bom`, `GET /api/bom/targets` (`src/atopile/server/routes/artifacts.py:22`, `src/atopile/server/routes/artifacts.py:46`)
  - `GET /api/variables`, `GET /api/variables/targets` (`src/atopile/server/routes/artifacts.py:61`, `src/atopile/server/routes/artifacts.py:85`)
  - Build-id keyed variants:
    - `GET /api/build/{build_id}/bom` (`src/atopile/server/routes/artifacts.py:158`)
    - `GET /api/build/{build_id}/variables` (`src/atopile/server/routes/artifacts.py:179`)
- Websocket actions:
  - `refreshBOM`, `fetchVariables`, `getBomTargets`, `getVariablesTargets` (`src/atopile/server/domains/actions.py:522`, `src/atopile/server/domains/actions.py:560`).

Status: **Supported now**.

## 8) Generate manufacturing output + review summary

- Server routes:
  - `GET /api/manufacturing/outputs` (`src/atopile/server/routes/manufacturing.py:265`)
  - `POST /api/manufacturing/export` (`src/atopile/server/routes/manufacturing.py:351`)
  - `GET /api/manufacturing/board-summary` (`src/atopile/server/routes/manufacturing.py:378`)
  - `POST /api/manufacturing/detailed-estimate` (`src/atopile/server/routes/manufacturing.py:441`)
  - `POST /api/manufacturing/estimate-cost` (`src/atopile/server/routes/manufacturing.py:301`)
- Websocket actions:
  - `getManufacturingOutputs`, `exportManufacturingFiles`, `getBoardSummary`, `getDetailedCostEstimate`, `estimateManufacturingCost` (`src/atopile/server/domains/actions.py:1696`, `src/atopile/server/domains/actions.py:1766`, `src/atopile/server/domains/actions.py:1820`, `src/atopile/server/domains/actions.py:1796`, `src/atopile/server/domains/actions.py:1722`).
- Current UI review includes:
  - Artifact checks, visual review tabs (BOM/3D/Layout), board summary, cost breakdown, export readiness (`src/ui-server/src/components/manufacturing/BuildReviewCard.tsx:55`, `src/ui-server/src/components/manufacturing/ManufacturingPanel.tsx:1046`).

Status: **Mostly supported**. Missing a single backend "review synthesis" endpoint optimized for agent consumption.

---

## Important Findings for "No Bash" Agent Design

1. Almost all required operations are already available via REST/WS APIs.
2. Shell/Bash should be unnecessary for normal agent flows if we expose a curated tool set.
3. Current backend action system (`handle_data_action`) already centralizes many operations (`src/atopile/server/domains/actions.py:317`), making it a strong integration point.

Recommended policy:

- Do not provide shell tools in the agent tool registry for normal sidebar chat.
- Only expose typed domain tools (parts, packages, builds, logs, artifacts, manufacturing, files).
- If a capability is unavailable via tool, return a structured "unsupported tool action" response rather than falling back to shell.

---

## Gaps and Recommended API Additions

## P0: Build log search API

Problem:

- Current log queries require build ID and do not support text search over message content.

Recommendation:

- Add `GET /api/logs/search` (or websocket action) with filters:
  - `query` (message full-text/LIKE)
  - optional `project_root`, `target`, `build_id`, `stage`, `levels`, `audience`, `limit`, `after_id`
- Return rows with `build_id`, `timestamp`, `stage`, `level`, `message`, `source_file`, `source_line`.

Implementation hint:

- Extend `Logs.fetch_chunk` query logic in `src/atopile/model/sqlite.py:346` to include message search clause.

## P0: Build-id discovery endpoint consistency

Problem:

- Client has `/api/logs/build-ids` call (`src/ui-server/src/api/client.ts:196`), but server route is missing in reviewed routes.

Recommendation:

- Add `GET /api/logs/build-ids?project_root=&target=&limit=`.
- Return:
  - `build_id`
  - `project_root`
  - `target`
  - `started_at`
  - `last_timestamp`
  - `log_count`

This gives the agent a deterministic entry point into logs.

## P1: Manufacturing review synthesis endpoint

Problem:

- Data exists across multiple endpoints, but no single "go/no-go" or "review packet" response.

Recommendation:

- Add `POST /api/manufacturing/review` that aggregates:
  - outputs availability
  - board summary
  - detailed estimate
  - BOM summary (unique/total, missing supplier IDs, out-of-stock counts)
  - top warnings/errors from logs
  - readiness blockers list
  - recommended next actions

This makes LLM output consistent with existing human-oriented panel review.

## P1: Response shape normalization

Problem:

- REST + websocket actions differ in naming and payload richness.

Recommendation:

- Define canonical response envelopes for tool execution:
  - `{ success, data, error, warnings, operation_id, build_id }`

---

## Proposed Agent Tool Contract (No Shell)

Expose a compact, high-signal tool set (examples):

1. `projects.list()`
2. `build_targets.create(project_root, name, entry)`
3. `build_targets.update(project_root, old_name, new_name?, new_entry?)`
4. `builds.run(project_root, targets, include_targets?, exclude_targets?, frozen?)`
5. `builds.status(build_id)`
6. `builds.list(project_root?, target?, limit?)`
7. `logs.search(query, project_root?, target?, build_id?, stage?, levels?, limit?)` (new)
8. `artifacts.bom(project_root?, target?, build_id?)`
9. `artifacts.variables(project_root?, target?, build_id?)`
10. `parts.search(query, limit?)`
11. `parts.install(project_root, lcsc_id)`
12. `packages.search(query, path?)`
13. `packages.install(project_root, package_identifier, version?)`
14. `manufacturing.review(project_root, target, quantity, assembly_type)` (new)
15. `manufacturing.export(project_root, targets, directory, file_types)`

Design rules:

- Strong JSON Schemas for all tools.
- Explicit idempotency guidance in tool descriptions.
- Mutating tools return operation/build IDs.
- Use per-project `allowed_tools` narrowing to reduce model confusion.

---

## Manufacturing LLM Flow (Target Behavior)

Goal: Provide the same practical review humans get today before export/order.

Recommended flow:

1. Ensure build target exists.
2. Run build with manufacturing targets (`mfg-data`; optionally include 3D).
3. Wait for terminal status; collect build ID.
4. Fetch aggregated review packet (`manufacturing.review`).
5. If blockers exist (missing artifacts, out-of-stock, failed checks), present actionable fixes.
6. On user confirmation, call export tool.
7. Return exported file list + destination path.

This should be implemented as either:

- A macro tool (`manufacturing.review_and_export`) plus atomic tools, or
- A planner-executor loop over atomic tools with hard stop conditions.

---

## State of the Art Tool-Use Patterns (What Applies Here)

These patterns are the best fit for atopile’s environment:

1. **Schema-locked tool calling**
   - Use strict function schemas, avoid free-form arguments.
   - OpenAI docs recommend strict mode and controlled tool choice.
2. **Curated, minimal active tool set**
   - Keep only relevant tools enabled per turn/workflow to reduce wrong tool calls.
3. **Planner + executor split**
   - Plan steps at high level, execute one tool call at a time with validation after each call.
4. **Read/write separation with approvals**
   - Reads auto-run; writes require explicit confirmation or policy gate.
5. **Deterministic recovery**
   - Tool errors should return structured retry hints and stable error codes.
6. **Security-first MCP/tool ingestion**
   - Treat tool descriptions and outputs as untrusted input; gate risky actions.

Why this matters:

- Research benchmarks show multi-step cross-tool orchestration remains difficult and degrades with broad tool inventories.
- Security research and platform docs both emphasize prompt-injection risk in tool-integrated systems.

---

## Follow-up Focus Areas (Context Freshness + LSP)

These are strong additions and map well to existing atopile architecture.

## 1) Keep project source in-context (small project assumption)

Why this is feasible:

- The extension already has project-local file enumeration in the sidebar bridge (`src/vscode-atopile/src/providers/SidebarProvider.ts:695`, `src/vscode-atopile/src/providers/SidebarProvider.ts:907`).
- It already supports a "focused" mode that excludes hidden noise and only includes `.ato` + `.py` when `includeAll=false` (`src/vscode-atopile/src/providers/SidebarProvider.ts:959`).
- Project/module discovery in backend already skips heavy/generated trees (`build`, `.ato`, `.git`, etc.) (`src/atopile/server/domains/projects.py:181`, `src/atopile/server/domains/projects.py:200`).
- File change signals already exist (`filesChanged`) for freshness (`src/vscode-atopile/src/providers/SidebarProvider.ts:327`, `src/ui-server/src/components/FileExplorerPanel.tsx:598`).

Recommended implementation:

1. Add extension bridge messages for source reads:
   - `readFiles(projectRoot, paths[])`
   - `readFilesByGlob(projectRoot, includeGlobs, excludeGlobs, maxFiles, maxBytes)`
2. Return structured metadata per file:
   - `path`, `size`, `mtime`, `sha256`, `content`
3. Build a `project.context_snapshot` tool that combines:
   - `ato.yaml`
   - selected `.ato` source files
   - optional `.py` helpers used by project
   - module list from `/api/modules`
4. Keep cache fresh by invalidating on:
   - `filesChanged`
   - selected project/target change
   - active editor file change

Result: small-project source can stay resident in model context without pulling KiCad/build artifacts.

## 2) Build history summary as cheap, high-value context

What exists now:

- Active and historical builds are already queryable (`/api/builds/active`, `/api/builds/history`) (`src/atopile/server/routes/builds.py:62`, `src/atopile/server/routes/builds.py:91`).
- A summary route exists (`/api/summary`) (`src/atopile/server/routes/builds.py:27`, `src/atopile/model/builds.py:45`).
- Frontend already computes a concise "active + latest historical per target" view (`src/ui-server/src/api/websocket.ts:514`).

Gap:

- No explicit API payload optimized for "agent context packet" (in-progress + recent failures + short reason digest).

Recommended implementation:

1. Add `GET /api/builds/agent-summary` with:
   - active builds
   - last N completed builds per target
   - failure/warning digest
2. Include cheap error summaries per failed build:
   - top 1-3 ERROR/ALERT messages
   - stage + source file/line when present
3. Keep it bounded (token-aware):
   - max targets, max builds/target, max digest chars/build

This gives the agent immediate operational awareness with very low cost.

## 3) LSP context injection (highest leverage for code-aware behavior)

What exists now:

- LSP is already running in the extension (`ato lsp start`) (`src/vscode-atopile/src/common/lspServer.ts:76`, `src/vscode-atopile/src/common/lspServer.ts:119`).
- Server supports diagnostics, completion, hover, definition, references, rename (`src/atopile/lsp/lsp_server.py:1239`, `src/atopile/lsp/lsp_server.py:1256`, `src/atopile/lsp/lsp_server.py:1407`, `src/atopile/lsp/lsp_server.py:1862`, `src/atopile/lsp/lsp_server.py:2971`, `src/atopile/lsp/lsp_server.py:3181`).

Gap:

- No dedicated webview/agent bridge for retrieving LSP outputs; current bridge mainly exposes active file + file operations (`src/vscode-atopile/src/providers/SidebarProvider.ts:424`, `src/vscode-atopile/src/providers/SidebarProvider.ts:695`).

Recommended implementation:

1. Add extension-side read-only LSP tools:
   - `lsp.getDiagnostics(projectRoot, file?)`
   - `lsp.getHover(file, line, character)`
   - `lsp.getDefinition(file, line, character)`
   - `lsp.getReferences(file, line, character, limit?)`
   - `lsp.getDocumentSymbols(file)`
   - `lsp.searchWorkspaceSymbols(query, limit?)`
2. Add `lsp.context_snapshot(projectRoot, activeFile)` that packages:
   - top diagnostics
   - symbol outline for active file
   - hover/definition for current selection or most recent symbol
3. Enforce strict read-only policy for these tools to reduce risk.

Result: the agent gets semantic context (not just raw text), reducing hallucinations and bad edits.

## Tooling-quality implications for these additions

- Prefer semantic context tools (`lsp.*`, module introspection, build summaries) before raw log/file scans.
- Keep write-capable tools separate from read-only tools in registry exposure.
- Continue "no shell fallback" policy: if a required operation is not mapped to a tool, return structured unsupported-action errors.

---

## Implementation Priorities

## Phase 1 (high impact, low risk)

1. Add logs build-id endpoint and logs search endpoint.
2. Build extension-side tool gateway with strict schemas and no shell tools.
3. Add `project.context_snapshot` (source + module index) with freshness invalidation hooks.
4. Add `builds.agent-summary` endpoint/tool for cheap operational context.
5. Expose only the curated tool set above.

## Phase 2

1. Add LSP read-only tool bridge and `lsp.context_snapshot`.
2. Add manufacturing review aggregator endpoint.
3. Normalize REST/WS response envelopes for agent operations.
4. Add tool-level telemetry/tracing for failure analysis.

## Phase 3

1. Add policy engine (project-scoped allowlists, write approvals, risk tiering).
2. Add regression evals for agent workflows (parts/package/build/manufacturing scenarios).

---

## References

OpenAI docs:

- Function calling guide: https://platform.openai.com/docs/guides/function-calling
- Tools guide (`tool_choice`, `allowed_tools`): https://platform.openai.com/docs/guides/tools
- Structured Outputs announcement: https://openai.com/index/introducing-structured-outputs-in-the-api/
- Responses API updates (incl. remote MCP): https://openai.com/index/new-tools-and-features-in-the-responses-api/
- MCP integration docs: https://platform.openai.com/docs/mcp
- ChatGPT developer mode safety warning: https://platform.openai.com/docs/guides/developer-mode

MCP spec:

- MCP specification overview: https://modelcontextprotocol.io/specification/2025-06-18/basic
- MCP versioning/current revision: https://modelcontextprotocol.io/specification/

Research:

- ReAct (2022): https://arxiv.org/abs/2210.03629
- Toolformer (2023): https://arxiv.org/abs/2302.04761
- MCP-Bench (2025): https://arxiv.org/abs/2508.20453
- MCP server security/maintainability study (2025): https://arxiv.org/abs/2506.13538
