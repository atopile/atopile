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

## Current Staged Progress

The current staged changes materially reduce the output-panel parity gap:

- `panel-layout` now opens the shared layout server for the selected project/target via
  `openLayout`; it is no longer a placeholder panel.
- The extension/webview panel host and RPC bridge are more robust and now emit structured logs.
- The 3D panel got small reliability fixes (logging + resize/init cleanup).

The plan below reflects that new baseline and focuses on the remaining user-visible gaps.

## Parity Matrix

| Status | Area | Mainline (`~/git/atopile`) | Rewrite (`~/git/atopile_extension`) | Gap to Close |
|---|---|---|---|---|
| 🟡 | Header + settings | Version, settings, health/status affordances | Version + settings button exist; settings are much narrower | Add connection/health affordances and finish settings coverage |
| 🟡 | Project selection | Searchable combobox + new-project flow | Searchable project picker + placeholder new-project button | Implement create-project flow end to end |
| 🟡 | Target selection | Select target, add/edit/delete target, choose build command | Select target only | Implement build-target lifecycle |
| 🟡 | Action row | Build, KiCad, 3D, Layout, Manufacture | Build, Layout, 3D, KiCad, Developer | Validate the new panel flows and decide whether Developer remains a rewrite-only affordance |
| 🟡 | Build queue | Resizable, collapsible, cancel actions, logs/problem affordances | Resizable only | Add collapse, cancel, and jump-to-diagnostics/logs |
| 🟡 | Connection UX | Disconnected/restart/help affordances integrated with status | Overlay exists; no visible live status indicator | Add explicit connection/health state in the chrome |
| 🟡 | Files | Mature explorer with lazy loading, context menu, create/rename/delete/duplicate, reveal/open terminal | Read-only tree open-file view | Add file-management operations and explorer affordances |
| 🟡 | Packages | Browse/install/remove plus detail panel and richer metadata flow | Detail panel is ported and integrated; package workflow exists | Polish behavior, validate copied flows, and close any metadata/action gaps |
| 🟡 | Parts | Search/install plus detail panel, datasheet and footprint/3D views | Detail panel is ported and integrated; datasheet/image/3D exist | Polish sourcing workflow; footprint preview is deferred until the shared layout viewer lands |
| 🟢 | Standard library | Browse/search stdlib | Browse/search stdlib | Good enough; keep current rewrite implementation |
| 🟢 | Structure | Module tree from active file | Module tree from active file | Good enough; polish only if bugs appear |
| 🟢 | Parameters | Variable/constraint browsing | Variable/constraint browsing | Good enough; polish only if bugs appear |
| 🟢 | BOM | BOM browsing with summary and source links | BOM browsing with summary and source links | Good enough; polish only if bugs appear |
| 🟡 | Logs | Dedicated logs panel with build-log workflows | Dedicated logs panel exists; structured extension/webview logging is wired | Add user-facing build/log jumps and any missing workflows |
| 🟡 | 3D | Dedicated preview surface tied to builds | Dedicated preview surface exists | Mostly done; verify asset resolution, resize, and failure UX |
| 🟡 | Layout | Real layout editor/preview | Shared layout server is embedded in `panel-layout` and opens the selected target PCB | Validate behavior end to end and restore related preview workflows on top of the shared viewer |
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
- Expose source/mode/version/health clearly in the UI.
- Make restart/failure recovery obvious from the sidebar and panel surfaces.

### 6. Remove parity-risk dead ends

- Delete placeholder or unused surfaces that are not part of the final parity story.
- Do not keep duplicate ways to do the same thing unless mainline users rely on them.
- Prefer one good rewrite-native path per user task.
