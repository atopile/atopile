# File Explorer Panel Specification

## Problem Statement

Cursor IDE doesn't allow an extension sidebar and the native file tree to be open simultaneously. This forces users to constantly toggle between the atopile extension panel and the file explorer, which significantly impacts workflow efficiency.

## Goal

Build a file explorer panel **inside the atopile sidebar webview** that provides a near-identical experience to VSCode's native file explorer.

---

## Decisions Made

| Question | Decision |
|----------|----------|
| **File types** | All file types (not just `.ato`/`.py`) |
| **Root scope** | Selected project root only |
| **Filtering** | No filtering initially (show everything including `.git`, `node_modules`) |
| **State persistence** | Not initially, but plan for it |
| **Tab position** | First tab on the left |
| **Implementation** | Fresh build, clone VSCode exactly |

---

## Detailed Specification

### 1. Visual Design Requirements

The file explorer should be **visually identical** to VSCode's native explorer:

#### 1.1 Tree Structure
- Indent per level: **19px** (VSCode default)
- Row height: **22px**
- Hover background: `var(--vscode-list-hoverBackground)`
- Selected background: `var(--vscode-list-activeSelectionBackground)`
- Focus outline: `var(--vscode-focusBorder)`

#### 1.2 Icons
Use `@vscode/codicons` for consistency:
- Folder closed: `codicon-folder`
- Folder open: `codicon-folder-opened`
- Chevron right: `codicon-chevron-right`
- Chevron down: `codicon-chevron-down`

For file type icons, options:
1. **Simple:** Use `codicon-file` for all files (minimal)
2. **Enhanced:** Use `vscode-icons` font (same as Material Icon Theme)
3. **Custom:** Map extensions to specific codicons:
   - `.ato` → custom atopile icon
   - `.py` → `codicon-symbol-method`
   - `.json` → `codicon-json`
   - `.md` → `codicon-markdown`
   - `.yaml/.yml` → `codicon-symbol-constant`

#### 1.3 Typography
- Font: `var(--vscode-font-family)`
- Font size: `13px`
- Color: `var(--vscode-foreground)`

### 2. Functional Requirements

#### 2.1 Core Features (MVP)
- [ ] Display project files in a tree structure
- [ ] Expand/collapse folders
- [ ] Click file to open in editor
- [ ] Show file icons based on extension
- [ ] Highlight currently open file
- [ ] Keyboard navigation (up/down arrows, Enter to open)

#### 2.2 Enhanced Features (Phase 2)
- [ ] Right-click context menu (New File, New Folder, Rename, Delete)
- [ ] Drag and drop files/folders
- [ ] Multi-select with Ctrl/Cmd + click
- [ ] Filter/search files (Ctrl+F in explorer)
- [ ] Show git status decorations (modified, untracked, etc.)
- [ ] File decorations (badges for errors/warnings)

#### 2.3 Performance Features
- [ ] Virtual scrolling for large directories (only render visible items)
- [ ] Lazy loading of subdirectories (load children on expand)
- [ ] Debounced file system watching

### 3. Architecture

#### 3.1 Frontend (React)

```
src/ui-server/src/components/
├── FileExplorerPanel/
│   ├── FileExplorerPanel.tsx      # Main panel component
│   ├── FileExplorerPanel.css      # Styles
│   ├── FileTreeNode.tsx           # Individual tree node
│   ├── FileIcon.tsx               # File icon resolver
│   ├── useFileTree.ts             # State management hook
│   ├── useVirtualScroll.ts        # Virtual scrolling hook
│   └── types.ts                   # TypeScript interfaces
```

#### 3.2 Backend Endpoints Needed

| Endpoint | Method | Description |
|----------|--------|-------------|
| `listDirectory` | action | List files in a directory |
| `watchDirectory` | subscribe | Subscribe to file changes |
| `createFile` | action | Create new file |
| `createFolder` | action | Create new folder |
| `renameFile` | action | Rename file/folder |
| `deleteFile` | action | Delete file/folder |
| `moveFile` | action | Move file/folder |

#### 3.3 Data Flow

```
Backend (FastAPI) ──WebSocket──► Store (Zustand) ──► FileExplorerPanel (React)
       │                                                      │
       │                                                      ▼
       │                                              User clicks file
       │                                                      │
       │◄─────── action('openFile', {path}) ──────────────────┘
```

### 4. UI Integration

#### 4.1 Tab Integration
Add "Files" as a new tab in the existing tab bar:

```tsx
<button
  className={`tab-button ${activeTab === 'files' ? 'active' : ''}`}
  onClick={() => setActiveTab('files')}
  title="Files"
>
  Files
</button>
```

#### 4.2 Panel Position Options

**Option A: New Tab (Recommended)**
- Add as sibling to Packages, Parts, Structure tabs
- Clean integration with existing UI

**Option B: Collapsible Section**
- Add above or below Projects section
- Always visible, can be collapsed

**Option C: Dedicated Panel**
- Replace the entire left side with file explorer
- Toggle between "Project" view and "Files" view

### 5. Implementation Phases

#### Phase 1: Basic File Tree (1-2 days)
1. Create `FileExplorerPanel` component
2. Add backend `listDirectory` endpoint
3. Implement basic tree with expand/collapse
4. Wire up file click to open in editor
5. Add as new tab in sidebar

#### Phase 2: Visual Polish (1 day)
1. Match VSCode styling exactly
2. Add proper file type icons
3. Implement hover/selection states
4. Add current file highlighting

#### Phase 3: File System Operations (2-3 days)
1. Add context menu
2. Implement create/rename/delete
3. Add file watching for live updates

#### Phase 4: Advanced Features (2-3 days)
1. Virtual scrolling
2. Git status decorations
3. Multi-select
4. Drag and drop

---

## References

- [VSCode TreeView API](https://code.visualstudio.com/api/extension-guides/tree-view)
- [VSCode File Explorer Sample](https://github.com/microsoft/vscode-extension-samples/blob/main/tree-view-sample/src/fileExplorer.ts)
- [VSCode Codicons](https://microsoft.github.io/vscode-codicons/)
- [React Icons - VSC Set](https://react-icons.github.io/react-icons/icons/vsc/)
- [VSCode Theme Colors](https://code.visualstudio.com/api/references/theme-color)

---

## Implementation Status

### Completed
- [x] Created `FileExplorerPanel.tsx` - VSCode-styled React component
- [x] Created `FileExplorerPanel.css` - VSCode CSS variable theming
- [x] Added "Files" tab as first tab in Sidebar
- [x] Updated backend to support `include_all=true` parameter
- [x] Updated API client to pass `include_all` flag
- [x] Component fetches files via `/api/files` endpoint

### Files Modified
- `src/ui-server/src/components/FileExplorerPanel.tsx` (new)
- `src/ui-server/src/components/FileExplorerPanel.css` (new)
- `src/ui-server/src/components/Sidebar.tsx` (added Files tab)
- `src/ui-server/src/api/client.ts` (added `includeAll` param)
- `src/atopile/server/core/projects.py` (added `include_all` param)
- `src/atopile/server/domains/projects.py` (added `include_all` param)
- `src/atopile/server/routes/projects.py` (added query param)

### TODO
- [ ] Add refresh button to refetch files
- [ ] Keyboard navigation (arrow keys)
- [ ] Context menu (right-click)
- [ ] Persist expanded state across sessions
- [ ] Add filter toggle to hide/show dotfiles
