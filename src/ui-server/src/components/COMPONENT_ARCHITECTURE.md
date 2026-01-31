# Project/Package Component Architecture

## Core Principle

**A package is a project with additional metadata.** All display components should reflect this hierarchy:

```
Project (base)
└── Package (extends Project with: publisher, version, install status, registry info)
```

Both should use the **same components** with feature flags to enable/disable functionality based on context.

---

## Building Blocks

### 1. ProjectCard (Primary Container)

The single source of truth for displaying any project or package.

```
┌─────────────────────────────────────────────────────────┐
│ ProjectHeader                                           │
├─────────────────────────────────────────────────────────┤
│ ProjectDescription                                      │
├─────────────────────────────────────────────────────────┤
│ PackageInstallBar (optional)                            │
├─────────────────────────────────────────────────────────┤
│ ProjectContent (expandable)                             │
│  ├── UsageExamples (optional)                           │
│  ├── MetadataBar (optional)                             │
│  ├── ModuleExplorer (optional)                          │
│  ├── BuildsCard                                         │
│  ├── FileExplorer (optional)                            │
│  └── DependencyCard                                     │
└─────────────────────────────────────────────────────────┘
```

### 2. Feature Flags

| Flag | Description | Default |
|------|-------------|---------|
| `editable` | Allow editing name, description, builds | `false` |
| `showBuildControls` | Show play/stop buttons, status indicators | `false` |
| `showInstallBar` | Show version selector + install button | `false` |
| `showUsageExamples` | Show import/usage code blocks | `false` |
| `showMetadata` | Show downloads, license, version count | `false` |
| `showModuleExplorer` | Show module structure tree | `false` |
| `showFileExplorer` | Show file tree | `false` |
| `showPublisher` | Show publisher badge | `false` |
| `compact` | Minimal header-only view (for dependency lists) | `false` |
| `expandable` | Allow expanding to show full content | `true` |

### 3. Presets (Convenience Configurations)

```typescript
const PRESETS = {
  // Local project in Projects panel
  localProject: {
    editable: true,
    showBuildControls: true,
    showModuleExplorer: true,
    showFileExplorer: true,
    showInstallBar: false,
    showUsageExamples: false,
    showMetadata: false,
    showPublisher: false,
  },

  // Package in Packages panel
  packageExplorer: {
    editable: false,
    showBuildControls: false,
    showModuleExplorer: false,  // Package may not be installed locally
    showFileExplorer: false,
    showInstallBar: true,
    showUsageExamples: true,
    showMetadata: true,
    showPublisher: true,
  },

  // Dependency in a project's dependency list (collapsed)
  dependencyCompact: {
    compact: true,
    expandable: true,
    editable: false,
    showBuildControls: false,
    // When expanded, switches to dependencyExpanded preset
  },

  // Dependency when expanded (same as packageExplorer but no install bar)
  dependencyExpanded: {
    editable: false,
    showBuildControls: false,
    showModuleExplorer: false,  // TODO: Enable when backend populates builds in PackageDetails
    showFileExplorer: false,
    showInstallBar: false,  // Already installed as dependency
    showUsageExamples: true,
    showMetadata: true,
    showPublisher: true,
  },
}
```

---

## Component Hierarchy

### Atomic Components (Smallest Units)

| Component | Purpose | Reused In |
|-----------|---------|-----------|
| `CopyableCodeBlock` | Code with syntax highlighting + copy button | UsageExamples, anywhere code is shown |
| `VersionBadge` | Displays version with optional "latest" tag | Header, InstallBar, DependencyItem |
| `PublisherBadge` | Shows publisher with "official" styling for atopile | Header |
| `StatusIndicator` | Error/warning/success counts | Header, BuildNode |
| `ExpandChevron` | Expand/collapse toggle | All expandable components |

### Composite Components (Built from Atoms)

| Component | Contains | Purpose |
|-----------|----------|---------|
| `ProjectHeader` | Icon, Name, PublisherBadge?, StatusIndicator?, BuildButton? | Top row of any project/package |
| `ProjectDescription` | Text, edit input | Description row |
| `PackageInstallBar` | ProjectSelector, VersionSelector, InstallButton | Install UI for packages |
| `UsageExamples` | CopyableCodeBlock × 2 | Import + usage code |
| `MetadataBar` | Downloads, versions, license | Package stats |

### Container Components (Aggregate Others)

