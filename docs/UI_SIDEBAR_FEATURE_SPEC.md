# Sidebar Feature Spec (Intent-First)

## Context

This spec is meant to be handed to an engineer to implement the backend support
for the sidebar UI. It is **intent-focused**: it captures **what the UI needs**
and **why**, not a specific code structure. It also documents the architectural
shift from the previous “state-push” model to the stage/0.14 event‑bus model.

## Architecture Summary (Old vs New)

### Previous Model (Branch UI / AppState Push)
- Backend owned a global AppState and pushed full state over `/ws/state`.
- UI subscribed to state broadcasts and rendered directly from that state.
- Actions mutated server state; results arrived via the next full-state push.
- Simpler UI wiring but heavy payloads and tight backend/UI coupling.

### Stage/0.14 Model (Event‑Bus + Refetch)
- Backend emits **targeted events** (e.g., `projects_changed`) over WebSocket.
- UI listens for events and **refetches only the affected slice** via HTTP/action.
- Backend does **not** own UI state; UI store is frontend‑only.
- Encourages clearer contracts, smaller payloads, and independent UI evolution.

This document captures the **intent and UX behavior** required by the current sidebar UI. It is not an implementation spec. It describes **what the UI needs** from the backend and extension host, panel by panel.

## Global Notes

- The sidebar reads from a single app state store and sends actions over WebSocket.
- The UI expects *event-driven refresh* for some data, and *response-returning actions* for others.
- Active project and target selection drive BOM/Variables requests and the Structure panel.
- All actions should be idempotent and safe to retry; UI can send the same action multiple times during refresh.

## Sidebar Header (Settings + Version Control)

### Intent
Let users pick which `atopile` build to use (release, branch, local), observe install progress/errors, and configure a small set of runtime settings.

### UI Controls
- Settings button toggles dropdown.
- Source selection buttons: **Release**, **Branch**, **Local**.
- Release version dropdown with install status + cancel.
- Branch search dropdown (typeahead).
- Local path input + browse button + validation status.
- Parallel builds setting: auto vs custom numeric.
- Developer mode toggle.

### Data Needed
- `atopile` state:
  - `source` (`release|branch|local`)
  - `currentVersion`
  - `availableVersions[]`
  - `branch` + `availableBranches[]`
  - `localPath`
  - `detectedInstallations[]` (path, source, version)
  - `isInstalling`, `installProgress`, `error`
- Max concurrent builds setting: default value, whether custom is used, custom value.

### Actions
- `getMaxConcurrentSetting` → returns `{use_default, custom_value?, default_value}`.
- `setMaxConcurrentSetting {useDefault, customValue}`
- `setDeveloperMode {enabled}`
- `setAtopileSource {source}`
- `setAtopileVersion {version}`
- `setAtopileBranch {branch}` (UI currently sends `setAtopieBranch`; keep compatibility or fix UI)
- `setAtopileLocalPath {path}`
- `browseAtopilePath` (open file picker)
- `validateAtopilePath {path}` → returns `{valid, version?, error?}`
- `setAtopileInstalling {installing:false}` (cancel)

## Projects Panel (Active Project + Targets + Build Queue)

### Intent
Select a project, choose a target, manage build actions, and view build queue history.

### UI Controls
- Project selector (combobox + search).
- Create project button → opens form (name/license/description/parent directory).
- Target selector (dropdown).
- Create target button → opens form (name, entry).
- Project description inline edit.
- Build actions:
  - **Build** (selected target)
  - **Build All** (all targets)
  - **MFG Data** (same as build for target)
- Output actions:
  - **KiCad**, **3D**, **Layout** (open last build outputs)
- Build queue list with expand/collapse and **Cancel build** for queued/building items.

### Data Needed
- Projects list:
  - `root`, `name`, `description`, `targets[]`
  - Target: `name`, `entry`, `lastBuild` (status, warnings, errors, elapsedSeconds, stages)
- Active/queued builds:
  - `buildId`, `projectRoot`, `target`, `status`, `queuePosition`
  - `stages[]` (name, displayName, status, elapsedSeconds)
  - `startedAt`, `elapsedSeconds`
- `projectModules` for target creation form (entry suggestions).

