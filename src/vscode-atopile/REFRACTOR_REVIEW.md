# Refactor Review + 3 Stages

This doc captures the review findings for the current implementation and the
three stages of work required to reach the Phase 1 goals (stateless extension,
VS Code-agnostic UI server, minimal webviews).

## Review Findings

### High
- Webview entrypoints still load the VS Code-bound UI (`Sidebar`/`LogViewer`) that
  uses `acquireVsCodeApi`, so the stateless/iframe flow will not work in dev.
  `src/ui-server/sidebar.html`,
  `src/ui-server/src/sidebar.tsx`,
  `src/ui-server/src/components/Sidebar.tsx`,
  `src/ui-server/log-viewer.html`,
  `src/ui-server/src/logViewer.tsx`,
  `src/ui-server/src/components/LogViewer.tsx`
- WebSocket URL and message types do not match the backend. UI connects to
  `ws://localhost:8501/ws` and expects `actionResponse`, while the backend serves
  `/ws/state` and responds with `action_result`.
  `src/ui-server/src/api/websocket.ts`,
  `src/atopile/server/server.py`

### Medium
- UI server has not moved to `src/ui-server` yet; `webviews/` still contains the
  full Vite app and tests, so webviews are not minimal wrappers.
  `src/ui-server/package.json`,
  `src/ui-server/src/`
- Dev flow still relies on VS Code polyfill + WS proxy, keeping the UI coupled
  to VS Code in dev.
  `src/ui-server/src/dev.tsx`,
  `src/ui-server/index.html`,
  `src/ui-server/dashboard/dev-server.ts`

### Low
- Types/comments still describe extension-owned state, conflicting with the
  new UI-owned state model.
  `src/ui-server/src/types/build.ts`

## Stage 1: Make UI Server Actually VS Code-Agnostic

Goal: UI runs in a normal browser without `acquireVsCodeApi`, and connects
directly to the backend WS/HTTP endpoints.

Tasks:
- Switch webview entrypoints to use the new store-based UI (e.g. `SidebarNew`),
  or migrate the old components to the store/hooks pattern.
- Remove/disable `acquireVsCodeApi` usage in core UI paths.
- Align WS URL and message types with backend (`/ws/state`, `action_result`).
- Update type comments to reflect UI-owned state.

## Stage 2: Move UI Server to `src/ui-server` (Vite)
Goal: Vite app lives outside `webviews/`, with its own package.json, dev scripts,
and build output.

Tasks:
- Relocate Vite app (src, config, tests) to `src/ui-server`.
- Update scripts/docs to run Vite from the new location.
- Remove or replace `webviews` dev server/proxy if not needed.

## Stage 3: Shrink `webviews/` to Minimal Wrappers

Goal: `webviews/` contains only the minimal HTML/JS needed to embed the UI
server in VS Code (iframe shells).

Tasks:
- Replace webview HTML with iframe wrappers pointing at the Vite dev server.
- Remove remaining React app code from `webviews/`.
- Ensure extension providers only inject iframe URLs and CSP.
- Update/trim tests to cover iframe wrappers and extension providers.

## Phase 2: Backend Layer Split (API/Core/Models)

Goal: Separate FastAPI routing from business logic and external API clients.

Tasks:
- Create explicit API routing layer (FastAPI routers).
- Move build/config/compiler logic into a Core layer.
- Move package registry / external calls into a Models layer.
- Align UI API client types with backend schemas.

## Phase 4: Feature Migration

Goal: Migrate remaining features to the new UI store/API flow.

Tasks:
- Move remaining panels/actions to the new hooks/store pattern.
- Remove legacy extension state/actions and old UI codepaths.
- Align UI actions with backend API/WebSocket events.
