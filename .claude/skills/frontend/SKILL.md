---
name: frontend
description: "Frontend standard for atopile: FastAPI + Vite + React, WebSocket-first transport, schema-driven contracts, and browser-first validation."
---

# Frontend Skill

This skill defines how to build frontend features in atopile at a consistently high bar for:

1. Frontend code quality
2. Design quality
3. Architecture quality

Primary reference implementations:
- `src/ui-server`
- `src/atopile/visualizer/web`

## Quick Start

Core frontend loop:

```bash
cd src/ui-server
npm run test
npm run build
```

Graph/worker-heavy UI loop:

```bash
cd src/atopile/visualizer/web
npm run build
```

Extension compile/install loop:

```bash
ato dev compile && ato dev install cursor
# or
ato dev compile && ato dev install vscode
```

Notes:
- `ato dev compile` default target is `all` (includes type generation + extension packaging).
- `ato dev install <cursor|vscode>` installs latest local `.vsix` with `--force`.

## Basic Frontend Repo Structure

Use this as the quick orientation map:

- `src/ui-server/`:
  main React webview app used in extension UI surfaces (sidebar/log viewer/migrate/test explorer).
- `src/vscode-atopile/`:
  VS Code/Cursor extension host layer (commands, webview wiring, IDE integration).
- `src/atopile/visualizer/web/`:
  standalone graph visualizer React app (3D rendering + graph interaction).
- `src/atopile/layout_server/frontend/`:
  specialized layout editor frontend for the layout server.

## Repository Surface Map (Where Things Live)

This section is intentionally explicit so agents know where to build, reuse, or extend.

### `ui-server` (primary product UI)

Root:
- `src/ui-server/src/`

Main structure:
- `components/` feature and panel components
- `components/shared/` reusable UI primitives for multiple panels
- `components/sidebar-modules/` sidebar composition and behavior modules
- `api/` HTTP + WebSocket transport clients
- `store/` Zustand app state
- `hooks/` feature/domain hooks
- `utils/` shared pure helpers
- `styles/` token and module CSS
- `types/` generated and hand-authored contracts

Shared components (reuse before creating new):
- `src/ui-server/src/components/shared/CopyableCodeBlock.tsx`
- `src/ui-server/src/components/shared/EmptyState.tsx`
- `src/ui-server/src/components/shared/MetadataBar.tsx`
- `src/ui-server/src/components/shared/PanelSearchBox.tsx`
- `src/ui-server/src/components/shared/PublisherBadge.tsx`
- `src/ui-server/src/components/shared/TreeRowHeader.tsx`
- `src/ui-server/src/components/shared/VersionSelector.tsx`

Shared utilities:
- `src/ui-server/src/utils/codeHighlight.tsx` (ATO highlighting/presentation helpers)
- `src/ui-server/src/utils/nameValidation.ts` (name validity rules)
- `src/ui-server/src/utils/packageUtils.ts` (package formatting/comparison helpers)
- `src/ui-server/src/utils/searchUtils.ts` (search matching/filter helpers)

### `visualizer/web` (graph visualization app)

Root:
- `src/atopile/visualizer/web/src/`

Main structure:
- `components/` UI shell/controls
- `components/Sidebar/` graph-specific sidebar panels
- `three/` 3D rendering layer
- `stores/` state slices for graph/view/filter/navigation
- `lib/` pure graph/filter/layout/export logic
- `workers/` background compute (layout)
- `types/` graph contracts

Core UI components:
- `src/atopile/visualizer/web/src/components/AtopileLogo.tsx`
- `src/atopile/visualizer/web/src/components/Breadcrumbs.tsx`
- `src/atopile/visualizer/web/src/components/ExportMenu.tsx`
- `src/atopile/visualizer/web/src/components/Minimap.tsx`
- `src/atopile/visualizer/web/src/components/Tooltip.tsx`
- `src/atopile/visualizer/web/src/components/Toolbar.tsx`
- `src/atopile/visualizer/web/src/components/Sidebar/FilterPanel.tsx`
- `src/atopile/visualizer/web/src/components/Sidebar/CollapsePanel.tsx`

