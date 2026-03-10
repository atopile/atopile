# Extension Parity Plan: `atopile_extension` vs `atopile`

## Goal

Reach **user-facing feature parity** with the current shipping extension interface in
`/Users/rallen/git/atopile` while keeping the rewrite architecture in
`/Users/rallen/git/atopile_extension`.

Parity here means **matching user capabilities**, not re-creating mainline's old
`vscode.postMessage` and `src/ui-server` implementation. The rewrite should keep
the hub/RPC model and only add the smallest missing surfaces needed to close the
product gap.

Before implementing any of this, review [src/EXTENSION_ARCHITECTURE.md](/Users/rallen/git/atopile_extension/src/EXTENSION_ARCHITECTURE.md).

## Recommended Approach

Recommended approach: **copy the exact mainline implementation first, then make it
compatible with the rewrite architecture**.

Use mainline as both the feature contract and the initial implementation source
for parity-sensitive UI. Then adapt the copied code to the rewrite's RPC/store
model with the fewest necessary compatibility changes. The simplest path is:

1. Copy the exact mainline UI implementation for parity-sensitive flows.
2. Adapt data flow and extension wiring to the rewrite's RPC/store architecture.
3. Remove temporary shims once the copied code is running cleanly on shared types and APIs.
4. Only reimplement from scratch when the copied implementation is clearly unnecessary or blocks the architecture.

## Parity Matrix

| Status | Area | Mainline (`~/git/atopile`) | Rewrite (`~/git/atopile_extension`) | Gap to Close |
|---|---|---|---|---|
| 🟢 | Header + settings | Version, settings, health/status affordances | Version badge, settings button, and live health state exist | Good enough; keep broader recovery/help work tracked under Connection UX |
| 🟢 | Project selection | Searchable combobox + new-project flow | Searchable project picker + end-to-end create-project flow with folder browse | Good enough; polish only if bugs appear |
| 🟢 | Target selection | Select target, add/edit/delete target, choose build command | Select target + create/edit/delete target with entry validation/suggestions | Good enough; keep the simpler rewrite target model unless product needs change |
| 🟢 | Action row | Build, KiCad, 3D, Layout, Manufacture | Build, KiCad, 3D, Layout, Manufacture, with migrate shown when needed | Good enough; keep Developer out of the primary parity chrome unless product needs change |
| 🟢 | Build queue | Resizable, collapsible, cancel actions, logs/problem affordances | Resizable, collapsible, cancel build, jump-to-logs with build/stage navigation, progress bar, completion animations | Good enough; polish only if bugs appear |
| 🟡 | Connection UX | Disconnected/restart/help affordances integrated with status | Overlay exists and the chrome now shows live health; restart/help affordances are still thin | Add explicit recovery/help actions, not just status |
| 🟡 | Files | Mature explorer with lazy loading, context menu, create/rename/delete/duplicate, reveal/open terminal | Read-only tree open-file view | Add file-management operations and explorer affordances |
| 🟢 | Packages | Browse/install/remove plus detail panel and richer metadata flow | Detail panel is ported and integrated; install/update/remove, readme, versioning, import/usage details, and 3D artifact preview exist | Good enough; keep package layout preview tracked under output panels |
| 🟢 | Parts | Search/install plus detail panel, datasheet and footprint/3D views | Detail panel is ported and integrated; install/uninstall, datasheet, image, and 3D exist | Good enough; keep footprint preview tracked under output panels |
| 🟢 | Standard library | Browse/search stdlib | Browse/search stdlib | Good enough; keep current rewrite implementation |
| 🟢 | Structure | Module tree from active file | Module tree from active file | Good enough; polish only if bugs appear |
| 🟢 | Parameters | Variable/constraint browsing | Variable/constraint browsing | Good enough; polish only if bugs appear |
| 🟢 | BOM | BOM browsing with enriched cost/stock data, build badge, grouped usages, and source links | Mainline BOM is ported onto the rewrite RPC/store architecture, including LCSC enrichment and source navigation | Validate behavior against real projects and keep follow-up polish small |
| 🟢 | Logs | Dedicated logs panel with build-log workflows | Dedicated logs panel with structured logging; sidebar build/stage clicks navigate directly via store-driven selection | Good enough; validate end-to-end and polish only if bugs appear |
| 🟡 | Runtime resolution | Extension-managed `uv`, strict ato binary resolution, self-check before use, explicit binary path override, explicit `from` source/version override, and default version pinning to the extension release | `uv` auto-bootstrap exists, production runs are pinned to the extension version, and local dev mode exists via `devPath`, but there is no explicit ato path override, no explicit `from` override, no self-check gate, and bootstrap/version behavior differs from mainline | Decide the rewrite contract for binary resolution, then restore parity for the supported modes instead of leaving install/bootstrap/version behavior implicit |
| 🔴 | LSP | VS Code language client started from the extension, with editor diagnostics/navigation/completions and build-target notifications wired through `atopile/didChangeBuildTarget` | Core server only; no VS Code `LanguageClient` is started | Add rewrite-native LSP startup and editor integration; this is separate from sidebar parity and required for full extension parity |
| 🟡 | 3D | Dedicated preview surface tied to builds | Dedicated preview surface exists and resolves project-target GLB assets | Reopen/resize path exists, but missing-file and load-failure UX still need to be surfaced instead of hanging on a loading state |
| 🟡 | Layout | Real layout editor/preview | Shared layout server is embedded in `panel-layout` and opens the selected target PCB | Shared viewer path is in place; validate `openLayout` against project/target changes and missing layouts, and restore package/part preview flows on top of it |
| 🟡 | Migration | Dedicated migrate tab/workflow | Detail UI is ported and integrated into the sidebar | Finish workflow validation and any remaining action/polish gaps |
| 🟢 | Syntax highlighting | `ato` language contribution, language configuration, and TextMate grammar | Same `ato` language contribution, language configuration, and TextMate grammar | Good enough; keep current rewrite implementation |
| 🔴 | Snippets | Extension contributes `ato` snippets | No snippet contribution | Port the mainline snippets contribution unless it is intentionally being replaced with LSP completions |

