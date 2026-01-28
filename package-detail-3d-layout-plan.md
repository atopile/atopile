# Plan: Fix 3D + Layout Previews in VS Code Package Detail Panel

## Scope
Fix package detail panel previews in the VS Code extension so 3D (.glb) and layout (.kicad_pcb) assets load reliably without proxy hacks. This covers the extension webview UI, the local build-server API, and the packages backend service.

## Overview: How This Is Set Up

### Actors and Responsibilities
- **VS Code Extension** (`src/vscode-atopile`): Hosts the webview, injects backend URLs, and sets the webview Content Security Policy (CSP).
- **UI Server** (`src/ui-server`): React UI that runs inside the webview. It renders the Package Detail panel and embeds the 3D and layout viewers.
- **Build Server** (`src/atopile/server`): Local FastAPI server used by the extension for builds, state, and package metadata aggregation.
- **Packages Backend** (`/Users/narayanpowderly/projects/backend/services/packages`): Service that stores package assets (artifacts, layouts) in S3/CDN and returns their URLs in package details.
- **CDN/S3**: Serves `.glb` and `.kicad_pcb` files via public URLs.

### Data / Asset Flow (Today)
1) UI requests package details from the **build server**.
2) Build server returns metadata that includes layout/artifact URLs from the **packages backend**.
3) UI currently rewrites those URLs through a **build-server proxy** endpoint (`/api/packages/proxy`).
4) Webview CSP blocks external hosts by default, so the proxy is used to keep requests “same-origin.”
5) Viewer scripts are loaded separately:
   - **3D**: `model-viewer` is loaded from Google CDN.
   - **Layout**: KiCanvas is loaded from `/vendored/kicanvas.js`.

### How It Should Work (Target)
- The Package Detail panel should **load assets directly from the package CDN/host** using the URLs already provided in package details.
- The webview CSP should explicitly allow that asset origin (and any required script/media origins).
- Viewer scripts should be **bundled in the webview build**, not loaded from external CDNs or hardcoded public paths.
- The proxy endpoint becomes unnecessary and can be removed.

## Current State Review (Key Findings)

### Extension / UI Server (this repo)
- Package detail panel uses a proxy helper that rewrites asset URLs to the local build-server endpoint: `proxyAssetUrl` in `src/ui-server/src/components/PackageDetailPanel.tsx`.
- The 3D viewer loads `model-viewer` from Google CDN (`https://ajax.googleapis.com/...`) in `src/ui-server/src/components/ModelViewer.tsx`. The webview CSP in `src/vscode-atopile/src/providers/SidebarProvider.ts` **does not** allow that host, so the script is blocked in VS Code webviews.
- KiCanvas loads a script from a hardcoded path (`/vendored/kicanvas.js`) in `src/ui-server/src/components/KiCanvasEmbed.tsx`. Webviews can only load files via `webview.asWebviewUri(...)`, so this path does not resolve in production webviews.
- The webview CSP (Sidebar) allows `connect-src` only to the build-server and websocket origin: `connect-src ${apiUrl} ${wsOrigin};` in `src/vscode-atopile/src/providers/SidebarProvider.ts`. Any direct CDN/package-backend asset URL will be blocked without CSP updates.

### Build Server (this repo)
- The build server exposes `/api/packages/proxy` and `/api/packages/proxy/{filename}` in `src/atopile/server/routes/packages.py` and restricts allowed hosts (default only `cloudfront.net`). This proxy is the current workaround but is fragile and fails if assets are not hosted on an allowed domain.

### Packages Backend (separate repo)
- Asset URLs in package details are built from a CDN domain: `compute_layout_url` / `compute_download_url` in `/Users/narayanpowderly/projects/backend/services/packages/backend/app/services.py`.
- CORS in the packages backend is driven by `settings.cors.allowed_origins` (default empty) in `/Users/narayanpowderly/projects/backend/services/packages/backend/app/config.py` and applied in `app/main.py`. If the UI accesses assets via the packages backend domain, CORS must explicitly allow webview origins.

## What’s Broken (Why It Fails Today)
- **CSP blocks external scripts**: `model-viewer` cannot load from Google CDN inside the VS Code webview.
- **KiCanvas script path is invalid in webview**: `/vendored/kicanvas.js` is not a webview URI.
- **Proxy is restrictive and brittle**: it only allows specific hosts by default and adds production-specific failure points.
- **Direct asset loads would be blocked** unless CSP and CORS are explicitly configured.

## Target Behavior
- The Package Detail panel loads layout and 3D assets directly from a single canonical server origin, without UI-side proxying.
- Webview CSP explicitly allows asset loads from that origin.
- The UI bundles/loads viewer scripts locally (no external CDN script dependencies).
- Backend permissions/CORS are configured to allow webview access to package assets.

## Proposed Fix (High-Level)
1) Remove the UI proxy helper and load package assets directly from the server URLs provided by package details.
2) Ensure the asset server responds with permissive CORS for VS Code webview origins (or `*` for public assets).
3) Bundle the viewer scripts in the UI build so they do not depend on external CDNs or hardcoded public paths.
4) Update webview CSP to allow the asset origin.

## Detailed Plan

### Phase 1 — Decide and Normalize Asset Origin
- Confirm the canonical asset origin for package assets:
  - Option A (preferred): package assets are served directly from the packages backend domain (or its CDN) and are publicly readable with CORS enabled.
  - Option B: assets are served by the local build server (not preferred if it reintroduces proxying).
