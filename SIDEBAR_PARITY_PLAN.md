# Sidebar Parity Plan: `atopile_extension` vs `atopile` (mainline)

## Repos

- **Mainline:** `/Users/rallen/git/atopile` — the current shipping version
- **Extension rewrite:** `/Users/rallen/git/atopile_extension` — major rewrite of the vscode extension/ui/backend

Run Claude Code from `/Users/rallen/git` to have access to both worktrees simultaneously.

Before making any changes, review [`src/EXTENSION_ARCHITECTURE.md`](src/EXTENSION_ARCHITECTURE.md) to understand the hub-spoke WebSocket architecture in the extension rewrite. It differs significantly from mainline's `vscode.postMessage` approach — all state flows through the hub, not the VS Code extension host.

## Differences

| Status | Feature | Mainline (`atopile`) | Extension Rewrite (`atopile_extension`) |
|---|---|---|---|
| ✅ | **Header** | Logo + "atopile" + version badge + settings gear (with dropdown for atopile source, local path, parallel builds, health indicator) | Logo + "atopile" only. No settings, no version, no health indicator |
| 🟡 | **Project/Target selector** | Custom combobox with fuzzy search, keyboard nav, path display, "New Project"/"New Build" buttons | Simple `<Select>` dropdowns, no search, no create |
| ✅ | **Action buttons** | Single row: Build \| KiCad \| 3D \| Layout \| Manufacture (with dividers) | Two buttons: "Build" + "Developer" |
| ✅ | **Tabbed panels** | 7 tabs: Files, Packages, Parts, Lib, Struct, Params, BOM — with responsive icon-only mode, tooltips, loading spinners, badges | **None** — no tabs at all |
| 🟡 | **File Explorer** | Full tree with lazy-loading, context menu (rename/delete/create/duplicate) | **Missing** |
| ✅ | **Packages panel** | Browse/install/uninstall packages, with detail slide-over panel | Browse/Project tabs, install/remove, search, version/update indicators. No detail slide-over yet. |
| ✅ | **Parts Search** | Component library search with detail view | Find Parts (debounced JLCPCB search) / Project tabs, install/uninstall, stock/price display. No detail slide-over yet. |
| ✅ | **Standard Library** | Browse stdlib modules | Items grouped by type (interface/module/component/trait), expandable cards with description, usage code, recursive children tree. Created `atopile.server.stdlib` to introspect STDLIB_ALLOWLIST via TypeGraph. |
| ✅ | **Structure panel** | Module/class tree from active file | Recursive module tree for active .ato file, type icons, spec display, refresh button. Tracks active editor via `setActiveFile` action. |
| ✅ | **Variables panel** | Parameters/constraints display | Tree view with table format (Name/Spec/Actual/Status), status icons, recursive filtering, auto-refresh after builds. |
| ✅ | **BOM panel** | Bill of materials table | Summary bar (parts/qty/cost/out-of-stock warnings), expandable component rows with type badges (R/C/L/IC), detail grid, parameters, usage tree with go-to-source. |
| 🟡 | **Build Queue** | Collapsible, resizable (mouse drag), with collapse/expand chevron, badge count, cancel button | Resizable (pointer drag), always shown, no collapse toggle, no cancel |
| ✅ | **Disconnected state** | Full overlay with troubleshooting steps, Discord link, restart button (5s grace period) | Simple "Connecting..." with spinner (no overlay) |
| | **Package detail panel** | Slide-over with full description, versions list, dependencies, import statements, readme | **Missing** |
| | **Parts detail panel** | Slide-over with datasheet link, all attributes, price tiers, stock history, footprint preview | **Missing** |
| | **Manufacturing wizard** | Slide-over panel for BOM export, manufacturer selection, order flow | **Missing** |
| | **Connection status** | Green/red dot button in header showing "Connected"/"Disconnected" | Not shown |
| ✅ | **Settings** | Gear icon dropdown: atopile version selector, local/release toggle, path input, browse button, parallel builds slider, health status | **Missing entirely** |
| | **New Project form** | Full form: name, location (browse), license selector, description | **Missing** |
| | **New Target form** | Full form: name, entry point (with autocomplete from modules), validation | **Missing** |

## Implementation Notes (Sidebar Panel Port)

### What was done

**Infrastructure (hub/core/extension):**
- Added 7 new state keys to `StoreState` in `types.ts` with full type definitions for all panel data
- Hub `webviewWebSocketServer.ts`: unknown actions now forward to core (instead of `console.warn`); added `setActiveFile` local action storing `activeFilePath` in `projectState`
- Hub `coreWebSocketClient.ts`: routes 7 new state keys from core into the store
- Core `websocket.py`: 11 new dispatch cases (`getPackagesSummary`, `installPackage`, `removePackage`, `getStdlib`, `getStructure`, `searchParts`, `getInstalledParts`, `installPart`, `uninstallPart`, `getVariables`, `getBom`) — all domain calls wrapped in `asyncio.to_thread()`
- Extension `extension.ts`: `onDidChangeActiveTextEditor` listener sends `setActiveFile` to hub
- Created `atopile/server/stdlib.py` — introspects `STDLIB_ALLOWLIST` via TypeGraph, returns `StdLibItem` objects (was missing, caused startup crash)

**Panel components (6 new panels + CSS):**
- `LibraryPanel.tsx` + CSS
- `PackagesPanel.tsx` + CSS
- `PartsPanel.tsx` + CSS
- `StructurePanel.tsx` + CSS
- `ParametersPanel.tsx` + CSS
- `BOMPanel.tsx` + CSS
- `sidebar/main.tsx`: updated `panelMap` to pass `projectRoot` and `selectedTarget` props

### What's still missing vs mainline
- Detail slide-over panels (package detail, part detail)
- File explorer context menu (rename/delete/create/duplicate)
- New Project / New Target forms
- Connection status indicator in header
- Build queue collapse toggle and cancel button