## Work Plan

### 1. Complete the files surface

Current rewrite files support is browse/open only.

- Add lazy directory loading if needed for large projects.
- Add context menu actions:
  - create file
  - create folder
  - rename
  - delete
  - duplicate
  - reveal in Finder/Explorer
  - open in terminal
- Add the extension bridge actions to execute those operations safely.
- Preserve the current simpler tree unless it proves insufficient.

### 2. Harden the output panels

The rewrite now has the right panel primitives. The remaining work is to make them
behave like product features instead of demos.

- Validate the existing `openLayout` flow against project changes, target changes, and missing/unbuilt layouts. The wiring exists; the missing work is confidence and failure-path polish.
- Keep `panel-layout` on the shared layout viewer path; do not add a second layout surface.
- Reintroduce package-layout preview through the shared layout viewer. Package details currently restore 3D artifacts, but not layout preview.
- Reintroduce part-footprint preview through the shared layout viewer. Part details still only expose image and 3D tabs.
- Fix 3D panel failure UX so missing or unloadable models produce a user-visible error state instead of an indefinite loading screen. Preserve the current open/reopen and resize path.
- Use the new structured logging to close debugging gaps in these flows, but keep parity work focused on user-visible behavior rather than log-only cleanup.

### 3. Finish migration and settings gaps

- Finish migrate workflow parity on top of the copied detail UI.
- Expand settings beyond `devPath` and `autoInstall` if the rewrite is replacing the shipped extension.
- Make binary/runtime resolution explicit instead of leaving it as resolver behavior hidden behind `devPath`.
- Decide and document which mainline resolution modes the rewrite keeps:
  - extension-managed default install pinned to the extension version
  - explicit ato binary path override
  - explicit source/version override (`from`)
  - local checkout/dev mode
- Add a real validation step before treating a resolved runtime as healthy, so bootstrap/install failures fail fast instead of surfacing later as generic core-server startup errors.
- Align `uv` bootstrap behavior with the chosen contract and keep the user-facing install flow obvious when auto-install is enabled or disabled.

### 4. Restore editor integration parity

- Start the atopile LSP from the rewrite extension as a proper VS Code `LanguageClient`.
- Match mainline document selector coverage for normal `.ato` editing.
- Wire selected build-target changes into the LSP via `atopile/didChangeBuildTarget`.
- Validate editor-facing parity for diagnostics, hovers, go-to-definition, references, completion, and rename/code actions as supported by the server.
- Keep this integration at the extension boundary; do not route editor features through the sidebar RPC/webview path.

### 5. Restore language-authoring contributions

- Keep the current syntax highlighting and language configuration unchanged unless regressions appear.
- Port snippet contribution parity from mainline.
- Prefer snippet parity through the normal VS Code contribution path rather than inventing a rewrite-specific mechanism.

### 6. Remove parity-risk dead ends

- Delete placeholder or unused surfaces that are not part of the final parity story.
- Do not keep duplicate ways to do the same thing unless mainline users rely on them.
- Prefer one good rewrite-native path per user task.
