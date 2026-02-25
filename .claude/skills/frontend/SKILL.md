---
name: frontend
description: "Frontend standards for atopile extension webviews: architecture, contracts, design system, and testing workflow."
---

# Frontend Skill

Use this skill when building or modifying frontend features in atopile.
Default target is extension webviews (`ui-server` + `vscode-atopile`).

## Quick Start

Dependency install:

```bash
cd src/ui-server
bun install
```

Frontend-only loop (no backend integration):

```bash
cd src/ui-server
bun run dev
bun run test
bun run build
```

Webview integration loop (backend + Vite):

```bash
cd src/ui-server
./dev.sh
```

Extension package/install loop:

```bash
ato dev compile && ato dev install cursor
# or
ato dev compile && ato dev install vscode
```

Command reference:

- `bun install`: install/sync JS dependencies.
- `bun run dev`: start local Vite dev server (frontend-only iteration).
- `bun run test`: run local Vitest suite once.
- `bun run build`: run local `tsc && vite build`.
- `./dev.sh`: run backend + Vite for integration testing in browser.
- `ato dev compile`: build extension artifacts (default target `all`).
- `ato dev install cursor|vscode`: install latest built extension `.vsix`.

## Relevant Files

### Main Extension Webview App

- Root: `src/ui-server/src/`
- Transport: `src/ui-server/src/api/`
- Global state: `src/ui-server/src/store/`
- Feature hooks: `src/ui-server/src/hooks/`
- Feature components: `src/ui-server/src/components/`
- Shared components: `src/ui-server/src/components/shared/`
- Utilities: `src/ui-server/src/utils/`
- Styles/tokens: `src/ui-server/src/styles/`
- Contracts: `src/ui-server/src/types/`
- Tests: `src/ui-server/src/__tests__/`

### Extension Host Bridge

- Root: `src/vscode-atopile/src/`
- Use for IDE commands/webview wiring/host integration.
- Keep core React UI logic out of this layer.

### Specialized Standalone App Example

- Root: `src/atopile/visualizer/web/src/`
- Use as reference for compute/canvas/worker patterns.

### Layout Editor (Specialized)

- Root: `src/atopile/layout_server/frontend/src/`
- Specialized layout editor frontend; not default architecture for webviews.

## Dependants (Call Sites)

- Extension webviews are built from `src/ui-server` and loaded by `src/vscode-atopile`.
- `ato dev compile` and `ato dev install` are the common extension developer loop.
- `src/atopile/visualizer/web` is a separate app and reference pattern, not default target.

## How to Work With / Develop / Test

### Typical Change Paths

Use these patterns to keep changes scoped and predictable.

1. UI-only change (no contract changes)

- touch `components/`, `styles/`, small `hooks/` usage
- avoid transport/store churn unless required
- validate through browser-first flow + focused component tests

2. UI + state change

- add/adjust store fields/actions/selectors
- keep transport untouched if payload shape is unchanged
- add store transition tests and UI interaction tests

3. UI + contract/transport change

- update Pydantic contracts first
- regenerate TS types
- update `api/` mapping + store state transitions + UI
- add transport and state tests, then browser flow validation

### Architecture Standard

Default architecture:

- Backend: FastAPI (domain, APIs, events)
- Frontend: React + Vite
- Realtime: WebSocket-first transport

Layer boundaries:

- `api/`: HTTP + WS transport and payload mapping
- `store/`: typed app state, actions, selectors
- `components/`: rendering/composition
- `utils/lib`: pure transforms/logic

### Contract Standard (Required)

Schema-first contract workflow:

1. Define/modify backend Pydantic model.
2. Regenerate frontend TS schema/types.
3. Update frontend transport/store/components using generated types.
4. Add/update tests for changed contract behavior.

Do not:

- maintain duplicate handwritten interfaces if generated types exist
- use stringly-typed protocol payloads when typed contracts exist

### One-Flow Rule (Required)

Implement one canonical user flow per feature.

Do not introduce fallback flow branches.
If dependency/state is unavailable, surface a clear stop-state error in the same flow context.

### WebSocket Standard

Use WebSocket for:

- interactive state sync
- action dispatch + action results
- long-running workflow updates

Use HTTP for:

- bootstrap reads
- direct idempotent reads
- file/artifact retrieval

