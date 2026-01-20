# Webview UI Tasks

## Overview
This document outlines the remaining UI tasks for the atopile VSCode extension webviews. Each task includes the problem description, implementation approach, files to modify, and testing strategy.

---

## Task 0: Project-Level Build Should Queue All Targets
**Priority:** CRITICAL | **Complexity:** Medium

### Problem
When clicking the project-level build button (play button on project/package row), only the "default" target builds. The desired behavior is to queue ALL targets from that project.

### Current Behavior
- Backend hardcodes `targets = ["default"]` for `level='project'` builds
- Only one build is queued regardless of how many targets the project has

### Desired Behavior
- Click project-level build button
- ALL targets from that project are added to the build queue as separate builds
- Each target builds independently

### Implementation
1. When `level='project'`, read targets from the project's `ato.yaml`
2. Queue a separate build for each target
3. For packages, read targets from the package's `ato.yaml` at `.ato/modules/{identifier}/ato.yaml`

### Files to Modify
- `src/atopile/dashboard/server.py` - Modify the `level='project'` handler in the build action (~line 2651)

### Current Code (server.py ~line 2651)
```python
if level == "project":
    project_root = payload_id
    if not targets:
        targets = ["default"]  # PROBLEM: hardcoded to default only
```

### New Logic
```python
if level == "project":
    project_root = payload_id
    if not targets:
        # Read all targets from ato.yaml after path resolution
        # This happens later after project_path is validated
        build_all_targets = True
```

Then after path validation:
```python
if build_all_targets:
    # Read targets from ato.yaml
    ato_yaml_path = project_path / "ato.yaml"
    if ato_yaml_path.exists():
        with open(ato_yaml_path) as f:
            ato_config = yaml.safe_load(f)
        all_targets = list(ato_config.get("builds", {}).keys())
        if all_targets:
            # Queue separate build for each target
            for target in all_targets:
                # Create and queue build for this target
                ...
```

### Testing
1. Create project with multiple build targets (default, usage, etc.)
2. Click project-level build button
3. Verify ALL targets appear in build queue
4. Verify each target builds correctly

### WebSocket Test
```python
def test_project_level_build_queues_all_targets(self, test_client, temp_workspace):
    """Project-level build should queue all targets from ato.yaml."""
    project_root = temp_workspace / "test_project"
    ato_yaml = project_root / "ato.yaml"
    ato_yaml.write_text("""
builds:
  default:
    entry: main.ato:App
  usage:
    entry: usage.ato:Usage
""")
    (project_root / "main.ato").write_text("module App:\n    pass\n")
    (project_root / "usage.ato").write_text("module Usage:\n    pass\n")

    with test_client.websocket_connect("/ws/state") as ws:
        ws.receive_json()  # Initial state

        ws.send_json({
            "type": "action",
            "action": "build",
            "payload": {"level": "project", "id": str(project_root), "label": "test"}
        })

        # Should receive success for multiple builds
        build_ids = []
        for _ in range(10):
            msg = ws.receive_json()
            if msg["type"] == "action_result" and msg.get("build_id"):
                build_ids.append(msg["build_id"])

        # Should have created 2 separate builds
        assert len(build_ids) >= 2
```

---

## Task 1: Build Queue Auto-Hide
**Priority:** High | **Complexity:** Low

### Problem
The build queue section remains visible even when there are no active builds, taking up unnecessary space.

### Implementation
- Modify `Sidebar.tsx` to conditionally render the BuildQueue section based on `queuedBuilds.length > 0`
- Or collapse the section by default when empty

### Files to Modify
- `src/components/Sidebar.tsx` - Add conditional rendering for build queue section

### Testing
1. Start with no builds - queue should be hidden/collapsed
2. Trigger a build - queue should appear
3. Build completes - queue should auto-hide when empty

---

## Task 2: Default Collapsed State on Startup
**Priority:** Medium | **Complexity:** Low

### Problem
On startup, all tabs should be collapsed except the Projects tab.

### Implementation
- Modify the initial state of `collapsedSections` in `Sidebar.tsx`
- Set all sections except 'projects' to collapsed by default

### Files to Modify
- `src/components/Sidebar.tsx` - Modify `useState` initialization for `collapsedSections`

### Current Code Location
```typescript
const [collapsedSections, setCollapsedSections] = useState<Set<string>>(new Set());
```