### Actions
- `selectProject {projectRoot}`
- `setSelectedTargets {targetNames[]}`
- `build {projectRoot, targets[]}` (or `build {level, id, label}`)
- `cancelBuild {buildId}`
- `createProject {name, license, description, parentDirectory}`
- `createTarget {project_root, name, entry}`
- `updateProjectDescription {project_root, description}`
- `getBuildsByProject {projectRoot, target?, limit}` (used to open outputs)
- `openKiCad {projectId, buildId}`
- `open3D {projectId, buildId}`
- `openLayout {projectId, buildId}`

## Structure Panel (Module Tree)

### Intent
Show the module/interface/component structure for the active `.ato` file with search and expansion state.

### UI Controls
- Search input + clear.
- Expand/collapse tree nodes.

### Data Needed
- `activeEditorFile`, `lastAtoFile`.
- `projects[]` (for workspace root resolution).
- `projectModules[projectRoot]` (to resolve entries + fallback).
- Module tree response for a file:
  - `modules[]` each with `name`, `entry`, `children[]` or a flat `{children, moduleName, entry}`.

### Actions
- `fetchModules {projectRoot}` (preload module list)
- `fetchFiles {projectRoot}` (optional if file tree needed)
- `getModuleChildrenForFile {projectRoot, filePath, maxDepth}` → returns `modules[]` or `{children, moduleName, entry}`.

## Packages Panel (Marketplace + Installed)

### Intent
Browse packages and installed project dependencies; open a package detail drawer.

### UI Controls
- Search input.
- Installed section expand/collapse.
- Click any package/dependency to open detail.

### Data Needed
- Marketplace packages list:
  - `identifier`, `name`, `summary`, `description`, `publisher`
  - `version`, `latestVersion`, `installedIn[]`
  - `homepage`, `repository`, `downloads`, `license`, `keywords`
- Project dependencies for selected project:
  - `identifier`, `name`, `version`, `summary`, `publisher`, `homepage`, `repository`
- `installError` (if install failed)

### Actions
- `getPackageDetails {packageId}` (open detail drawer)
- `installPackage {packageId, projectRoot, version?}` (from detail panel)
- `fetchDependencies {projectRoot}`

## Package Detail Panel (Drawer)

### Intent
Show package metadata + usage snippet and let users install/update a version.

### UI Controls
- Close.
- Version dropdown.
- Install/Update button.

### Data Needed
- `packageDetails`:
  - `version`, `installed`, `installedVersion`
  - `description`, `summary`, `usageContent`
  - `versions[]` (version, releasedAt, requiresAtopile?, size?)
- `isInstalling`, `installError`, `error`.

### Actions
- `installPackage {packageId, projectRoot, version?}`
- `clearPackageDetails` (optional, to close)

## Problems Panel

### Intent
Show build problems grouped by file, filter by text, and open files at problem locations.

### UI Controls
- Search input + clear.
- Expand/collapse file groups.
- Click problem → open file at line/column.

### Data Needed
- `problems[]` with:
  - `id`, `level` (`error|warning`), `message`
  - `file`, `line`, `column`
  - `stage`, `logger`, `buildName`, `projectName`, `timestamp`
  - `ato_traceback` (for developer mode)

### Actions
- `openFile {file, line?, column?}`
- `refreshProblems` (initial load / manual refresh)

## Standard Library Panel

### Intent
Browse stdlib items with nested children and usage snippets.

### UI Controls
- Search input.
- Expand/collapse item details.
- Expand/collapse child nodes.
- Copy usage snippet.

### Data Needed
- `stdlibItems[]`:
  - `id`, `name`, `type` (`interface|module|component|trait|parameter`)
  - `description`, `usage`
  - `children[]` (name, type, itemType, children, enumValues)

### Actions
- `refreshStdlib`

## Variables Panel

### Intent
Inspect computed vs actual parameter values and show pass/fail status.

### UI Controls
- Search input.
- Source filter (user/computed/picked/all).
- Expand/collapse tree nodes.
- Click a row to copy variable info.

### Data Needed
- `variablesData`:
  - `build_id`, `version`, `nodes[]`
  - Node: `name`, `type` (`module|interface|component`), `path`, `typeName`, `variables[]`, `children[]`
  - Variable: `name`, `spec`, `specTolerance`, `actual`, `actualTolerance`, `unit`, `type`, `meetsSpec`, `source`
- `isLoadingVariables`, `variablesError`.

### Actions
- `fetchVariables {projectRoot, target, requestId}`

## BOM Panel

### Intent
Show BOM components, costs, stock, parameters, and usages; allow quick jump to source.