Key utility area:
- `src/atopile/visualizer/web/src/lib/exportUtils.ts` (PNG/SVG/JSON export helpers)

### `vscode-atopile` (extension host side)

Root:
- `src/vscode-atopile/src/`

Use for:
- extension host integration and webview wiring
- command registration and IDE bridge behaviors

Avoid using this module for:
- core UI logic that belongs in React/webview app layers

### `layout_server/frontend` (specialized layout editor UI)

Root:
- `src/atopile/layout_server/frontend/src/`

Use for:
- focused canvas/layout-editor frontend concerns

Do not copy as default architecture for new product webviews:
- it has a different UI model and constraints than the main React webview apps

### Reuse Decision Rules

When adding a new feature:
1. First check `components/shared/` for an existing primitive.
2. If similar logic exists in `utils/`, extend it instead of duplicating.
3. If feature is graph-specific, prefer patterns from `visualizer/web/src/lib` + `stores`.
4. If behavior is IDE-host specific, keep it in `vscode-atopile` bridge modules.
5. If a new primitive is needed, place it where cross-feature reuse is likely.

## Non-Negotiable Rules

1. One canonical user flow
- Design and implement one primary happy-path per feature.
- Do not introduce alternate fallback UX branches.
- If a dependency is unavailable, fail clearly and stop; do not fork into a second workflow.

2. Schema-first contracts
- Backend contracts are Pydantic models.
- Frontend types are generated from backend schema.
- Avoid stringly-typed protocols and hand-maintained duplicate interfaces where generated types exist.

3. WebSocket-first interaction model
- Use WebSocket for interactive state sync, actions, and events.
- Use HTTP for bootstrap/read/download flows where request-response is natural.

4. Clear module boundaries
- `api/` handles transport and protocol mapping.
- `store/` handles app state and actions.
- `components/` handles rendering and interaction composition.
- `utils/` or `lib/` handles pure transforms/business helpers.

5. Browser-first self testing
- Agent validates behavior in browser webview dev flow first.
- Ask user to test in extension host only after browser flow is verified.

## Architecture Standard: FastAPI + Vite + React

### System Topology

1. FastAPI backend
- Owns domain logic, persistence, job orchestration, and event emission.
- Exposes HTTP APIs and WebSocket endpoints.

2. React app on Vite
- Owns UI rendering, local interactions, and client-side state orchestration.
- Uses typed API/WS clients under `api/`.

3. Integration boundary
- Typed payload contracts at API and WS boundaries.
- No ad-hoc payload parsing scattered across components.

### Required Request/State Flow

1. User action in component
2. Component dispatches handler/store action
3. Handler calls `api/` transport
4. Transport maps payload to typed domain shape
5. Store updates through explicit action
6. UI rerenders from selectors

### Transport Standard: WebSocket-First

Use WebSocket for:
- state synchronization
- action dispatch/result events
- long-running workflow progress

Use HTTP for:
- initial bootstrap reads
- idempotent direct queries
- file or artifact retrieval

Required WS client behavior:
- reconnect with bounded backoff
- explicit connection status in store
- pending request timeout/cancellation
- post-reconnect resync
- out-of-order tolerance in reducers

Example WS envelope:

```ts
type WsMessage =
  | { type: "state"; data: AppState }
  | { type: "event"; event: EventType; data: EventPayload }
  | {
      type: "action_result";
      action: string;
      requestId?: string;
      result: { success: boolean; error?: string };
    };
```

### Contract Standard: Pydantic -> Generated TypeScript

Required workflow:
1. Update backend Pydantic model
2. Regenerate schema/types
3. Fix frontend compile errors using generated contracts
4. Add/update tests for contract behavior changes

Never prefer this:
- handwritten duplicate interfaces when generated types are available
- raw string action/event typing where enums/literal types exist

## Code Quality Standard

A feature is high quality when:
- strict TS typing is preserved
- state transitions are explicit and testable
- errors/loading/empty states are implemented
- side effects are isolated in transport/hooks

### Preferred Patterns

1. Typed API boundary

```ts
export async function fetchBuilds(projectRoot: string): Promise<BuildSummary[]> {
  const res = await fetch(`/api/builds?project_root=${encodeURIComponent(projectRoot)}`);
  if (!res.ok) throw new APIError(res.status, "Failed to fetch builds");
  const data = (await res.json()) as { builds: BuildSummary[] };
  return data.builds;
}
```