Should become:
```typescript
const [collapsedSections, setCollapsedSections] = useState<Set<string>>(
  new Set(['buildQueue', 'packages', 'problems', 'stdlib', 'variables', 'bom'])
);
```

### Testing
1. Reload the webview
2. Verify only Projects section is expanded
3. Other sections should be collapsed but expandable

---

## Task 3: Render .ato and .py Files in Projects Tab
**Priority:** High | **Complexity:** Medium

### Problem
The file tree in the projects tab is not rendering .ato or .py files.

### Implementation
1. Check the backend file discovery logic in `server.py`
2. Verify the `fetchFiles` action is returning .ato and .py files
3. Check the frontend `ProjectsPanel.tsx` file tree rendering

### Files to Investigate
- `src/atopile/dashboard/server.py` - `discover_files_in_project()` or similar
- `src/components/ProjectsPanel.tsx` - File tree rendering component

### Testing
1. Expand a project in the Projects tab
2. Navigate to a directory with .ato files
3. Verify .ato and .py files are displayed
4. Click on a file - should open in editor

---

## Task 4: Replace Placeholder Logo
**Priority:** Low | **Complexity:** Low

### Problem
The webview uses a placeholder SVG logo instead of the actual atopile logo.

### Implementation
1. The actual logo is at `ato_logo_256x256.png` in the extension root
2. Need to pass the logo URI from extension to webview
3. Or embed the logo directly in the webview

### Files to Modify
- `src/vscode-atopile/src/common/logo.ts` - Already has `getLogoUri()` function
- `src/ui/vscode-panels.ts` - Pass logo URI to webview HTML
- `src/components/Sidebar.tsx` - Use passed logo URI instead of DEFAULT_LOGO

### Current Placeholder (Sidebar.tsx line ~70)
```typescript
const DEFAULT_LOGO = `data:image/svg+xml,...`;
```

### Testing
1. Reload webview
2. Verify atopile logo appears correctly in header
3. Check logo renders in both light and dark themes

---

## Task 5: Packages Not Showing Blurb/Description
**Priority:** Medium | **Complexity:** Medium

### Problem
Package cards in the Packages section are not showing their description/summary blurb.

### Implementation
1. Check if `pkg.summary` or `pkg.description` is populated from backend
2. Verify the `PackageCard` component renders the description
3. Check the state transformation in `Sidebar.tsx` for `transformedPackages`

### Files to Investigate
- `src/atopile/dashboard/server.py` - Package info retrieval
- `src/components/ProjectsPanel.tsx` - `PackageCard` component
- `src/components/Sidebar.tsx` - `transformedPackages` memo

### Testing
1. View Packages section
2. Verify each package shows its summary/description
3. Expanded view should show full description

---

## Task 6: Add Dependency Viewer to Projects
**Priority:** Medium | **Complexity:** Medium

### Problem
Need a simple dependency viewer showing installed packages with versions, similar to build queue style.

### Implementation
1. Create new `DependencyPanel.tsx` component
2. Simple card layout showing: package name, version, publisher
3. Add as a subsection within each project or as a separate collapsible section
4. Fetch dependencies from project's `ato.yaml`

### Files to Create/Modify
- `src/components/DependencyPanel.tsx` (NEW) - Simple dependency cards
- `src/components/DependencyPanel.css` (NEW) - Styling
- `src/components/Sidebar.tsx` - Add section or integrate into ProjectsPanel
- `src/atopile/dashboard/server.py` - Ensure dependencies are exposed in state

### Component Design
```
┌─────────────────────────────────────┐
│ Dependencies (3)                    │
├─────────────────────────────────────┤
│ ┌─────────────────────────────────┐ │
│ │ atopile/pin-headers     v0.1.6 │ │
│ └─────────────────────────────────┘ │
│ ┌─────────────────────────────────┐ │
│ │ atopile/resistors       v0.2.1 │ │
│ └─────────────────────────────────┘ │
└─────────────────────────────────────┘
```

### Testing
1. Expand a project with dependencies
2. Verify dependencies section appears
3. Click on dependency - should navigate to package details

---

## Task 7: Problems Not Displaying
**Priority:** High | **Complexity:** Medium

### Problem
Warnings and errors from builds (e.g., adxl warnings) are not appearing in the Problems section.