- If Option A:
  - Ensure package details in the build server continue to expose the asset URLs provided by the packages backend (no proxy rewriting).

### Phase 2 — Remove Proxy Hack in UI + Build Server
- UI: remove `proxyAssetUrl` in `src/ui-server/src/components/PackageDetailPanel.tsx` and pass `layout.url` / `artifact.url` directly to `KiCanvasEmbed` and `ModelViewer`.
- Build server: deprecate or remove `/api/packages/proxy` endpoints in `src/atopile/server/routes/packages.py` and any related env/config (`ATOPILE_PACKAGES_ASSET_HOSTS`, `ATOPILE_ALLOW_UNSAFE_ASSET_PROXY`).

### Phase 3 — Fix Viewer Script Loading (No External CDN)
- `ModelViewer` (`src/ui-server/src/components/ModelViewer.tsx`):
  - Replace CDN script injection with a bundled dependency (e.g. `@google/model-viewer`) imported in the module so it ships in the main webview bundle.
- `KiCanvasEmbed` (`src/ui-server/src/components/KiCanvasEmbed.tsx`):
  - Replace hardcoded `/vendored/kicanvas.js` with a bundled asset reference via Vite (e.g. `import kicanvasUrl from '../assets/kicanvas.js?url'`) or package it as a module if possible.
  - Ensure the generated URL resolves inside the webview (no raw file paths).

### Phase 4 — Update Webview CSP
- In `src/vscode-atopile/src/providers/SidebarProvider.ts`, extend CSP to allow the asset origin:
  - Add the packages backend/CDN host to `connect-src`.
  - If `model-viewer` requires `img-src` or `media-src` for textures/environment maps, add the asset host there as well.
- Keep CSP tight: only add the known asset origin(s), not a blanket `https:` unless required.

### Phase 5 — Backend Permissions / CORS
- Packages backend (`/Users/narayanpowderly/projects/backend/services/packages`):
  - Update `settings.cors.allowed_origins` to include VS Code webview origins (or allow `*` for public asset GETs).
  - If assets are served from a CDN (S3/CloudFront), ensure the CDN’s CORS configuration allows:
    - `GET`/`HEAD` from `vscode-webview://*` (or `*`),
    - `Content-Type` exposure for `.glb` and `.kicad_pcb`.
- Verify that the CDN returns correct `Content-Type` (`model/gltf-binary` for `.glb`, `text/plain` for `.kicad_pcb`).

### Phase 6 — Verification
- Add a small manual checklist in the extension docs (or a test plan) to verify:
  - 3D model loads in the Package Detail panel.
  - Layout renders in KiCanvas.
  - No CSP violations in webview console.
  - No backend proxy calls (`/api/packages/proxy`).

## Risks / Open Questions
- What is the actual production asset host (CDN domain) and its current CORS policy?
- Do package assets require auth? If yes, direct loading will need signed URLs or an authenticated asset endpoint.
- Are there package assets that exceed size limits or require streaming optimizations for the webview?

## Deployment + Prod Implications (Packages Backend)

### CI/CD Flow (from repo workflows)
- **Backend deploy is automated** via GitHub Actions on `push` to `main` for `services/packages/**`.
- Workflow: `.github/workflows/packages_test_and_deploy.yml`
  - Runs tests + lint for backend.
  - If `main`, deploys with **Porter** using `services/packages/backend/porter.yaml`.
  - Target app: `package-server` (packages.atopileapi.com).
- **Frontend deploy** is separate: `.github/workflows/packages_frontend_deploy.yml`
  - Deploys `packages-ui` (packages.atopile.io) via Porter on `main`.
  - Preview environments for PRs.

### Production Implications for CORS Changes
- CORS allowlist is set via environment variables (Porter env groups).
- If assets are public, a permissive `GET`/`HEAD` CORS policy is low risk, but still ensure:
  - No credentials are allowed.
  - CDN/S3 CORS matches backend policy.
  - `Content-Type` is exposed for `.glb` and `.kicad_pcb`.

## Suggested Validation Steps (post-change)
1) Open VS Code → Atopile extension → Package Detail panel for a package with layouts + 3D artifacts.
2) Confirm no requests hit `/api/packages/proxy`.
3) Confirm network requests for `.glb` and `.kicad_pcb` succeed with 200 and correct `Content-Type`.
4) Confirm `model-viewer` and `kicanvas-embed` register without CSP errors.

## Local Backend Test Notes (in progress)

### Backend tweaks applied (local)
- Added `cors.allow_all` flag in packages backend config and used it in FastAPI CORS setup.
- `CDN_DOMAIN` now accepts explicit schemes (e.g., `http://localhost:9000`) to support local MinIO.

### MinIO setup observations
- Docker is required (OrbStack). Initial attempts failed until Docker was running.
- MinIO container started successfully on `127.0.0.1:9000` / `9001`.
- Creating buckets with `minio/mc` works after installing the standalone `mc` binary.
- **CORS config still failing** with `mc cors set`:
  - JSON input returned `decoding xml: EOF` (expects XML).
  - XML attempt returned `A header you provided implies functionality that is not implemented.`
  - Next step: try a simpler XML (no `ExposeHeader`) or use `mc cors set ... -` with stdin, or apply CORS via MinIO console.

### Local env (target)
- `CDN_DOMAIN=http://localhost:9000`
- `S3_ENDPOINT_URL=http://localhost:9000`
- Buckets: `packages-upload`, `packages`
