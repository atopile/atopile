---
name: frontend
description: "How to build frontend features in atopile at a 10/10 bar for code quality, design, and architecture using proven repo patterns."
---

# Frontend Skill

This skill defines the standard for building frontend features in atopile.
It is optimized for:

1. High code quality (correct, maintainable, testable)
2. High design quality (clear, cohesive, production-ready UI)
3. High architecture quality (clear boundaries, low coupling, scalable structure)

Primary reference implementations:
- `src/ui-server` (best overall product frontend baseline)
- `src/atopile/visualizer/web` (best focused architecture for compute-heavy UI)

## Quick Start

For new frontend feature work in `ui-server`:

```bash
cd src/ui-server
npm run test
npm run build
```

For graph/worker-heavy feature work:

```bash
cd src/atopile/visualizer/web
npm run build
```

## Architecture Standard: FastAPI + Vite + React

Use this as the default architecture for new atopile frontend product features.

### System Topology

1. Backend: FastAPI domain/API server
- Owns business logic, persistence, long-running jobs, and event generation.
- Exposes HTTP endpoints for request/response workflows.
- Exposes WebSocket endpoints for realtime state and event updates.

2. Frontend: React app bundled by Vite
- Owns presentation, local interaction logic, and client-side state.
- Calls backend through typed API client modules (`api/`).
- Receives realtime updates through dedicated websocket client modules.

3. Integration boundary
- Transport contract is explicit: typed payloads for REST and WS messages.
- UI does not parse ad-hoc backend payloads directly inside components.

### Request/State Flow (Required)

1. User action in React component
2. Component dispatches typed store action or calls feature handler
3. Handler calls API/WS transport module
4. Transport normalizes payload to typed domain shape
5. Store updates through explicit action
6. UI re-renders via selectors only

### Contract Standard: Pydantic -> Generated TypeScript

This is the default and preferred pattern for atopile frontend/backend integration.

1. Backend contracts
- Define request/response/event contracts as Pydantic models.
- Keep schema as source of truth for field names and types.

2. Frontend contracts
- Generate TypeScript types/API bindings from backend schema.
- Import generated types in `api/`, `store/`, and feature handlers.

3. Protocol discipline
- Avoid ad-hoc stringly-typed payloads and free-form `Record<string, unknown>` when a typed contract exists.
- Prefer generated enums/literal unions for message/action/event kinds.

4. Change workflow
- Modify Pydantic model first.
- Regenerate TS types/API.
- Update frontend usage with compile-time type checks.

### Transport Standard: WebSocket-First

atopile frontend architecture is WebSocket-first.

1. Primary transport
- Use WebSocket for state synchronization, action dispatch, event streams, and long-running workflow updates.
- Keep a single typed message protocol for events/action results where possible.

2. Secondary transport
- Use HTTP for initial fetch/bootstrap, idempotent reads, file/blob download, and endpoints that are naturally request/response.

3. Client behavior requirements
- Implement reconnect with bounded backoff.
- Handle offline/disconnected states explicitly in UI.
- Re-subscribe or re-initialize required state after reconnect.
- Treat out-of-order/late events as normal; design reducers/state updates to be resilient.

### Recommended Project Layout

```text
src/
  api/          # HTTP + WebSocket clients, protocol mapping
  components/   # Presentational + container components
  hooks/        # UI/feature hooks (side-effect aware)
  store/        # Global state, actions, selectors
  types/        # Shared contracts and generated types
  utils/        # Pure helper/domain transform functions
  styles/       # Tokens and style modules
```

### Non-Negotiable Architecture Rules

- Components do not own transport protocol details.
- Transport modules do not own rendering logic.
- Domain transforms are pure and testable.
- Realtime and request/response code paths are both resilient to failures/timeouts.
- Compute-heavy operations run in workers when they can block the UI thread.
- API/WS contracts must be schema-driven (Pydantic backend, generated TS frontend).
- Avoid raw string protocol switches when generated typed variants are available.
- Default to WebSocket transport for interactive product features; use HTTP selectively for bootstrap/read/download flows.

## Color + Style Guide (Production Baseline)

Use this guide for all new UI surfaces unless a subsystem has stricter host requirements.

### Design Principles

1. Token-first styling
- All colors/spacing/radius/typography come from shared tokens.
- No one-off hex colors in feature components.

2. Theme-aware defaults
- Every semantic token has dark and light behavior.
- Contrast must remain readable in both modes.