2. Typed store action with explicit state transitions

```ts
const useBuildStore = create<BuildState>((set) => ({
  items: [],
  loading: false,
  error: null,
  refresh: async (projectRoot) => {
    set({ loading: true, error: null });
    try {
      const items = await fetchBuilds(projectRoot);
      set({ items, loading: false });
    } catch (err) {
      set({ loading: false, error: err instanceof Error ? err.message : "Unknown error" });
    }
  },
}));
```

3. Component-store separation
- Components call actions/selectors; they do not implement protocol logic.

### Anti-Patterns

- “God” components/providers mixing UI + transport + domain + file ops
- full-store subscriptions where selectors are sufficient
- implicit defaults not represented in types

## Unified Product Style Guide

Apply these rules across all surfaces (sidebar, panels, overlays, inspectors, dialogs).

1. Host-native + brand-balanced
- Respect host theme and typography variables.
- Express brand with targeted accents, not full-theme overrides.

2. Hierarchy first
- Maintain consistent spacing, row heights, and typography scale.
- Use badges/counts only when they add decision value.

3. Complete interaction states
- Every control defines default/hover/focus-visible/active/disabled/loading.

4. Tokenized styling
- Use shared tokens for color, spacing, radius, typography, z-index.
- Avoid one-off feature-local hardcoded semantic colors.

5. Single-flow UX
- Interface should guide users through one canonical sequence.
- Do not add alternate fallback routes; surface clear stop-state errors instead.

Example tokenized control:

```css
.btn-primary {
  background: var(--color-brand-500);
  color: var(--color-text-on-brand, #fff);
  border: 1px solid var(--color-brand-500);
  border-radius: var(--radius-md);
  padding: var(--space-sm) var(--space-md);
}
.btn-primary:hover { background: var(--color-brand-600); }
.btn-primary:focus-visible { outline: 2px solid var(--color-info); outline-offset: 2px; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
```

## Testing Standard

### Minimum Test Matrix Per Feature

1. Store/action test
2. API/transport test
3. UI interaction test
4. Error/loading/empty-state test

Example matrix (build queue):
- store: `enqueueBuild` / `completeBuild`
- API: build start error -> `APIError`
- UI: cancel click -> `sendAction('cancelBuild', { buildId })`
- state: disconnected WS shows status banner

### Browser-First Dev Viewer Flow (Required)

Agents should self-test in browser webview flow first:

```bash
cd src/ui-server
npm run dev:all
```

Then:
1. Run interaction checks in browser
2. Run screenshot checks
3. Inspect UI logs
4. Fix issues
5. Ask user to test in extension host only after above passes

### UI Automation: Puppeteer + Vite Screenshot APIs

These are correct tools in this repo:
- Puppeteer is already a dependency
- Vite dev server exposes screenshot and UI-log endpoints

Useful calls:

```bash
curl -sS -X POST http://127.0.0.1:5173/api/screenshot \
  -H 'Content-Type: application/json' \
  -d '{"path":"/","name":"default","waitMs":1200}'
```

```bash
curl -sS -X POST http://127.0.0.1:5173/api/screenshot \
  -H 'Content-Type: application/json' \
  -d '{
    "path":"/",
    "name":"projects-expanded",
    "uiActions":[{"type":"openSection","sectionId":"projects"}],
    "uiActionWaitMs":600
  }'
```

```bash
curl -sS http://127.0.0.1:5173/api/ui-logs
```

Automation guardrails:
- stable selectors (`data-testid` or semantic role)
- fixed viewport for visual comparisons
- readiness-based waits preferred over arbitrary sleeps
- runtime errors treated as failures unless explicitly allowlisted

### Webview Pages to Validate in Browser Flow

For `ui-server`, verify the relevant page for your change:
- `http://127.0.0.1:5173/` (main sidebar shell)
- `http://127.0.0.1:5173/log-viewer.html`
- `http://127.0.0.1:5173/migrate.html`
- `http://127.0.0.1:5173/test-explorer.html`

