# Sidebar Parity Plan: `atopile_extension` vs `atopile` (mainline)

## Repos

- **Mainline:** `/Users/rallen/git/atopile` — the current shipping version
- **Extension rewrite:** `/Users/rallen/git/atopile_extension` — major rewrite of the vscode extension/ui/backend

Run Claude Code from `/Users/rallen/git` to have access to both worktrees simultaneously.

Before making any changes, review [`src/EXTENSION_ARCHITECTURE.md`](src/EXTENSION_ARCHITECTURE.md) to understand the hub-spoke WebSocket architecture in the extension rewrite. It differs significantly from mainline's `vscode.postMessage` approach — all state flows through the hub, not the VS Code extension host.

## Differences

| Feature | Mainline (`atopile`) | Extension Rewrite (`atopile_extension`) |
|---|---|---|
| **Header** | Logo + "atopile" + version badge + settings gear (with dropdown for atopile source, local path, parallel builds, health indicator) | Logo + "atopile" only. No settings, no version, no health indicator |
| **Project selector** | Custom combobox with fuzzy search, keyboard nav, path display, "New Project" button | Simple `<Select>` dropdown, no search, no create |
| **Target selector** | Custom combobox with keyboard nav, entry point info, "New Build" button | Simple `<Select>` dropdown, no search, no create |
| **Action buttons** | Single row: Build \| KiCad \| 3D \| Layout \| Manufacture (with dividers) | Two buttons: "Build" + "Developer" |
| **Tabbed panels** | 7 tabs: Files, Packages, Parts, Lib, Struct, Params, BOM — with responsive icon-only mode, tooltips, loading spinners, badges | **None** — no tabs at all |
| **File Explorer** | Full tree with lazy-loading, context menu (rename/delete/create/duplicate) | **Missing** |
| **Packages panel** | Browse/install/uninstall packages, with detail slide-over panel | **Missing** |
| **Parts Search** | Component library search with detail view | **Missing** |
| **Standard Library** | Browse stdlib modules | **Missing** |
| **Structure panel** | Module/class tree from active file | **Missing** |
| **Variables panel** | Parameters/constraints display | **Missing** |
| **BOM panel** | Bill of materials table | **Missing** |
| **Build Queue** | Collapsible, resizable (mouse drag), with collapse/expand chevron, badge count, cancel button | Resizable (pointer drag), always shown, no collapse toggle, no cancel |
| **Build items** | Same general structure — expandable, status-colored left border, stage progress | Same — nearly identical visually |
| **Disconnected state** | Full overlay with troubleshooting steps, Discord link, restart button (5s grace period) | Simple "Connecting..." with spinner (no overlay) |
| **Detail panels** | Package detail, Parts detail, Manufacturing wizard slide in as overlay panels | **Missing** |
| **Connection status** | Green/red dot button in header showing "Connected"/"Disconnected" | Not shown |
| **Settings** | Gear icon dropdown: atopile version selector, local/release toggle, path input, browse button, parallel builds slider, health status | **Missing entirely** |
| **New Project form** | Full form: name, location (browse), license selector, description | **Missing** |
| **New Target form** | Full form: name, entry point (with autocomplete from modules), validation | **Missing** |