### UI Controls
- Search input.
- Expand/collapse rows.
- Copy fields (MPN/LCSC/etc).
- Click usage → open source file at line.
- Inline LCSC data fetch indicator.

### Data Needed
- `bomData`:
  - `components[]` with:
    - `id`, `type`, `value`, `package`, `manufacturer`, `mpn`, `lcsc`
    - `quantity`, `unitCost`, `stock`, `parameters[]`, `source`
    - `usages[]` (address, designator, line?)
- Latest build metadata for target:
  - `build_id`, `started_at`, `completed_at`, `duration` (used to decide LCSC refresh).
- LCSC lookup results:
  - `parts[lcscId]` with `unit_cost`, `stock`, `description`, `manufacturer`, `mpn`.

### Actions
- `refreshBOM {projectRoot, target, requestId}`
- `getBuildsByProject {projectRoot, target?, limit}`
- `fetchLcscParts {lcscIds[], projectRoot?, target?}`
- `openFile {file, line?}` (from usage clicks)

## Cross-Panel Events / Refreshes

- Initial load triggers:
  - `refreshProblems`, `refreshPackages`, `refreshStdlib`
- Selection changes trigger:
  - `refreshBOM`, `fetchVariables`, `fetchDependencies`
- Panels expect eventual consistency; if requests fail, panel shows an error or empty state.

## Event-Bus Reconciliation (Stage/0.14 Model)

Stage/0.14 emits **targeted events** and expects the UI to refetch only the affected slice.
This table maps each UI slice to event(s) and the preferred fetch endpoint/action.

| UI Slice | Stage Event(s) | Fetch / Action | Notes |
| --- | --- | --- | --- |
| Projects list | `projects_changed` | `GET /api/projects` | Refresh list of projects/targets. |
| Builds (active/queue/history) | `builds_changed` | `GET /api/builds/active`, `/api/builds/queue`, `/api/builds/history` | UI may combine into queue + recent history. |
| Problems | `problems_changed` | `GET /api/problems?project_root=...&build_name=...` | Filtered by project/target if needed. |
| Packages (marketplace) | `packages_changed` | `GET /api/packages` (or `/api/packages/summary`) | Project deps are separate. |
| Project dependencies | `project_dependencies_changed` | `GET /api/dependencies?project_root=...` | Trigger on project selection + dependency change. |
| Stdlib | `stdlib_changed` | `GET /api/stdlib` | Used for Standard Library panel. |
| BOM | `bom_changed` | `GET /api/bom?project_root=...&target=...` or `GET /api/build/{buildId}/bom` | UI currently looks up last build ID before fetch. |
| Variables | `variables_changed` | `GET /api/variables?project_root=...&target=...` or `GET /api/build/{buildId}/variables` | Similar to BOM. |
| Project files | `project_files_changed` | `GET /api/files?project_root=...` | Used by Structure/Explorer. |
| Project modules | `project_modules_changed` | `GET /api/modules?project_root=...` + `/api/module/children?...` | Structure panel uses `module/children`. |
| Atopile config | `atopile_config_changed` | `GET /api/...` or `action_result` | Stage should emit event when install/version changes. |
| Open outputs | `open_layout`, `open_kicad`, `open_3d` | event → host/extension | One-shot commands to VS Code. |

### Notes on WebSocket Actions

- In stage model, WebSocket actions should return **action_result** and then emit a **targeted event** if data changed.
- The UI should treat action responses as acknowledgements and refetch via the event trigger.

## Implementation Plan (Engineer Hand‑Off)

1. **Confirm Contracts**
   - Agree on the event list and payloads (use the reconciliation table).
   - Agree on HTTP endpoints or action responses for each data slice.
   - Decide where request correlation lives (e.g., `requestId` in action payload).

2. **Define Data Models**
   - Document JSON shapes for:
     - Projects/targets
     - Builds (active/queue/history + stages)
     - Problems
     - Stdlib items
     - BOM components + LCSC data
     - Variables tree
     - Packages + dependencies + package details

3. **Implement API Surface**
   - Create or update endpoints to satisfy each panel’s needs:
     - `/api/projects`, `/api/builds/*`, `/api/problems`, `/api/stdlib`, `/api/bom`, `/api/variables`, `/api/dependencies`, `/api/modules`, `/api/files`, `/api/packages`, `/api/parts/lcsc`.
   - Ensure endpoints are idempotent and return stable shapes.