Required WS client behavior:

- reconnect with bounded backoff
- explicit connected/disconnected state in store
- pending request timeout/cancel handling
- post-reconnect resync

Recommended WS client behavior:

- centralize WS connection in `api/` module
- keep message decoding/type-guarding out of components
- record minimal telemetry/logging for reconnect and parse failures
- guard against stale async results when reconnecting

Example envelope shape:

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

### Reuse Rules

Before creating new primitives:

1. Check `src/ui-server/src/components/shared/`.
2. Check `src/ui-server/src/utils/` for existing logic.
3. If adding compute/canvas behavior, check `src/atopile/visualizer/web/src/lib/` and `src/atopile/visualizer/web/src/workers/`.
4. If behavior is IDE-host specific, keep it in `src/vscode-atopile/src/`.

Promote to shared when:

- used by 2+ feature surfaces, or
- repeated interaction semantics would drift if duplicated.

## Shared Assets Reference

### Shared Components (ui-server)

Prefer reusing these before creating equivalents:

- `src/ui-server/src/components/shared/CopyableCodeBlock.tsx`
- `src/ui-server/src/components/shared/EmptyState.tsx`
- `src/ui-server/src/components/shared/MetadataBar.tsx`
- `src/ui-server/src/components/shared/PanelSearchBox.tsx`
- `src/ui-server/src/components/shared/PublisherBadge.tsx`
- `src/ui-server/src/components/shared/TreeRowHeader.tsx`
- `src/ui-server/src/components/shared/VersionSelector.tsx`

### Shared Utilities (ui-server)

Prefer extending these utilities:

- `src/ui-server/src/utils/codeHighlight.tsx`
- `src/ui-server/src/utils/nameValidation.ts`
- `src/ui-server/src/utils/packageUtils.ts`
- `src/ui-server/src/utils/searchUtils.ts`

### Specialized Utility Reference (visualizer)

Useful standalone reference:

- `src/atopile/visualizer/web/src/lib/exportUtils.ts`

## Best Practices

### Frontend Code Quality

- Keep strict TS and typed state transitions.
- Isolate side effects in transport/hooks, not leaf components.
- Use selectors, not broad full-store subscriptions.
- Implement explicit loading/error/empty states.

Example typed API boundary:

```ts
export async function fetchBuilds(
  projectRoot: string,
): Promise<BuildSummary[]> {
  const res = await fetch(
    `/api/builds?project_root=${encodeURIComponent(projectRoot)}`,
  );
  if (!res.ok) throw new APIError(res.status, "Failed to fetch builds");
  const data = (await res.json()) as { builds: BuildSummary[] };
  return data.builds;
}
```

### Design System

Apply across all surfaces:

- host-native typography/colors first
- brand accents only where semantically useful
- complete interaction states (`default/hover/focus-visible/active/disabled/loading`)
- consistent spacing/row-height/typography rhythm
- tokenized colors/spacing/radius/z-index, no ad-hoc semantic hardcoding

Example tokenized control:

```css
.btn-primary {
  background: var(--color-brand-500);
  color: var(--color-text-on-brand, #fff);
  border: 1px solid var(--color-brand-500);
  border-radius: var(--radius-md);
  padding: var(--space-sm) var(--space-md);
}
.btn-primary:hover {
  background: var(--color-brand-600);
}
.btn-primary:focus-visible {
  outline: 2px solid var(--color-info);
  outline-offset: 2px;
}
.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
```

### Accessibility Baseline

Required:

- keyboard-operable controls
- deterministic focus order
- ARIA only where native semantics are insufficient
- visible focus states
- readable contrast in light/dark modes

### Performance Baseline

Required:

- memoize expensive derived data/callbacks in hot paths
- use `requestAnimationFrame` for drag/resize animation paths
- move heavy layout/geometry/compute work to workers where needed
- keep WS update handling efficient under active event streams

Operational checks:

- avoid full-store subscriptions in high-frequency components
- memoize derived collections used in render loops
- verify no avoidable setState chains during drag/scroll/update streams
- keep long-running transformations out of component render bodies

## Implementation Playbooks

### Playbook A: New Extension Webview Panel (`ui-server`)

1. Add/confirm contracts

- if backend shape changes: update Pydantic + regenerate types

