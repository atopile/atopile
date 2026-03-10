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
| 🟡 | Packages | Browse/install/remove plus detail panel and richer metadata flow | Detail panel is ported and integrated; package workflow exists | Polish behavior, validate copied flows, and close any metadata/action gaps |
| 🟡 | Parts | Search/install plus detail panel, datasheet and footprint/3D views | Detail panel is ported and integrated; datasheet/image/3D exist | Polish sourcing workflow; footprint preview is deferred until the shared layout viewer lands |
| 🟢 | Standard library | Browse/search stdlib | Browse/search stdlib | Good enough; keep current rewrite implementation |
| 🟢 | Structure | Module tree from active file | Module tree from active file | Good enough; polish only if bugs appear |
| 🟢 | Parameters | Variable/constraint browsing | Variable/constraint browsing | Good enough; polish only if bugs appear |
| 🟢 | BOM | BOM browsing with enriched cost/stock data, build badge, grouped usages, and source links | Mainline BOM is ported onto the rewrite RPC/store architecture, including LCSC enrichment and source navigation | Validate behavior against real projects and keep follow-up polish small |
| 🟢 | Logs | Dedicated logs panel with build-log workflows | Dedicated logs panel with structured logging; sidebar build/stage clicks navigate directly via store-driven selection | Good enough; validate end-to-end and polish only if bugs appear |
| 🟡 | 3D | Dedicated preview surface tied to builds | Dedicated preview surface exists | Mostly done; verify asset resolution, resize, and failure UX |
| 🟡 | Layout | Real layout editor/preview | Shared layout server is embedded in `panel-layout` and opens the selected target PCB | Validate behavior end to end and restore related preview workflows on top of the shared viewer |
| 🟡 | Migration | Dedicated migrate tab/workflow | Detail UI is ported and integrated into the sidebar | Finish workflow validation and any remaining action/polish gaps |

## Work Plan

### 1. Finish target lifecycle and polish project creation

The rewrite can now create projects and add build targets, but lifecycle coverage is still incomplete.

- Validate the sidebar "New Project" flow against real workspaces and error cases.
- Keep the folder browse/pick flow reliable across the VS Code/webview bridge.
- Implement target rename/update/delete.
- Decide whether build-command parity belongs in the rewrite UI or can stay implicit.
- Decide whether target management lives only in the sidebar or also elsewhere in the rewrite UI.
- Keep this rewrite-native; do not bring back mainline's older card tree unless needed.

### 2. Complete the files surface

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

### 3. Add the missing detail workflows

This is the largest sidebar parity gap.

- Validate and polish the copied package detail UI:
  - description/readme
  - versions
  - install/update/remove
  - imports/usage
  - package artifacts if still relevant
- Validate and polish the copied part detail UI:
  - datasheet link
  - richer attributes
  - stock/pricing
  - image / 3D views where available
  - restore footprint preview later via the shared layout viewer rather than a temporary custom embed

### 4. Harden the output panels

The rewrite now has the right panel primitives. The remaining work is to make them
behave like product features instead of demos.

- Validate the new `openLayout` flow against project changes, target changes, and missing/unbuilt layouts.
- Keep `panel-layout` on the shared layout viewer path; do not add a second layout surface.
- Reintroduce package-layout and part-footprint preview through the shared layout viewer instead of bespoke embeds.
- Verify 3D panel open/reopen behavior, model resolution, resize handling, and error states.
- Use the new structured logging to close debugging gaps, but keep parity work focused on user-visible flows.

### 5. Finish migration, settings, and status gaps

- Finish migrate workflow parity on top of the copied detail UI.
- Expand settings beyond `devPath` and `autoInstall` if the rewrite is replacing the shipped extension.
- Keep source/mode/version/health visible in the UI and add obvious recovery/help actions.
- Make restart/failure recovery obvious from the sidebar and panel surfaces.

### 6. Remove parity-risk dead ends

- Delete placeholder or unused surfaces that are not part of the final parity story.
- Do not keep duplicate ways to do the same thing unless mainline users rely on them.
- Prefer one good rewrite-native path per user task.