4. **Wire Event‑Bus Emissions**
   - Emit targeted events after any action that changes data:
     - Build start/finish → `builds_changed`, `problems_changed`, `bom_changed`, `variables_changed`.
     - Package install/remove → `packages_changed`, `project_dependencies_changed`.
     - Project edits → `projects_changed`, `project_modules_changed`.
     - Stdlib refresh → `stdlib_changed`.
   - Keep event payloads minimal; rely on refetch.

5. **Front‑End Refresh Strategy**
   - On each event, call the corresponding fetch endpoint.
   - On selection changes, trigger BOM/Variables/Dependencies fetch directly.
   - Keep UI store as frontend‑owned state; no full state push from backend.

6. **Smoke + Regression Tests**
   - Manual smoke: project selection, build, open outputs, problems, BOM/Variables, package install.
   - Add/adjust tests for API contracts and event emission counts if desired.

## Branch Setup + File Migration Notes

### Proposed Branch Flow
1. Create a new branch off `origin/stage/0.14.x`.
2. Cherry‑pick the **sidebar UI files** from the current branch (UI only).
3. Adapt the UI’s WebSocket and store to the **event‑bus + refetch** model.
4. Implement backend endpoints/events per this spec.

### UI Files to Copy (Sidebar Scope)

**Core sidebar UI (required):**
- `src/ui-server/src/components/Sidebar.tsx`
- `src/ui-server/src/components/ActiveProjectPanel.tsx`
- `src/ui-server/src/components/StructurePanel.tsx`
- `src/ui-server/src/components/PackagesPanel.tsx`
- `src/ui-server/src/components/ProblemsPanel.tsx`
- `src/ui-server/src/components/StandardLibraryPanel.tsx`
- `src/ui-server/src/components/VariablesPanel.tsx`
- `src/ui-server/src/components/BOMPanel.tsx`
- `src/ui-server/src/components/PackageDetailPanel.tsx`
- `src/ui-server/src/components/CollapsibleSection.tsx`
- `src/ui-server/src/components/sidebar-modules/*`
- `src/ui-server/src/components/ModuleTreeNode.tsx` (StructurePanel dependency)
- `src/ui-server/src/components/shared/*` (CopyableCodeBlock, badges)
- `src/ui-server/src/hooks/usePanelSizing.ts`
- `src/ui-server/src/styles/_explorer.css`
- `src/ui-server/src/styles/_utilities.css`
- `src/ui-server/src/components/*.css` (related to the above panels)

**Supporting UI (optional, only if keeping other pages/features):**
- `src/ui-server/src/components/ProjectsPanel.tsx`
- `src/ui-server/src/components/ProjectCard.tsx`
- `src/ui-server/src/components/ProjectExplorerCard.tsx`
- `src/ui-server/src/components/DependencyCard.tsx`
- `src/ui-server/src/components/BuildsCard.tsx`
- `src/ui-server/src/components/BuildItem.tsx`
- `src/ui-server/src/components/BuildNode.tsx`
- `src/ui-server/src/components/BuildTargetItem.tsx`

**Needs structural updates (event‑bus alignment):**
- `src/ui-server/src/api/websocket.ts`  
  - Replace full‑state handling with event handling; keep `action_result`.
- `src/ui-server/src/store/index.ts`  
  - Remove `replaceState` full‑state pathway; keep per‑slice setters and loading/error states.
- `src/ui-server/src/hooks/useConnection.ts`  
  - Reconnect logic can stay, but should subscribe to event‑bus messages (no AppState replacement).
- `src/ui-server/src/components/sidebar-modules/useSidebarEffects.ts`  
  - Swap “action‑driven state push” for event‑triggered refetch.
- `src/ui-server/src/components/sidebar-modules/useSidebarHandlers.ts`  
  - Ensure actions return `action_result` and refetch on event instead of implicit state push.
- `src/ui-server/src/components/BOMPanel.tsx` / `StructurePanel.tsx`  
  - Currently use `sendActionWithResponse`; consider switching to `api.client` or explicit actions + refetch.
- `src/ui-server/src/types/build.ts` / `src/ui-server/src/types/generated.ts`  
  - Ensure types match new backend response shapes (no AppState push).

**Optional / Evaluate:**
- `src/ui-server/src/api/client.ts`  
  - Prefer this for refetch endpoints under the event‑bus model.
- `src/ui-server/src/api/vscodeApi.ts`  
  - Verify host messaging still aligns (open file/layout, connection status).