2. Add transport mapping

- implement data/action methods in `src/ui-server/src/api/`

3. Add store state/actions

- add minimal new fields/actions in `store/`
- expose selectors for component use

4. Compose UI

- build panel in `components/`
- reuse `components/shared/` primitives where possible

5. Validate

- run tests
- run browser-first flow
- capture screenshot + inspect ui logs

### Playbook B: Compute/Canvas-heavy Feature

1. Put core transforms into `utils/` or specialized `lib/` module.
2. Add worker offload if main-thread latency becomes visible.
3. Keep render components thin and memoized.
4. Validate interaction smoothness under active updates.

### Playbook C: Long-running Workflow UI

Use one canonical flow:

- trigger
- in-progress
- completion or error in same context

Required:

- disable conflicting controls during in-progress state
- emit progress updates via typed WS events
- provide deterministic terminal state in store

## Detailed Testing Notes

### Testing Scope by Layer

1. Unit tests

- pure utils/lib transforms

2. Store tests

- action transitions and derived selector correctness

3. Transport tests

- API/WS mapping, error handling, request correlation behavior

4. UI tests

- user interaction + state rendering behavior

5. Browser automation checks

- key flow interaction + screenshot + ui logs

### WebSocket Feature Test Cases

At minimum test:

- initial connect path
- disconnect state update
- reconnect and resync path
- pending request timeout/cancel path

Recommended:

- late or duplicate event tolerance
- malformed message handling without UI crash

## Testing Standard

Minimum per feature:

1. Store/action test
2. API/transport test
3. UI interaction test
4. Error/loading/empty-state test

Example matrix (build queue):

- store: enqueue + complete transitions
- API: build start error -> typed API error
- UI: cancel click dispatches cancel action
- state: disconnected WS state is visible

### Browser-First Dev Viewer Flow (Required)

Agents should self-test in browser flow first:

```bash
cd src/ui-server
./dev.sh
```

Then:

1. Validate interaction flow in browser webview page.
2. Capture key-state screenshots.
3. Inspect UI logs.
4. Fix issues.
5. Ask user to test in extension host only after browser flow is clean.

Relevant pages:

- `http://127.0.0.1:5173/`
- `http://127.0.0.1:5173/log-viewer.html`
- `http://127.0.0.1:5173/migrate.html`
- `http://127.0.0.1:5173/test-explorer.html`

### Puppeteer + Vite Screenshot APIs

Use these built-in dev endpoints:

```bash
curl -sS -X POST http://127.0.0.1:5173/api/screenshot \
  -H 'Content-Type: application/json' \
  -d '{"path":"/","name":"default","waitMs":1200}'
```

```bash
curl -sS -X POST http://127.0.0.1:5173/api/screenshot \
  -H 'Content-Type: application/json' \
  -d '{"path":"/","name":"projects-expanded","uiActions":[{"type":"openSection","sectionId":"projects"}],"uiActionWaitMs":600}'
```

```bash
curl -sS http://127.0.0.1:5173/api/ui-logs
```

Automation guardrails:

- stable selectors (`data-testid` or semantic roles)
- fixed viewport for diffs
- readiness-based waits preferred over arbitrary sleep
- runtime errors treated as failures unless allowlisted

## Definition of Done

A feature is done only when all are true:

- [ ] one canonical flow implemented (no fallback branch)
- [ ] contract changes modeled in Pydantic + regenerated TS consumed
- [ ] WS behavior validated (connect/reconnect/resync)
- [ ] tests added/updated (store + transport + UI + state handling)
- [ ] browser-first dev viewer checks complete
- [ ] user asked to test extension host only after browser validation
- [ ] build/test commands pass for touched app
- [ ] component/util placement follows repo structure and reuse rules

## PR Checklist (Copy/Paste)

```md
- [ ] Single canonical flow preserved (no fallback path added)
- [ ] Pydantic models updated for API/WS changes
- [ ] Generated TS schema/types regenerated and committed
- [ ] WS reconnect/resync behavior verified
- [ ] Browser dev viewer flow validated (`./dev.sh`)
- [ ] Screenshots + UI logs reviewed (no unapproved runtime errors)
- [ ] Added/updated: store test, transport test, UI interaction test
- [ ] Asked user to test in extension host only after browser checks passed
```
