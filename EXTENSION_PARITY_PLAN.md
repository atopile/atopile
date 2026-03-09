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
| 🟡 | Header + settings | Version, settings, health/status affordances | Version + settings button exist; settings are much narrower | Add connection/health affordances and finish settings coverage |
| 🟡 | Project selection | Searchable combobox + new-project flow | Searchable project picker + placeholder new-project button | Implement create-project flow end to end |
| 🟡 | Target selection | Select target, add/edit/delete target, choose build command | Select target only | Implement build-target lifecycle |
| 🟡 | Action row | Build, KiCad, 3D, Layout, Manufacture | Build, Layout, 3D, KiCad, Developer | Add manufacturing entry point and real layout parity |
| 🟡 | Build queue | Resizable, collapsible, cancel actions, logs/problem affordances | Resizable only | Add collapse, cancel, and jump-to-diagnostics/logs |
| 🟡 | Connection UX | Disconnected/restart/help affordances integrated with status | Overlay exists; no visible live status indicator | Add explicit connection/health state in the chrome |
| 🟡 | Files | Mature explorer with lazy loading, context menu, create/rename/delete/duplicate, reveal/open terminal | Read-only tree open-file view | Add file-management operations and explorer affordances |
| 🟡 | Packages | Browse/install/remove plus detail panel and richer metadata flow | Detail panel is ported and integrated; package workflow exists | Polish behavior, validate copied flows, and close any metadata/action gaps |
| 🟡 | Parts | Search/install plus detail panel, datasheet and footprint/3D views | Detail panel is ported and integrated; datasheet/image/3D exist | Polish sourcing workflow; footprint preview is deferred until the shared layout viewer lands |
| 🟢 | Standard library | Browse/search stdlib | Browse/search stdlib | Good enough; keep current rewrite implementation |
| 🟢 | Structure | Module tree from active file | Module tree from active file | Good enough; polish only if bugs appear |
| 🟢 | Parameters | Variable/constraint browsing | Variable/constraint browsing | Good enough; polish only if bugs appear |
| 🟢 | BOM | BOM browsing with summary and source links | BOM browsing with summary and source links | Good enough; polish only if bugs appear |
| 🟡 | Logs | Dedicated logs panel with build-log workflows | Dedicated logs panel exists | Wire missing extension entry points and cross-links |
| 🟡 | 3D | Dedicated preview surface tied to builds | Dedicated preview surface exists | Mostly done; verify behavior and polish failure states |
| 🔴 | Layout | Real layout editor/preview | Placeholder panel | Build or embed the actual layout surface |
| 🔴 | Manufacturing | Full manufacturing/export workflow | Missing | Add manufacturing panel/workflow |
| 🟡 | Migration | Dedicated migrate tab/workflow | Detail UI is ported and integrated into the sidebar | Finish workflow validation and any remaining action/polish gaps |

## Work Plan

### 1. Finish project and target lifecycle flows

The rewrite can select projects and targets, but it cannot manage them yet.

- Implement "New Project" from the sidebar.
- Support folder browse/pick flows needed by project creation.
- Implement new target creation.
- Implement target rename/update/delete.
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
- Add build queue actions:
  - collapse/expand
  - cancel build
  - jump to logs

### 4. Restore advanced output workflows

These are still effectively missing.

- Replace the placeholder `panel-layout` with the real layout experience.
- Reintroduce package-layout and part-footprint preview through the shared layout viewer once that surface exists.
- Add manufacturing/export workflow parity.
  - Build confirmation
  - export directory selection
  - artifact selection / review
  - cost/stock review if still part of the product
- Finish migrate workflow parity on top of the copied detail UI.
- Verify 3D and logs flows work cleanly from the rewrite UI surfaces.

### 5. Close settings and status gaps

- Expand settings beyond `devPath` and `autoInstall` if the rewrite is replacing the shipped extension.
- Expose source/mode/version/health clearly in the UI.
- Make restart/failure recovery obvious from the sidebar and panel surfaces.

### 6. Remove parity-risk dead ends

- Delete placeholder or unused surfaces that are not part of the final parity story.
- Do not keep duplicate ways to do the same thing unless mainline users rely on them.
- Prefer one good rewrite-native path per user task.