3. Semantic color usage
- Color is meaning, not decoration: success/warning/error/info/selection/accent.

### Core Color Roles

1. Brand
- `--color-brand-500`: primary brand action color
- `--color-brand-600`: hover/active brand state
- `--color-brand-subtle`: low-emphasis brand background

2. Neutrals (surface/text)
- `--color-bg-primary`
- `--color-bg-secondary`
- `--color-bg-tertiary`
- `--color-text-primary`
- `--color-text-secondary`
- `--color-text-muted`
- `--color-border`
- `--color-border-subtle`

3. Feedback
- `--color-success`, `--color-success-bg`
- `--color-warning`, `--color-warning-bg`
- `--color-error`, `--color-error-bg`
- `--color-info`, `--color-info-bg`

### Typography Scale

- `--font-size-xxs`: metadata chips, dense status labels
- `--font-size-xs`: compact helper text
- `--font-size-sm`: control labels, section subheaders
- `--font-size-md`: default body/control text
- `--font-size-lg`: panel titles

### Spacing and Shape

- `--space-xs`, `--space-sm`, `--space-md`, `--space-lg`, `--space-xl`
- `--radius-sm`, `--radius-md`, `--radius-lg`
- Keep density consistent in a panel; do not mix unrelated spacing scales.

### Component State Contract

Every interactive component must define:
- default
- hover
- focus-visible
- active/pressed
- disabled
- loading (if async)
- error (if user-correctable)

### Style Acceptance Gate

- [ ] No hardcoded feature-local colors for semantic UI states.
- [ ] Typography uses approved scale.
- [ ] Interactive states are complete.
- [ ] Light/dark mode validated.
- [ ] Spacing/radius consistent with tokens.

### Unified Product Style Guide (Generalized)

Apply these rules across all atopile frontend surfaces (not tied to one panel/view):

1. Host-native + brand-balanced UI
- Respect host environment tokens (fonts, colors, surface semantics).
- Keep brand expression focused in accents, not full-surface overrides.

2. Information hierarchy over decoration
- Keep row heights, typography, and spacing consistent.
- Use badges/counters/status indicators sparingly and meaningfully.
- Optimize for scanability in dense technical interfaces.

3. Explicit system-state communication
- Always expose key runtime states (connected, loading, installing, failed, ready).
- Every state should have a clear visual treatment and user-understandable message.

4. Consistent layout mechanics
- Reuse common patterns for collapsible sections, split panes, and resizable regions.
- Interaction behavior should be predictable across all modules.

5. Complete interaction-state language
- All interactive controls define default/hover/focus-visible/active/disabled/loading.
- Keyboard and focus behavior are first-class, not optional.

6. Tokenized scale and rhythm
- Use shared tokens for color, spacing, radius, typography, and layering.
- New components should compose existing tokens before introducing new ones.

7. Resilience-first UX
- Design for failure/recovery as a primary flow, not an exception.
- Error and disconnected states should include next-step actions.

## Specific Examples (Copyable Patterns)

Note: these examples are structural patterns. In real atopile features, prefer generated types from backend schema instead of hand-written duplicate interfaces.

### Example 1: Typed API boundary + store action

```ts
// api/builds.ts
export interface BuildSummary {
  id: string;
  status: "queued" | "building" | "success" | "failed";
}

export async function fetchBuilds(projectRoot: string): Promise<BuildSummary[]> {
  const res = await fetch(`/api/builds?project_root=${encodeURIComponent(projectRoot)}`);
  if (!res.ok) throw new Error(`Failed to fetch builds: HTTP ${res.status}`);
  const data = (await res.json()) as { builds: BuildSummary[] };
  return data.builds;
}
```

```ts
// store/builds.ts
import { create } from "zustand";
import { fetchBuilds, type BuildSummary } from "../api/builds";

interface BuildState {
  items: BuildSummary[];
  loading: boolean;
  error: string | null;
  refresh: (projectRoot: string) => Promise<void>;
}

export const useBuildStore = create<BuildState>((set) => ({
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

### Example 2: WebSocket event handling without UI coupling

```ts
// api/ws.ts
type EventMessage =
  | { type: "build_started"; buildId: string }
  | { type: "build_finished"; buildId: string; success: boolean };

export function connectBuildEvents(onEvent: (e: EventMessage) => void): WebSocket {
  const ws = new WebSocket("/ws/state");
  ws.onmessage = (evt) => onEvent(JSON.parse(evt.data) as EventMessage);
  return ws;
}
```

```ts
// hooks/useBuildEvents.ts
import { useEffect } from "react";
import { connectBuildEvents } from "../api/ws";
import { useBuildStore } from "../store/builds";