### Implementation
1. Check backend is sending problems in state
2. Verify problems are extracted from build logs/stages
3. Check frontend `ProblemsPanel.tsx` filtering and rendering
4. Ensure problem transformation in `Sidebar.tsx` works

### Files to Investigate
- `src/atopile/dashboard/server.py` - Problem extraction from logs
- `src/atopile/dashboard/state.py` - Problem model
- `src/components/ProblemsPanel.tsx` - Problem rendering
- `src/components/Sidebar.tsx` - Problem filtering

### Testing
1. Run a build that generates warnings
2. Check Problems section updates
3. Click on problem - should navigate to source file

---

## Task 8: Variable Report Build Selector
**Priority:** Medium | **Complexity:** Medium

### Problem
The Variable report needs a build/target selector to choose which build's variables to view.

### Implementation
1. Create reusable `BuildSelector` component
2. Add selector to VariablesPanel header
3. Filter variables by selected build target

### Files to Create/Modify
- `src/components/common/BuildSelector.tsx` (NEW) - Reusable dropdown component
- `src/components/VariablesPanel.tsx` - Add build selector integration
- `src/components/Sidebar.tsx` - Pass available builds to VariablesPanel

### Testing
1. Have multiple build targets in a project
2. Open Variables section
3. Use dropdown to switch between targets
4. Verify variables update for selected target

---

## Task 9: BOM Build Selector + Search Bar
**Priority:** Medium | **Complexity:** Medium

### Problem
BOM needs a build selector and search bar, standardized with other panels.

### Implementation
1. Reuse `BuildSelector` component from Task 8
2. Create reusable `SearchBar` component
3. Add both to BOM panel header
4. Implement BOM filtering by search query

### Files to Create/Modify
- `src/components/common/SearchBar.tsx` (NEW) - Reusable search component
- `src/components/BOMPanel.tsx` - Add selector and search integration
- `src/components/common/BuildSelector.tsx` - Ensure reusable

### Standardized Header Pattern
```
┌─────────────────────────────────────────────┐
│ [Build: default ▼] [🔍 Search...        ]   │
├─────────────────────────────────────────────┤
│ Content...                                  │
└─────────────────────────────────────────────┘
```

### Testing
1. Open BOM section
2. Select different build targets
3. Use search to filter BOM items
4. Verify results update correctly

---

## Implementation Order

### Phase 0: Critical Fix
0. **Task 0: Project-Level Build Queues All Targets** (BLOCKING)

### Phase 1: Quick Wins (Low complexity)
1. Task 2: Default Collapsed State
2. Task 1: Build Queue Auto-Hide
3. Task 4: Replace Placeholder Logo

### Phase 2: Data/Display Fixes
4. Task 7: Problems Not Displaying (HIGH PRIORITY)
5. Task 5: Packages Blurb
6. Task 3: Render .ato/.py Files

### Phase 3: New Features
7. Task 8: Variable Report Build Selector
8. Task 9: BOM Build Selector + Search
9. Task 6: Dependency Viewer

---

## Testing Strategy

### Unit Tests
- Add tests for new components (BuildSelector, SearchBar, DependencyPanel)
- Update existing tests for modified components

### Integration Tests
- WebSocket state tests for new data flows
- Test build selector state management

### Manual Testing Checklist
- [x] Project-level build queues ALL targets (DONE - uses ProjectConfig from atopile.config)
- [x] All sections collapse/expand correctly (DONE - default collapsed state set)
- [x] Build queue auto-hides when empty (DONE)
- [x] Logo displays correctly (DONE - embedded as base64 data URI)
- [x] Files render in project tree (DONE - fixed fetchFiles handler)
- [x] Package descriptions show (DONE - implementation verified)
- [x] Problems display from builds (DONE - auto-refresh after build completion)
- [x] Settings parallel workers config (DONE - WebSocket handlers added)
- [ ] Build selectors work across panels
- [ ] Search filtering works
- [ ] Dependencies display correctly

---

## Notes

### Reusable Components to Create
1. `BuildSelector` - Dropdown for selecting build targets
2. `SearchBar` - Standardized search input
3. `DependencyCard` - Simple package card for dependencies

### State Considerations
- Build selection may need to be global or per-panel
- Consider adding `selectedBuildTarget` to app state
- Search state should be local to each panel