If your feature affects one of these views, include at least one screenshot and one interaction check on that page.

### Browser-First Promotion Gate (Before Asking User)

All must be true:
- UI interactions behave correctly in browser flow
- screenshot captures are stable for key states
- `api/ui-logs` contains no unapproved runtime errors
- relevant test matrix items are passing

Only then ask the user to validate in the extension host.

## Accessibility Baseline

Required:
- keyboard-operable primary controls
- deterministic focus order
- semantic roles/ARIA where native semantics are insufficient
- focus-visible styles via tokens
- readable contrast in light/dark modes

Example:

```tsx
<button aria-expanded={!collapsed} aria-controls={`section-${id}`} onClick={toggle}>
  {title}
</button>
<div id={`section-${id}`} role="region">
  {children}
</div>
```

## Performance Baseline

Required:
- memoize expensive derived data and callback props in hot paths
- use `requestAnimationFrame` for resize/drag animation loops
- move heavy graph/layout/geometry work to Web Workers
- avoid broad store subscriptions

Practical budgets (set per feature):
- input-to-paint latency target
- rerender count target for key interactions
- max main-thread compute before worker offload

## Implementation Playbooks (Use These by Default)

Use these as concrete build patterns when starting a new feature.

### Playbook A: New Sidebar/Panel Feature (`ui-server`)

1. Contract
- Add/extend backend Pydantic models for panel data and actions.
- Regenerate frontend schema/types.

2. Transport
- Add one module in `src/ui-server/src/api/` for panel actions/data.
- Keep HTTP calls and WS events in this module only.

3. State
- Add state fields and explicit actions in `src/ui-server/src/store/index.ts` (or a split slice if introduced).
- Add selectors for component consumption; avoid exposing raw complex objects to UI.

4. UI
- Reuse `components/shared/` primitives before adding new ones.
- Keep panel container logic in feature module; keep leaf controls presentational.

5. Styling
- Use existing tokens from `styles/_variables.css`.
- Add module styles only if existing style modules cannot express the feature.

6. Validation
- Browser flow via `npm run dev:all`.
- Capture at least one screenshot per critical panel state.
- Ensure no unapproved `ui-logs` errors.

### Playbook B: New Graph/Visualizer Capability (`visualizer/web`)

1. Data model
- Add/update graph types in `src/atopile/visualizer/web/src/types/`.

2. Core logic
- Implement filters/transforms/layout math in `src/atopile/visualizer/web/src/lib/`.
- Keep these functions pure and unit-testable.

3. State integration
- Add state to the appropriate store under `stores/` (graph, filter, view, navigation, selection).
- Expose small selectors to UI components.

4. Rendering
- Keep scene primitives in `three/`.
- Memoize expensive geometry/material/data transforms.

5. Performance
- Offload heavy iterative work to `workers/`.
- Ensure UI input remains responsive during layout recompute.

### Playbook C: New Long-Running Workflow (Build/Migrate/Export)

1. Canonical sequence
- Define one linear flow: trigger -> progress -> completion/error.
- Do not introduce alternate fallback branch UX.

2. Event protocol
- Emit typed events/states for progress updates and completion.
- Include correlation IDs for action-result mapping where applicable.

3. UI behavior
- Show explicit phase state with clear progress messaging.
- Disable conflicting controls during active execution.

4. Completion handling
- On success: update canonical state and surface result artifact/action.
- On failure: surface actionable error in same flow context.

### Playbook D: Shared Primitive Extraction

Promote to shared when at least one is true:
- used by 2+ feature areas
- same interaction/state semantics repeated
- design consistency risk if duplicated

Extraction steps:
1. move primitive to `components/shared/`
2. keep API minimal and typed
3. colocate small style module if needed
4. update existing call sites
5. add or update focused component test

## Contract and Protocol Conventions

### Naming Conventions

Backend (Pydantic):
- `FeatureActionRequest`
- `FeatureActionResult`
- `FeatureState`
- `FeatureEvent`

Frontend (generated/usage):
- keep generated names when possible
- avoid local aliases that hide meaning
- use explicit event unions for WS handlers

### Message Shape Conventions