| Component | Contains | Purpose |
|-----------|----------|---------|
| `ProjectCard` | All of the above based on flags | Main display component |
| `BuildsCard` | BuildNode[] | List of build targets |
| `DependencyCard` | DependencyItem[] | List of dependencies |
| `FileExplorer` | FileNode[] | File tree |
| `ModuleExplorer` | ModuleNode[] | Module structure per build |

---

## View Contexts

### 1. Projects Panel (Local Projects)

```
┌─ ProjectCard (preset: localProject) ─────────────────────┐
│ [v] [Layers] MyProject              [errors] [▶]         │
│     A hardware project for...                            │
├──────────────────────────────────────────────────────────┤
│ [v] Explorer                                             │
│     └── default → App                                    │
│ [v] Builds (2)                                           │
│     ├── default    [entry.ato:App]    [▶]                │
│     └── test       [test.ato:Test]    [▶]                │
│ [v] Files                                                │
│     ├── src/                                             │
│     └── ato.yaml                                         │
│ [v] Dependencies (3)                                     │
│     ├── atopile/generics     0.2.1  [dropdown] [x]       │
│     ├── atopile/rp2040       1.0.0  [dropdown] [x]       │
│     └── vendor/sensor        2.1.0  [dropdown] [x]       │
└──────────────────────────────────────────────────────────┘
```

**Features enabled**: editable, showBuildControls, showModuleExplorer, showFileExplorer

### 2. Packages Panel (Registry Packages)

```
┌─ ProjectCard (preset: packageExplorer) ──────────────────┐
│ [v] [Package] rp2040-driver              atopile    [↗]  │
│     RP2040 microcontroller with USB and power            │
│     [quickstart ▾] [1.2.0 ▾] [Install]                   │
├──────────────────────────────────────────────────────────┤
│ ┌─ Import ──────────────────────────────────── [copy] ─┐ │
│ │ from "atopile/rp2040/rp2040.ato" import RP2040      │ │
│ └──────────────────────────────────────────────────────┘ │
│ ┌─ Usage ───────────────────────────────── [copy][open]┐ │
│ │ module MyModule:                                     │ │
│ │     mcu = new RP2040                                 │ │
│ └──────────────────────────────────────────────────────┘ │
│ [downloads] 1.2k  [versions] 5  [license] MIT            │
│ [v] Builds (1)                                           │
│     └── example    [example.ato:Example]                 │
│ [v] Dependencies (2)                                     │
│     ├── atopile/generics     0.2.1                       │
│     └── atopile/power        1.0.0                       │
└──────────────────────────────────────────────────────────┘
```

**Features enabled**: showInstallBar, showUsageExamples, showMetadata, showPublisher

### 3. Dependency List Item (Compact)

```
┌─ DependencyItem (compact) ───────────────────────────────┐
│ [>] [Package] generics    by atopile    0.2.1   [x]      │
└──────────────────────────────────────────────────────────┘
```

**Minimal view**: Just name, publisher, version, remove button

### 4. Dependency Expanded (Same as Package, No Install)

```
┌─ DependencyItem (expanded) ──────────────────────────────┐
│ [v] [Package] generics    by atopile    0.2.1   [x]      │
├──────────────────────────────────────────────────────────┤
│ ┌─ Import ──────────────────────────────────── [copy] ─┐ │
│ │ from "atopile/generics/..." import Resistor          │ │
│ └──────────────────────────────────────────────────────┘ │
│ [downloads] 5.2k  [versions] 12  [license] MIT           │
│ [v] Builds (1)                                           │
│ [v] Dependencies (1)                                     │
└──────────────────────────────────────────────────────────┘
```

**Same as packageExplorer but**: No install bar (already installed)
**TODO**: Enable Module Explorer when backend populates `builds` in PackageDetails

---

## Data Model

```typescript
interface ProjectData {
  // Core (always present)
  id: string
  name: string
  root: string
  builds: BuildTarget[]

  // Optional project metadata
  summary?: string
  description?: string

  // Package metadata (present when type === 'package')
  type?: 'project' | 'package'
  publisher?: string
  version?: string
  latestVersion?: string
  homepage?: string
  license?: string
  downloads?: number
  installedIn?: string[]  // Which projects have this as a dependency
}

interface ProjectCardProps {
  project: ProjectData

  // Feature flags (or use preset)
  preset?: 'localProject' | 'packageExplorer' | 'dependencyCompact' | 'dependencyExpanded'

  // Or individual flags for fine-grained control
  editable?: boolean
  showBuildControls?: boolean
  showInstallBar?: boolean
  showUsageExamples?: boolean
  showMetadata?: boolean
  showModuleExplorer?: boolean
  showFileExplorer?: boolean
  showPublisher?: boolean
  compact?: boolean
  expandable?: boolean

  // State
  isExpanded?: boolean
  onExpandChange?: (expanded: boolean) => void

  // Callbacks
  onBuild?: (buildId: string) => void
  onInstall?: (version: string, targetProject: string) => void
  onEdit?: (updates: Partial<ProjectData>) => void
  // ... etc
}
```

