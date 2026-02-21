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