Prefer:
- stable top-level discriminator (`type`)
- typed payload object (`data` or `result`)
- optional correlation (`requestId`)
- no polymorphic anonymous payloads

Avoid:
- overloading one field with multiple payload types
- encoded “status” strings that duplicate `type`
- implicit null/undefined semantics for required states

### Versioning and Migration

For incompatible contract changes:
1. update Pydantic schema
2. regenerate TS
3. update backend emitters and frontend consumers in same change
4. add regression tests for old/new boundary expectations (if needed)
5. keep PR notes explicit about contract impact

## Detailed Testing Notes

### What to Validate for WS Features

At minimum:
- initial connect success path
- disconnect transition visible in UI state
- reconnect/backoff path
- resync on reconnect
- pending request timeout cleanup

Recommended:
- late event arrival handling
- duplicate event idempotency (if protocol can replay)
- malformed message guard behavior (drop + log)

### UI Automation Scenario Set

For each major feature, automate at least these scenarios:

1. Initial render
- page loads and primary container appears
- no runtime error in `ui-logs`

2. Primary action path
- perform canonical user action
- assert expected UI state transition

3. Progress/working state
- verify loading/progress visual state while in-flight

4. Completion path
- verify final expected state and visible confirmation/result

5. Error path (same flow)
- force backend/action failure
- verify error rendering in same UI context (no flow fork)

6. Reload/reconnect stability
- simulate websocket drop/reconnect
- verify canonical state recovers correctly

### Screenshot Strategy

Use screenshot captures as regression anchors for:
- baseline/default view
- active/selected state
- loading/progress state
- error state
- completed/ready state

Keep captures stable by:
- fixed viewport
- deterministic setup actions
- waiting for specific DOM/state conditions
- avoiding transient animation frames when asserting image diffs

### Test Naming and Placement

Recommended naming:
- `FeatureName.store.test.ts`
- `FeatureName.api.test.ts`
- `FeatureName.test.tsx` (interaction rendering)

Placement:
- close to feature module for local reasoning
- keep global test setup centralized in `__tests__/setup.ts`

## Review and Quality Heuristics

### Code Review Focus Order

1. Contract correctness
- Are types/schema and runtime behavior aligned?

2. Flow correctness
- Does UI implement one canonical sequence without fallback branches?

3. State correctness
- Are transitions explicit and recoverable for reconnect/reload?

4. UI quality
- Are interaction states and accessibility complete?

5. Maintainability
- Is feature organized per module boundaries and reuse rules?

### Red Flags (Block Merge)

- ad-hoc payload typings where generated types already exist
- untyped WS parsing directly in components
- duplicate shared primitives with near-identical behavior
- fallback branch introduced for a core user path
- browser-first validation skipped before asking extension testing

## Definition of Done

A feature is done only when all are true:

- [ ] one canonical flow implemented (no fallback path forks)
- [ ] contract changes modeled in Pydantic and regenerated TS types consumed
- [ ] websocket behavior validated (connect/reconnect/resync)
- [ ] tests added/updated (store + API + UI + state handling)
- [ ] browser-first dev viewer checks complete
- [ ] extension-host validation requested only after browser flow is clean
- [ ] build/test commands pass for touched frontend app(s)
- [ ] component/util placement follows repository surface map and reuse rules

## PR Checklist (Copy/Paste)

```md
- [ ] Single canonical flow preserved (no fallback path added)
- [ ] Pydantic models updated for API/WS changes
- [ ] Generated TS schema/types regenerated and committed
- [ ] WS reconnect/resync behavior verified
- [ ] Browser dev viewer flow validated (`npm run dev:all`)
- [ ] Screenshots + UI logs reviewed (no unapproved runtime errors)
- [ ] Added/updated: store test, transport test, UI interaction test
- [ ] Asked user to test in extension host only after browser checks passed
```

## Golden Path Reference Implementation

For each major feature type, keep one small end-to-end reference showing:
- contract
- transport
- state
- UI
- tests

Minimal outline:
1. Add Pydantic request/result models
2. Regenerate TS contracts and import generated types in `api/`
3. Implement typed WS/API action path
4. Update store pending/success/error transitions
5. Wire UI control to store action
6. Add tests for transitions + transport + interaction
