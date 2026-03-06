# File Watcher Proposal

## Summary

Use the current extension-side watcher for the short term, but fix the refresh pipeline in the webview so nested lazy-loaded directories survive watcher-driven reloads. This is a low-risk bridge to the `feature/extension-rewrite` architecture, where file watching moves out of the sidebar provider and into a dedicated backend/store flow.

## Findings: `main`

- The current watcher registration in `src/vscode-atopile/src/providers/SidebarProvider.ts` already watches `**/*` under the selected project root.
- The actual regression is in `src/ui-server/src/components/FileExplorerPanel.tsx`: on `filesChanged`, the UI clears the whole tree, refetches the root, and only re-requests lazy directories that still exist in that fresh root payload.
- Nested expanded lazy directories disappear from the temporary root-only payload, so deeper paths like `build/foo/bar` are never reloaded after a watcher refresh.
- This makes create/delete/rename events appear to work at the root or first lazy boundary, but fail more than one level deep.

## Findings: PR `#1732`

- The rewrite architecture moves file watching away from ad hoc webview/provider state and into a clearer data pipeline: extension host -> hub/store -> core server.
- The concrete file-watching implementations in that branch split into:
  - `src/atopile/model/file_watcher.py`: shared native `watchdog` observer with recursive watches, filtering, debouncing, and hash-based suppression.
  - `src/atopile/model/files.py`: project file-tree scanning plus watcher-triggered rebroadcast of `projectFiles`.
- The rewrite direction is correct for long-term maintainability, but it is too invasive to cherry-pick into `main` as an “easy merge” fix.

## Implemented Patch

- Move sidebar file-tree ownership into the backend using the existing websocket channel.
- Add a dedicated selected-project watcher in `src/atopile/server/project_files.py`.
- Broadcast full `project_files_changed` payloads with `{ project_root, files }` instead of relying on the extension to reconstruct the tree.
- Update the React file explorer to subscribe via `watchProjectFiles` and render backend-pushed state directly.
- Keep `fetchFiles` alive for existing project-card callers, but source it from the same backend scanner.
- Remove sidebar-specific file-tree watching/listing code from the VS Code extension provider.

## Why This Is Easy To Merge

- No protocol changes.
- No hub/server rewrite required.
- No unrelated sidebar/package/build refactors.
- The patch is isolated to file-tree ownership and removes the duplicate extension-side watcher path.