---

## Implementation Plan

### Phase 1: Extract Shared Utilities
```
src/ui-server/src/utils/
├── codeHighlight.tsx      # highlightAtoCode(), CopyableCodeBlock
├── packageUtils.ts        # formatDownloads(), compareVersions(), etc.
└── versionUtils.ts        # Version comparison, formatting
```

### Phase 2: Create Atomic Components
```
src/ui-server/src/components/shared/
├── VersionBadge.tsx
├── PublisherBadge.tsx
├── StatusIndicator.tsx
├── ExpandChevron.tsx
└── CopyableCodeBlock.tsx
```

### Phase 3: Refactor ProjectCard with Presets
- Add `preset` prop to ProjectCard
- Implement feature flags
- Remove conditional logic in favor of flag-based rendering

### Phase 4: Unify DependencyItem
- When collapsed: compact view (just header)
- When expanded: render ProjectCard with `dependencyExpanded` preset
- Remove duplicate ExpandedDependencyContent

### Phase 5: Delete Dead Code
- Remove PackageCard.tsx
- Remove ProjectNode.tsx
- Consolidate CSS files

---

## Editability Matrix

This table defines which UI elements are editable in each context. **Packages and dependencies are always read-only** - they represent installed code that shouldn't be modified from the UI.

### Element-Level Editability

| UI Element | Local Project | Package | Dependency (Compact) | Dependency (Expanded) |
|------------|---------------|---------|---------------------|----------------------|
| **Header** |
| Project/Package Name | ❌ Static | ❌ Static | ❌ Static | ❌ Static |
| Description | ✅ Editable | ❌ Static | — | ❌ Static |
| Expand/Collapse | ✅ | ✅ | ✅ | ✅ |
| **Build Targets** |
| Build Name | ✅ Editable | ❌ Static | — | ❌ Static |
| Entry Point | ✅ Editable | ❌ Static | — | ❌ Static |
| Play/Build Button | ✅ Visible | ❌ Hidden | — | ❌ Hidden |
| Stop/Cancel Button | ✅ Visible | ❌ Hidden | — | ❌ Hidden |
| Open .ato Button | ✅ Visible | ✅ Visible | — | ✅ Visible |
| Open KiCad Button | ✅ Visible | ❌ Hidden | — | ❌ Hidden |
| Open Layout Button | ✅ Visible | ❌ Hidden | — | ❌ Hidden |
| Open 3D Button | ✅ Visible | ❌ Hidden | — | ❌ Hidden |
| Delete Build Button | ✅ Visible | ❌ Hidden | — | ❌ Hidden |
| Add Build Button | ✅ Visible | ❌ Hidden | — | ❌ Hidden |
| Status Indicators | ✅ Visible | ❌ Hidden | — | ❌ Hidden |
| **Dependencies Section** |
| Version Selector | ✅ Dropdown | — | ❌ Static | ❌ Static |
| Remove Button | ✅ Visible | — | ❌ Hidden | ❌ Hidden |
| Add Dependency | ✅ Visible | — | ❌ Hidden | ❌ Hidden |
| **Package-Specific** |
| Install Bar | ❌ Hidden | ✅ Visible | ❌ Hidden | ❌ Hidden |
| Usage Examples | ❌ Hidden | ✅ Visible | — | ✅ Visible |
| Metadata (downloads, license) | ❌ Hidden | ✅ Visible | — | ✅ Visible |
| Publisher Badge | ❌ Hidden | ✅ Visible | ✅ Visible | ✅ Visible |
| **Files Section** |
| File Tree | ✅ Visible | ❌ Hidden | — | ❌ Hidden |
| Open File Click | ✅ Active | ❌ Disabled | — | ❌ Disabled |
| **Module Explorer** |
| Module Tree | ✅ Visible | ❌ Hidden | — | ❌ Hidden (TODO) |

### Legend

- ✅ **Editable/Visible**: Element is shown and interactive
- ❌ **Static**: Element is shown but not editable (display only)
- ❌ **Hidden**: Element is not rendered at all
- **—**: Not applicable for this context (e.g., compact view has no content)

