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

## Current State

The rewrite is no longer "sidebar-only". It already has:

- sidebar header, project picker, target picker, action bar, tabbed panels, build queue
- files, packages, parts, standard library, structure, parameters, and BOM panels
- logs panel
- settings panel
- 3D model panel
- developer/debug panel

Mainline is still ahead in the places that matter most to end users:

- project lifecycle flows
- build-target lifecycle flows
- file management actions
- package and part detail workflows
- manufacturing/export workflow
- layout and migration surfaces
- build-log affordances across the extension

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
| 🟡 | Packages | Browse/install/remove plus detail panel and richer metadata flow | Browse/install/remove only | Add package detail view and version-aware workflows |
| 🟡 | Parts | Search/install plus detail panel, datasheet and footprint/3D views | Search/install/uninstall only | Add part detail view and richer sourcing workflow |
| 🟢 | Standard library | Browse/search stdlib | Browse/search stdlib | Good enough; keep current rewrite implementation |
| 🟢 | Structure | Module tree from active file | Module tree from active file | Good enough; polish only if bugs appear |
| 🟢 | Parameters | Variable/constraint browsing | Variable/constraint browsing | Good enough; polish only if bugs appear |
| 🟢 | BOM | BOM browsing with summary and source links | BOM browsing with summary and source links | Good enough; polish only if bugs appear |
| 🟡 | Logs | Dedicated logs panel with build-log workflows | Dedicated logs panel exists | Wire missing extension entry points and cross-links |
| 🟡 | 3D | Dedicated preview surface tied to builds | Dedicated preview surface exists | Mostly done; verify behavior and polish failure states |
| 🔴 | Layout | Real layout editor/preview | Placeholder panel | Build or embed the actual layout surface |
| 🔴 | Manufacturing | Full manufacturing/export workflow | Missing | Add manufacturing panel/workflow |
| 🔴 | Migration | Dedicated migrate tab/workflow | Missing | Add migrate entry point and UI |

## Recommended Approach

Do **not** port mainline UI code wholesale.

Use the rewrite as the source of truth and close parity by adding missing RPC
actions, panels, and VS Code contributions. The simplest path is:

1. Reuse rewrite sidebar/panel components where they already cover the capability.
2. Add only the missing backend and extension bridge actions.
3. Rebuild missing user flows in the rewrite UI instead of reviving mainline's old
   `src/ui-server` stack.
4. Treat mainline as the feature contract, not as an implementation template.

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

- Add package detail UI:
  - description/readme
  - versions
  - install/update/remove
  - imports/usage
  - package artifacts if still relevant
- Add part detail UI:
  - datasheet link
  - richer attributes
  - stock/pricing
  - footprint / 3D / image views where available
- Add build queue actions:
  - collapse/expand
  - cancel build
  - jump to logs

### 4. Restore advanced output workflows

These are still effectively missing.

- Replace the placeholder `panel-layout` with the real layout experience.
- Add manufacturing/export workflow parity.
  - Build confirmation
  - export directory selection
  - artifact selection / review
  - cost/stock review if still part of the product
- Add migrate UI parity.
- Verify 3D and logs flows work cleanly from the rewrite UI surfaces.

### 5. Close settings and status gaps

- Expand settings beyond `devPath` and `autoInstall` if the rewrite is replacing the shipped extension.
- Expose source/mode/version/health clearly in the UI.
- Make restart/failure recovery obvious from the sidebar and panel surfaces.

### 6. Remove parity-risk dead ends

- Delete placeholder or unused surfaces that are not part of the final parity story.
- Do not keep duplicate ways to do the same thing unless mainline users rely on them.
- Prefer one good rewrite-native path per user task.

## Suggested Delivery Order

1. New project and target-management flows
2. File explorer actions
3. Package detail, part detail, build queue actions
4. Real layout panel
5. Manufacturing and migration workflows
6. Final polish on settings, health, and 3D/log cross-links

## Done Definition

The rewrite reaches parity when a user can do all of the following without
falling back to mainline:

- discover or create a project from the extension UI
- choose and manage build targets
- build, cancel builds, and inspect logs
- open KiCad, 3D, and layout outputs
- browse and manage project files
- browse/install/update/remove packages with enough detail to make decisions
- search/install/remove parts with enough detail to make decisions
- inspect stdlib, structure, parameters, and BOM
- export manufacturing data
- run migration workflows

## Notes

- The rewrite already covers more sidebar parity than the old `SIDEBAR_PARITY_PLAN.md`
  claimed. The remaining work is now mostly about **workflow completeness** and
  **extension-level affordances**, not basic panel presence.
- If a mainline feature is redundant with a cleaner rewrite-native flow, match the
  **user outcome** and delete the duplicate path.