export function useBuildEvents() {
  const refresh = useBuildStore((s) => s.refresh);
  useEffect(() => {
    const ws = connectBuildEvents((event) => {
      if (event.type === "build_started" || event.type === "build_finished") {
        void refresh("current-project-root");
      }
    });
    return () => ws.close();
  }, [refresh]);
}
```

Recommended production extension for this pattern:
- reconnect/backoff strategy
- connection status in store
- post-reconnect resync action
- typed action-result correlation IDs

### Example 3: Tokenized button styles (no one-off colors)

```css
.btn-primary {
  background: var(--color-brand-500);
  color: var(--color-text-on-brand, #fff);
  border: 1px solid var(--color-brand-500);
  border-radius: var(--radius-md);
  padding: var(--space-sm) var(--space-md);
}

.btn-primary:hover { background: var(--color-brand-600); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary:focus-visible { outline: 2px solid var(--color-info); outline-offset: 2px; }
```

## Section 1: Frontend Code Quality (10/10)

### Quality Target

A feature is 10/10 when:
- Behavior is deterministic and type-safe under strict TypeScript.
- Logic is test-covered at the right level (unit + integration where needed).
- State transitions are explicit and observable.
- Error/loading/empty states are first-class.

### Required Patterns

1. Strong typing and strict TS
- Keep strict mode on.
- Avoid `any`; use narrowed unions and typed payloads.
- Define payload/data contracts in shared type modules.
- Prefer generated types from backend schema over hand-maintained duplicate interfaces.

2. Predictable state updates
- Use store slices/selectors to prevent accidental broad rerenders.
- Keep state mutations centralized in explicit actions.
- Separate view-local UI state from domain state.

3. Test strategy as part of implementation
- Add tests for new behaviors, not only snapshots.
- Cover: happy path, failure path, empty state, loading state.
- For stateful features, include at least one store/action-level test.

4. Runtime safety
- Handle reconnect/failure/timeout paths for websocket/API flows.
- Never leave silent failures; surface actionable user-facing errors.

### Golden Examples

- Store and typed action layering:
  - `src/ui-server/src/store/index.ts`
- Websocket lifecycle + reconnect handling:
  - `src/ui-server/src/api/websocket.ts`
- Focused typed store for graph workflows:
  - `src/atopile/visualizer/web/src/stores/graphStore.ts`
- Existing test baseline:
  - `src/ui-server/src/__tests__/store.test.ts`
  - `src/ui-server/src/__tests__/api-client.test.ts`

### Mistakes To Avoid

- Large "god component" consuming full app state object.
- UI behavior with no tests.
- Mixing transport concerns directly inside presentational components.
- Hidden implicit defaults that are not encoded in types.

### Frontend Code Quality Checklist

- [ ] Strict TS passes with no new `any`.
- [ ] New behavior includes tests.
- [ ] Loading/error/empty states are implemented.
- [ ] State updates happen through explicit actions/selectors.
- [ ] Side effects are isolated to hooks/services, not random components.
- [ ] API/WS payloads use generated types (or documented exception if generation unavailable).

## Section 2: Design Quality (10/10)

### Design Target

A feature is 10/10 when:
- It is visually consistent with atopile + VS Code environment.
- It has strong hierarchy, spacing rhythm, and readable interaction states.
- It works in both light/dark themes and different panel widths.
- Motion/feedback is purposeful and not noisy.

### Required Patterns

1. Token-driven styling
- Use CSS variables/tokens for spacing, color, radius, typography, z-index.
- Reuse existing style modules before creating new one-off CSS.

2. Theme-aware by default
- Respect VS Code theme variables.
- Verify contrast and readability in both light and dark modes.

3. Interaction states
- Define hover/active/selected/disabled/error/loading states for interactive controls.
- Keep feedback immediate and visible (buttons, status badges, toasts, inline states).

4. Responsive panel behavior
- Design for narrow sidebars first, then expanded layouts.
- Ensure truncation, wrapping, and icon-only fallbacks are intentional.

### Golden Examples

- Design tokens and theme plumbing:
  - `src/ui-server/src/styles/_variables.css`
  - `src/ui-server/src/styles/_base.css`
  - `src/ui-server/src/styles/index.css`
- Cohesive control bar with clear action groups:
  - `src/atopile/visualizer/web/src/components/Toolbar.tsx`

### Mistakes To Avoid

- Inline ad-hoc styles spread across HTML/TS without tokenization.
- Hardcoded colors that break in alternate themes.
- Missing disabled/loading states for actions.
- Visual density with no hierarchy (everything styled equally).

### Design Checklist

- [ ] Uses existing tokens or adds new tokens in shared variables.
- [ ] Verified in light + dark mode.
- [ ] Interactive states are complete.
- [ ] Works in narrow sidebar and larger panel widths.
- [ ] Visual hierarchy is obvious at first glance.

## Section 3: Architecture Quality (10/10)

### Architecture Target

A feature is 10/10 when:
- Boundaries are clear: view, state, transport, domain logic.
- Complexity is distributed across small composable modules.
- Heavy compute is offloaded from UI thread when needed.
- Integration points are explicit and easy to test/replace.

### Required Patterns

1. Clear layering
- `components/` for presentation/composition.
- `store/` or `stores/` for app state.
- `api/` for transport clients and protocol handling.
- `utils/lib/` for pure domain logic.

2. Controlled side-effect entry points
- Keep network/websocket/file interactions inside dedicated modules/hooks.
- Components trigger actions; they do not own protocol logic.

3. Complexity control
- Prefer many small modules over one giant orchestrator file.
- Use workers for expensive graph/layout/geometry operations.

4. Feature modularity
- Organize by feature areas (panel/module domains), not only by primitive type.
- Keep interfaces narrow and typed between feature boundaries.

### Golden Examples

- Feature modularization approach:
  - `src/ui-server/src/components/sidebar-modules/`
- API boundary separation:
  - `src/ui-server/src/api/`
- Worker-based compute offload:
  - `src/atopile/visualizer/web/src/workers/layoutWorker.ts`
  - `src/atopile/visualizer/web/src/stores/graphStore.ts`

### Mistakes To Avoid

- Overloaded provider/controller files that combine message routing, IO, and business logic.
- Feature logic trapped in giant top-level UI files.
- Imperative manual DOM composition for complex UI that should be declarative components.
- Cross-module hidden coupling via globals.

### Architecture Checklist

- [ ] Feature has explicit boundaries: view/state/api/domain.
- [ ] Side effects are centralized and testable.
- [ ] No new high-coupling "god file".
- [ ] Compute-heavy work moved off main thread where applicable.
- [ ] Module structure matches feature boundaries.

## 10/10 Feature Blueprint (Apply This For New Work)

Use this structure for new non-trivial frontend features:

1. Contract
- Define contract in backend Pydantic model first.
- Generate frontend TS types/API from schema.
- Use generated contracts in transport and state layers.

2. Domain logic
- Add pure helpers in `utils/` or `lib/`.
- Include unit tests for non-trivial transforms.

3. State slice
- Add store actions/selectors for feature state.
- Keep transient UI-only state local unless shared.

4. Transport
- Add API/websocket calls in `api/`.
- Normalize and map backend payloads once.
- Avoid free-form string protocol branching when typed event/action models exist.

5. UI composition
- Build small presentational components first.
- Compose in panel/container components.

6. Styling
- Extend shared tokens if needed.
- Implement complete interaction states.

7. Tests
- Add tests for store transitions and UI behavior.
- Include error/loading/empty scenarios.

8. Verification gate
- Build passes.
- Tests pass.
- Manual checks in light/dark + narrow/wide panel widths.

## Definition of Done (Must Pass)

A frontend feature is not done until all are true:

- [ ] Code quality checklist passes.
- [ ] Design checklist passes.
- [ ] Architecture checklist passes.
- [ ] Build succeeds for touched frontend app(s).
- [ ] Tests added/updated and passing for changed behavior.
- [ ] No major coupling or file-size hotspot introduced.
- [ ] Backend contract changes are modeled in Pydantic and reflected in regenerated TS types.

## Review Rubric (Scoring)

Score each category 1-10:

1. Frontend code quality
- 9-10: strict typing, clear state model, strong tests, resilient failure handling
- 7-8: good structure but some coverage or maintainability gaps
- 5-6: works but weak tests/types/boundaries
- <5: high risk of regression

2. Design
- 9-10: cohesive tokenized design, strong hierarchy, complete states, theme-safe
- 7-8: solid but with some inconsistency/gaps
- 5-6: functional but visually/UX inconsistent
- <5: fragile or unclear interaction model

3. Architecture
- 9-10: crisp boundaries, modular, low coupling, scalable
- 7-8: mostly clean with a few hotspots
- 5-6: notable coupling and organization debt
- <5: difficult to extend safely

If any category is <8, create follow-up tasks before closing the feature.

## Best Practices by Category (Extracted from Existing atopile Frontends)

This section translates current proven patterns into reusable defaults for new web apps.

### 1) Feature Scaffold Template

Best practices:
- Start from a predictable module split: `api/`, `store/`, `hooks/`, `components/`, `types/`, `styles/`, `utils/`.
- Keep feature entrypoints small; place business logic in hooks/store/actions.
- Build multi-entry pages with shared provider/bootstrap patterns where needed.

Use:
- One feature root folder per major UI capability (explorer, logs, builds, wizard).
- One typed API module per backend domain.
- One store slice or store action cluster per feature domain.

### 2) Testing Matrix

Best practices:
- Maintain a dedicated frontend test setup for DOM and host mocks.
- Test store transitions directly (state/action correctness).
- Test API clients and error handling independently from UI.
- Add component behavior tests for interaction-heavy controls.

Use:
- `setup.ts` equivalent for jsdom and host API mocks.
- Minimum per feature:
  - 1 store/action test
  - 1 API/transport test
  - 1 component interaction test
  - 1 error/loading-state test

Example (scoped test matrix for a build queue feature):
- Store test: `enqueueBuild` + `completeBuild` transitions.
- API test: `POST /api/build` error -> `APIError` mapping.
- Component test: clicking "Cancel" calls `sendAction('cancelBuild', { buildId })`.
- State test: disconnected websocket shows reconnect banner.

### UI Automation Notes (Puppeteer + Vite Dev Server)

For this repo, these are the correct tools:
- Puppeteer is already a project dependency and used by Vite dev tooling.
- Vite dev server already exposes screenshot and UI-log endpoints for automation flows.

Recommended test pyramid for UI:
1. Vitest + RTL for component/store/API logic.
2. Puppeteer against Vite dev server for interaction and visual regression checks.
3. Screenshot-based assertions for key states (loading/error/expanded/collapsed/workflow steps).

Dev-server-driven automation workflow:
1. Start backend + Vite (`npm run dev:all` in `src/ui-server`).
2. Drive UI via Puppeteer (click/type/scroll/key events).
3. Capture images through screenshot endpoint.
4. Inspect `ui-logs` endpoint for runtime errors/warnings.
5. Fail CI/local check if screenshot diff or UI logs exceed threshold.

Example (capture screenshot via Vite API):
```bash
curl -sS -X POST http://127.0.0.1:5173/api/screenshot \
  -H 'Content-Type: application/json' \
  -d '{"path":"/","name":"sidebar-default","waitMs":1200}'
```

Example (trigger deterministic UI state before screenshot):
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

Example (read captured UI runtime logs):
```bash
curl -sS http://127.0.0.1:5173/api/ui-logs
```

Automation guardrails:
- Keep selectors stable with `data-testid`/semantic roles for critical flows.
- Use fixed viewport and deterministic waits for screenshot consistency.
- Prefer state-triggered waits (element/event ready) over arbitrary sleep when possible.
- Treat console/runtime errors as test failures unless explicitly allowlisted.

### 3) Performance Budgets + Profiling Workflow

Best practices:
- Memoize expensive derived data (`useMemo`) and callback props (`useCallback`) in hot render paths.
- Use `requestAnimationFrame` for resize/drag/render loops.
- Offload layout/graph/geometry heavy computation to Web Workers.
- Avoid broad subscriptions to global store when only slices are needed.

Use:
- Define budgets per feature:
  - input-to-paint latency target
  - max acceptable rerenders per interaction
  - max compute time on main thread before worker offload
- Profile before optimizing: capture hot components/selectors/effects first.

### 4) Accessibility Baseline

Best practices:
- Include keyboard handlers for interactive widgets (lists, comboboxes, panels).
- Add semantic roles and ARIA state where native semantics are insufficient.
- Keep focus-visible styling explicit and consistent with tokens.

Use:
- Required checks:
  - keyboard navigation works without mouse
  - focus order is deterministic
  - controls expose state via ARIA where needed
  - color contrast remains readable in both themes

Example (keyboard-ready collapsible section):
```tsx
<button
  aria-expanded={!collapsed}
  aria-controls={`section-${id}`}
  onClick={toggle}
  onKeyDown={(e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      toggle();
    }
  }}
>
  {title}
</button>
<div id={`section-${id}`} role="region">
  {children}
</div>
```

### 5) Error Taxonomy + UX Handling

Best practices:
- Use typed error wrappers for HTTP/API failures.
- Model connection state explicitly (connected, disconnected, reconnecting).
- Auto-clear transient errors only with clear timeout policy.
- Provide actionable UI messaging for degraded states.

Use:
- Define standard classes:
  - transport/network
  - validation/user input
  - backend action failure
  - permission/auth (if applicable)
  - unknown/internal
- Map each class to a required UI response pattern.

Example (error mapping):
- `transport/network`: show reconnect status + retry affordance.
- `validation/user input`: inline field error + preserve user input.
- `backend action failure`: toast + contextual action row error.
- `unknown/internal`: generic error panel + diagnostic ID/log pointer.

### 6) State Management Conventions

Best practices:
- Centralize app state in typed store actions/selectors.
- Use selector-based subscriptions to minimize rerenders.
- Keep persisted selection/context state separate from ephemeral UI state.
- Use cross-view synchronization mechanisms only where necessary and explicit.

Use:
- For each feature, document:
  - source-of-truth state
  - derived selectors
  - side-effect entrypoints
  - reset semantics

### 7) WebSocket Protocol Playbook

Best practices:
- Implement reconnect with bounded exponential backoff.
- Track pending action requests with correlation IDs and timeouts.
- Distinguish full-state sync messages from action-result/event messages.
- On reconnect, resync critical state via explicit bootstrap actions.

Use:
- Standard WS envelope:
  - `type` (state/event/action_result/action)
  - typed payload
  - optional `requestId` for request/response correlation
- Required client behavior:
  - safe cleanup on disconnect
  - pending request cancellation on reconnect/disconnect
  - out-of-order tolerance in reducers

Example (typed WS envelope):
```ts
type WsMessage =
  | { type: 'state'; data: AppState }
  | { type: 'event'; event: EventType; data: EventPayload }
  | { type: 'action_result'; action: string; requestId?: string; result: { success: boolean; error?: string } };
```

Example (request/response correlation):
```ts
const requestId = `${Date.now()}-${++counter}`;
pending.set(requestId, { resolve, reject, timeoutId });
ws.send(JSON.stringify({ type: 'action', action: 'build', payload: { requestId, ...payload } }));
```

### 8) Data-Contract Workflow Details

Best practices:
- Treat backend schema as source-of-truth.
- Generate frontend TS types from schema and import them in API/store layers.
- Avoid manual string protocol branching where generated enums/types exist.

Use:
- Mandatory workflow:
  1. update backend Pydantic model
  2. regenerate schema/types
  3. update frontend compile errors until clean
  4. add/adjust tests for contract changes

### 9) PR Checklist + Quality Gates

Best practices:
- Enforce gates on architecture, design, and code quality before merge.
- Require explicit confirmation of websocket resiliency and typed contracts.
- Require proof of testing for changed behaviors (not only snapshots).

Use:
- Include PR checklist items for:
  - contract generation updated
  - WS reconnect/resync path verified
  - accessibility checks completed
  - performance-sensitive paths reviewed
  - tests added/updated

Example (copy into PR description):
```md
- [ ] Pydantic contract updated (if API/WS changed)
- [ ] TS generated types regenerated and committed
- [ ] WS reconnect + resync verified manually
- [ ] Keyboard/focus behavior verified
- [ ] Added/updated: store test, API test, UI interaction test
- [ ] Loading/error/empty states verified in UI
```

### 10) End-to-End Feature Example Standard

Best practices:
- Build at least one “reference implementation” per major feature type.
- Keep reference examples small but complete: contract -> transport -> state -> UI -> tests.

Use:
- For new apps/features, document one exemplar flow including:
  - Pydantic model definition
  - generated TS contract usage
  - API + WS handling
  - store update path
  - component rendering and interaction
  - verification steps and test cases

Example (minimal exemplar flow outline):
1. Add `BuildActionRequest` and `BuildActionResult` Pydantic models.
2. Regenerate TS schema and import types in `api/ws.ts`.
3. Implement `sendActionWithResponse('build', payload)` in transport.
4. Update store `startBuild` action for pending/success/error states.
5. Wire button in component to call `startBuild`.
6. Add tests for store transition + action transport + button interaction.