### Implementation Notes

1. **Local Projects**: Full editing capabilities. Users can modify builds, manage dependencies, and trigger builds.

2. **Packages (in Packages Panel)**: Read-only view of registry packages. Shows install UI, usage examples, and metadata. No build controls since packages aren't built locally.

3. **Dependencies (Compact)**: Minimal row showing name, publisher, version. Clicking expands to show full details.

4. **Dependencies (Expanded)**: Same as package view but without install bar (already installed). Shows usage examples and metadata to help users understand how to use the dependency.

### Code Implementation

The `readOnly` prop controls most editability:

```typescript
// In ProjectCard
{!readOnly && (
  <button className="build-btn" onClick={handleBuild}>
    <Play size={12} />
  </button>
)}

// In BuildNode
{!readOnly && (
  <div className="build-card-actions">
    {/* Action buttons */}
  </div>
)}

// In DependencyCard
{!readOnly ? (
  <select value={version} onChange={handleVersionChange}>
    {versions.map(v => <option key={v}>{v}</option>)}
  </select>
) : (
  <span className="version-display">{version}</span>
)}
```

---

## Benefits

1. **Single Source of Truth**: One component (ProjectCard) handles all views
2. **Consistent UX**: Same content shown the same way everywhere
3. **Easy to Extend**: Add new preset for new contexts
4. **Less Code**: ~1000 lines of duplication removed
5. **Easier Maintenance**: Fix once, works everywhere

---

## Migration Path

| Current | After |
|---------|-------|
| `<PackageCard project={p} />` | `<ProjectCard project={p} preset="packageExplorer" />` |
| `<ProjectNode project={p} />` | `<ProjectCard project={p} preset="localProject" />` |
| `<ExpandedDependencyContent dep={d} />` | `<ProjectCard project={d} preset="dependencyExpanded" />` |
| `<DependencyItem dep={d} />` | `<ProjectCard project={d} preset="dependencyCompact" expandable />` |

---

## Implementation Status

**Last Updated:** 2026-01-23

### What's Done ✅

| Task | Status | Notes |
|------|--------|-------|
| **Phase 1: Extract Shared Utilities** | ✅ Complete | |
| `codeHighlight.tsx` | ✅ | `highlightAtoCode()`, `generateImportStatement()`, `generateUsageExample()` |
| `packageUtils.ts` | ✅ | `formatDownloads()`, `compareVersionsDesc()`, `isInstalledInProject()` |
| **Phase 2: Create Atomic Components** | ✅ Complete | Located in `components/shared/` |
| `CopyableCodeBlock.tsx` | ✅ | Reusable code display with copy button |
| `MetadataBar.tsx` | ✅ | Downloads, versions, license display |
| `PublisherBadge.tsx` | ✅ | Publisher display with "official" styling |
| `VersionSelector.tsx` | ✅ | Dropdown for version selection |
| **Phase 3: ProjectCard Unification** | ✅ Complete | |
| Projects use ProjectCard | ✅ | `ProjectsPanel` uses `ProjectCard` for local projects |
| Packages use ProjectCard | ✅ | `ProjectsPanel` uses `ProjectCard` with `readOnly=true` |
| `readOnly` prop for editability | ✅ | Controls build buttons, edit fields, remove buttons |
| Preset system | ✅ | `preset` prop with `localProject`, `packageExplorer`, `dependencyExpanded` |
| Feature flags | ✅ | `showInstallBar`, `showBuildControls`, `showUsageExamples`, `showMetadata`, `showModuleExplorer`, `showFileExplorer` |
| **Phase 4: Unify DependencyItem** | ✅ Complete | |
| Dependencies use ProjectCard | ✅ | `DependencyCard` uses `ProjectCard` with `preset="dependencyExpanded"` |
| **Phase 5: Delete Dead Code** | ✅ Complete | |
| Remove PackageCard.tsx | ✅ | Deleted |
| Remove ProjectNode.tsx | ✅ | Deleted |
| Remove ExpandedDependencyContent | ✅ | Replaced with ProjectCard |

### Current Architecture ✅

```
ProjectsPanel
├── Projects view: uses ProjectCard (preset="localProject")
└── Packages view: uses ProjectCard (preset="packageExplorer")

DependencyCard (inside ProjectCard)
├── DependencyItem (compact header)
└── ProjectCard (preset="dependencyExpanded")  ← NOW UNIFIED
    ├── MetadataBar
    ├── CopyableCodeBlock × 2 (import/usage)
    ├── BuildsCard
    └── nested DependencyCard
```

### Code Locations

| Component | File | Uses ProjectCard? |
|-----------|------|-------------------|
| Projects Panel | `ProjectsPanel.tsx` | ✅ Yes (`preset="localProject"`) |
| Packages Panel | `ProjectsPanel.tsx` (filterType="packages") | ✅ Yes (`preset="packageExplorer"`) |
| Dependency List | `DependencyCard.tsx` | ✅ Yes (compact header + ProjectCard) |
| Expanded Dependency | `DependencyCard.tsx` | ✅ Yes (`preset="dependencyExpanded"`) |

### Data Conversions

| Source | Target | Location | Notes |
|--------|--------|----------|-------|
| `ProjectDependency` | `Project` | `DependencyCard.tsx` | `dependencyToProject(dep)` uses `installedPath` from backend |
| `PackageBuildTarget[]` | `BuildTarget[]` | `ProjectCard.tsx` | Inline conversion for packages |

---

## Dependency Data Lifecycle (Comprehensive Trace)

### Where Packages Live on Disk

```
my-project/
├── ato.yaml                      # Lists direct dependencies
└── .ato/
    └── modules/
        └── {publisher}/{package}/  # e.g., adi/ad1938
            ├── ato.yaml           # Package config (builds, version)
            └── *.ato              # Source files
```

### When Packages Get Installed

| Command | Effect |
|---------|--------|
| `ato build` | Auto-installs missing deps before building |
| `ato sync` | Explicitly installs/updates all deps |
| `ato add <pkg>` | Adds to ato.yaml and installs |
| `git clone` | **Nothing** - user must build/sync first |

---

### Data Fetch Trace for Expanded Dependency

When a dependency is clicked to expand in the UI, here's what happens for each piece of data:

#### 1. Dependency List (shown before expand)

```
TRIGGER: Project card expands, calls onProjectExpand(project.root)
         └─> handleProjectExpand() in useSidebarHandlers.ts

BACKEND ACTION: fetchDependencies
  └─> src/atopile/server/domains/actions.py (line ~830)
      └─> _build_dependencies() in projects.py
          ├─ Reads ato.yaml for direct deps
          ├─ Scans .ato/modules/ for installed packages
          ├─ Checks each dep path exists: modules_root / identifier
          └─ Returns DependencyInfo[] with installed_path set

STATE UPDATE: server_state.set_project_dependencies(projectRoot, deps)
  └─> Broadcasts via WebSocket

FRONTEND: projectDependencies[projectRoot] in store
  └─> DependencyCard receives dependencies prop
      └─> Each dep has installedPath from backend
```

**Key Fields in DependencyInfo:**
- `identifier`: e.g., "adi/ad1938"
- `installed_path`: e.g., "/Users/foo/project/.ato/modules/adi/ad1938" (NEW)
- `version`, `name`, `publisher`, etc.

#### 2. Files (✅ WORKS)

```
TRIGGER: DependencyItem.handleClick() when expanding
  └─> onProjectExpand(dependencyAsProject.root)
      └─> dependencyAsProject.root = dependency.installedPath || dependency.identifier

BACKEND ACTION: fetchFiles
  └─> src/atopile/server/domains/actions.py (line ~800)
      └─> Reads file tree from projectRoot path

STATE UPDATE: server_state.set_project_files(projectRoot, files)
  └─> Broadcasts via WebSocket

FRONTEND: projectFiles[projectRoot] in store
  └─> Passed to ProjectCard via projectFilesByRoot prop
      └─> FileExplorer receives projectFiles prop
```

**Why it works:** The path resolution is correct and fetchFiles works.

#### 3. Builds (❌ MAY NOT WORK)

```
TRIGGER: DependencyItem.handleClick() when expanding
  └─> onProjectExpand(dependencyAsProject.root)

BACKEND ACTION: fetchBuilds (line 860 in actions.py)
  └─> Reads ato.yaml from projectRoot
      └─> ProjectConfig.from_path(project_path)
      └─> Returns builds[] with {id, name, entry, root}

STATE UPDATE: server_state.set_project_builds(projectRoot, builds)
  └─> Broadcasts via WebSocket

FRONTEND: projectBuilds[projectRoot] in store
  └─> Passed to ProjectCard via projectBuildsByRoot prop
      └─> ProjectCard computes: localBuilds = projectBuildsByRoot[project.root]
          └─> BuildsCard receives builds prop
          └─> ProjectExplorerCard receives builds prop
```

**Potential Issues:**
1. **Key mismatch**: The `projectRoot` used in fetch might differ from `project.root` in lookup
2. **installedPath not set**: If backend doesn't return `installed_path`, `dependency.installedPath` is undefined, and `project.root` becomes `dependency.identifier` (not a valid path)
3. **State not broadcast**: Check if `set_project_builds` actually broadcasts

#### 4. Explorer/Module Tree (❌ MAY NOT WORK)

```
TRIGGER: ProjectExplorerCard mounts with builds
  └─> For each build, calls getModuleChildren when expanded

BACKEND ACTION: getModuleChildren (line 898 in actions.py)
  └─> Requires valid projectRoot and entryPoint
      └─> Parses .ato files to build module tree

FRONTEND: ModuleTree renders children

**Depends on:** Builds being loaded first (provides entry points)
```

**Why it might fail:** If builds array is empty, no module children are fetched.

#### 5. Metadata (downloads, license, versions)

```
TRIGGER: ProjectCard expanded with readOnly=true
  └─> useEffect fetches packageDetails

BACKEND ACTION: getPackageDetails
  └─> Fetches from REMOTE REGISTRY (packages.atopileapi.com)
      └─> Returns downloads, license, versions, etc.

FRONTEND: packageDetails state in ProjectCard
  └─> MetadataBar receives downloads, license, versionCount
```

**Note:** This is the only data that requires network fetch. All other data should be local.

---

### Debug Checklist

When dependency expansion doesn't show data:

| Check | How to Verify |
|-------|---------------|
| 1. Is `installedPath` set? | Console log `dependency` in DependencyItem |
| 2. Is `onProjectExpand` called? | Console log in handleClick |
| 3. Is `fetchBuilds` called? | Check Network/WS tab for action message |
| 4. Does backend find ato.yaml? | Check server logs for "No ato.yaml found" |
| 5. Is state broadcast? | Check WS message for `projectBuilds` key |
| 6. Is key correct? | Compare `projectRoot` in fetch vs `project.root` in lookup |

### Known Gaps & Likely Issues

1. **Backend not restarted**: After code changes, the Python server must be restarted for changes to take effect. The `fetchBuilds` action and `installedPath` field were added recently.

2. **installedPath undefined**: If `dependency.installedPath` is undefined, `project.root` becomes `dependency.identifier` (e.g., "adi/ad1938") which is NOT a valid path. This causes:
   - `fetchBuilds({ projectRoot: "adi/ad1938" })` → fails with "Project not found"
   - `projectBuildsByRoot["adi/ad1938"]` → undefined (no data)

3. **Key mismatch between fetch and lookup**:
   - Fetch uses: `onProjectExpand(dependencyAsProject.root)`
   - Lookup uses: `projectBuildsByRoot[project.root]`
   - If `project.root` differs from what was used in fetch, lookup returns undefined

### Quick Debug Steps

Add these console.logs to trace the issue:

**In DependencyCard.tsx, `dependencyToProject()`:**
```tsx
console.log('[DEP] dependency.installedPath:', dependency.installedPath);
console.log('[DEP] computed root:', root);
```

**In DependencyItem, `handleClick()`:**
```tsx
console.log('[EXPAND] Calling onProjectExpand with:', dependencyAsProject.root);
```

**In ProjectCard.tsx, builds computation:**
```tsx
console.log('[BUILDS] project.root:', project.root);
console.log('[BUILDS] projectBuildsByRoot keys:', Object.keys(projectBuildsByRoot));
console.log('[BUILDS] localBuilds:', localBuilds);
```

### Expected vs Actual

| Field | Expected Value | If undefined, means... |
|-------|----------------|------------------------|
| `dependency.installedPath` | `/path/to/.ato/modules/adi/ad1938` | Backend not returning it |
| `project.root` | Same as installedPath | Falls back to identifier |
| `projectBuildsByRoot[path]` | `BuildTarget[]` | Fetch didn't run or failed |

---

### Remaining TODOs (Low Priority)

1. **Compact mode for ProjectCard**
   - Goal: `compact` flag that renders just the header row (for use in dependency lists)
   - Would allow DependencyItem to be replaced entirely by ProjectCard

2. **Full data model unification**
   - Current: `dependencyToProject()` function converts `ProjectDependency` to `Project`
   - Goal: Both could use the same interface directly
