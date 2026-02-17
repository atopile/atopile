# Manufacturing & Review Dashboard — Specification

**Status:** Draft
**Date:** 2026-02-17
**Authors:** Team
**Scope:** Phase 1 (Dashboard Shell) + Phase 2 (outline)

---

## 1. Context & Motivation

The manufacturing step is the final step in a user's atopile project build process. A user designs electronics in `.ato` code, the compiler resolves parameters and generates KiCad PCB files, and then the user must **build**, **review**, and **export** manufacturing artifacts before sending them to a fab house.

Today this workflow lives in a sidebar panel (`ManufacturingPanel.tsx`, ~1325 lines) with a Build → Review → Export flow crammed into the sidebar's narrow column. There is also an older `ManufacturingWizard.tsx` modal-based 3-step flow (Select Builds → Build & Review → Export) that will be superseded.

### Current Limitations

- **Cramped layout**: Sidebar is too narrow for meaningful visual review. Gerber layers, 3D models, and BOM tables all compete for ~350px of width.
- **Only 3 review tabs**: Gerbers, BOM, 3D Preview. No 2D PCB render, no documents checklist, no structured review workflow.
- **No guided review**: Users can skip straight to export without reviewing anything. No completion tracking, no review comments.
- **Limited export options**: Only gerbers, BOM CSV, and pick & place are selectable. Many available artifacts (SVG, DXF, testpoints, variables report, datasheets, power tree) are not exposed.
- **Single fab house**: Cost estimation is hardcoded to JLCPCB with no way to select alternatives.
- **No review persistence**: Review state is lost on panel close. No way to annotate findings.

### Goal

A **full-screen dashboard** experience with a structured, guided review workflow, rich export capabilities, and a plugin architecture that makes adding new review pages trivial.

---

## 2. Current State

### 2.1 Frontend Components

| File | Location | Purpose |
|------|----------|---------|
| `ManufacturingPanel.tsx` | `src/ui-server/src/components/manufacturing/` | Full sidebar panel: build stages, git status, 3 review tabs (Gerbers/BOM/3D), cost estimation, export |
| `ManufacturingWizard.tsx` | same | Older 3-step modal wizard (Select Builds → Build & Review → Export). To be superseded. |
| `WizardStep.tsx` | same | Accordion step wrapper for the wizard |
| `SelectBuildsStep.tsx` | same | Build target selection with git status warning |
| `BuildReviewStep.tsx` | same | Review container with progress bar |
| `BuildReviewCard.tsx` | same | Per-build card with BOM/3D/Layout tabs |
| `ExportStep.tsx` | same | Directory selection, file checkboxes, cost panel |
| `CostEstimatePanel.tsx` | same | Cost breakdown display with quantity input |
| `types.ts` | same | All manufacturing type definitions |

### 2.2 Viewer Components

| Component | Location | Used For |
|-----------|----------|----------|
| `ModelViewer.tsx` | `src/ui-server/src/components/` | 3D GLB/STEP model display with orbit/zoom/pan |
| `GerberViewer.tsx` | same | Gerber zip rendering via `@tracespace/core` |
| `KiCanvasEmbed.tsx` | same | KiCad PCB/schematic interactive viewer |
| `BOMPanel.tsx` | same | BOM table display with LCSC enrichment |

### 2.3 Backend

**Routes** (`src/atopile/server/routes/manufacturing.py`), prefix `/api/manufacturing`:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/git-status` | GET | Check for uncommitted changes, return changed files list |
| `/outputs` | GET | Get paths to all build output files for a target |
| `/estimate-cost` | POST | Simple cost estimation (legacy) |
| `/export` | POST | Copy selected files to export directory |
| `/board-summary` | GET | Board dimensions, layers, assembly info, part categorization |
| `/detailed-estimate` | POST | Full JLCPCB pricing breakdown with board summary |

**Domain logic** (`src/atopile/server/domains/`):

- `manufacturing.py` — Git status, build output discovery, file export orchestration
- `cost_estimation.py` — JLCPCB pricing model: PCB fab, component, and assembly cost calculation with detailed breakdowns

### 2.4 Build Artifacts

The build system produces these artifacts (via `src/faebryk/exporters/`):

| Artifact | Build Target | Output Pattern | Currently in `BuildOutputs` |
|----------|-------------|----------------|----------------------------|
| Gerbers | `mfg-data` | `{target}.gerber.zip` | Yes |
| BOM (CSV) | `bom` | `{target}.bom.csv` | Yes |
| BOM (JSON) | `bom` | `{target}.bom.json` | Yes |
| Pick & Place | `mfg-data` | `{target}.jlcpcb_pick_and_place.csv` | Yes |
| 3D Model (STEP) | `mfg-data` | `{target}.pcba.step` | Yes |
| 3D Model (GLB) | `mfg-data` | `{target}.pcba.glb` | Yes |
| KiCad PCB | — | `{target}.kicad_pcb` | Yes |
| KiCad Schematic | — | `{target}.kicad_sch` | Yes |
| PCB Summary | `mfg-data` | `{target}.pcb_summary.json` | Yes |
| 2D Render (SVG) | `2d-image` | `{target}.pcba.svg` | **No** |
| 3D Render (PNG) | `3d-image` | `{target}.pcba.png` | **No** |
| Board Outline (DXF) | `mfg-data` | `{target}.pcba.dxf` | **No** |
| Testpoints | `mfg-data` | `{target}.testpoints.json` | **No** |
| Variables Report | `variable-report` | `{target}.variables.json` | **No** |
| Power Tree | `power-tree` | `power_tree.md` | **No** |
| Datasheets | `datasheets` | `documentation/datasheets/` | **No** |

### 2.5 WebSocket Actions (existing)

| Action | Purpose |
|--------|---------|
| `build` | Trigger build with project/targets |
| `getManufacturingGitStatus` | Check uncommitted changes |
| `getManufacturingOutputs` | Fetch build output file paths |
| `refreshBOM` | Load BOM data |
| `fetchLcscParts` | Fetch LCSC part stock/pricing |
| `getDetailedCostEstimate` | Full cost calculation |
| `estimateManufacturingCost` | Quick cost estimate |
| `exportManufacturingFiles` | Export files to directory |

### 2.6 VS Code Webview Infrastructure

`BaseWebview` (`src/vscode-atopile/src/ui/webview-base.ts`) provides the foundation for full-screen tab webviews. Existing implementations: `ModelViewerWebview`, `LayoutEditorWebview`, `PackageExplorerWebview`, `KiCanvasWebview`. Each registers a `WebviewConfig` with `id`, `title`, `column`, and gets a dedicated VS Code tab.

### 2.7 State Management

The Zustand store (`src/ui-server/src/store/index.ts`) tracks `ManufacturingWizardState` with:
- Wizard open/step state
- Selected builds and their status
- Git status (uncommitted changes, file list)
- Export directory, selected file types, quantity
- Cost estimate data
- Loading states

---

## 3. Goals & Non-Goals

### Goals

1. **Full-screen tab layout** — Opens as a dedicated VS Code webview tab (like the 3D viewer tab), not a sidebar panel.
2. **Two-column layout** — Left sidebar (~250px) for step navigation, main content area for active step.
3. **Guided review workflow** — Step-by-step review with completion tracking per sub-step.
4. **5+ review sub-views** — 3D PCBA, 2D PCB render, Interactive BOM, Gerber viewer, Documents checklist. Architecture supports adding more (testpoints, power tree, I2C tree, etc.).
5. **Review page plugin system** — Adding a new review page requires only a React component and a registry entry.
6. **Rich export options** — All available artifacts selectable via checkboxes (standard + advanced).
7. **Fab house selector** — Dropdown to choose fab house (JLCPCB default), affecting cost estimation and "Go to" link.
8. **Cost estimation** — Integrated into export step, reflecting selected fab house and PCB/PCBA quantities.
9. **Review comments** — Per-step comment persistence to `review_comments.md` in the build output folder.
10. **Git status awareness** — Uncommitted changes warning for reproducibility.

### Non-Goals

- Direct PCB editing within the dashboard
- Real-time collaboration features
- Ordering integration beyond linking to the fab house website
- Replacing the sidebar panel entirely (it remains for quick access; the dashboard is for thorough review)

---

## 4. UI Layout

### 4.1 Entry Point

The sidebar "Manufacture" button opens the dashboard as a full-screen VS Code webview tab. The existing sidebar panel remains available for quick builds; the dashboard is the thorough review experience.

### 4.2 Overall Layout

```
┌──────────────────────────────────────────────────────────────┐
│  Manufacturing Dashboard — {project name} / {target}         │
├─────────────┬────────────────────────────────────────────────┤
│             │                                                │
│  1. Build   │                                                │
│    ○ Git    │           Main Content Area                    │
│    ○ Build  │                                                │
│    ○ Verify │     (renders active step's content)            │
│             │                                                │
│  2. Review  │     Layout varies per step:                    │
│    ○ 3D     │     - single pane (3D viewer)                  │
│    ○ 2D     │     - split view (BOM + details)               │
│    ○ iBOM   │     - checklist (documents)                    │
│    ○ Gerber │                                                │
│    ○ Docs   │                                                │
│             │                                                │
│  3. Export  │                                                │
│    ○ Files  │                                                │
│    ○ Cost   │                                                │
│             │                                                │
├─────────────┴────────────────────────────────────────────────┤
│  Status bar: "3 of 5 review items completed"                 │
└──────────────────────────────────────────────────────────────┘
```

### 4.3 Left Sidebar (~250px)

Vertical step navigator with three top-level sections, each expandable to show sub-steps:

```
1. Build
   └─ (build progress, git status)

2. Review
   ├─ 3D View
   ├─ 2D Render
   ├─ Interactive BOM
   ├─ Gerber Viewer
   └─ Documents

3. Export
   └─ (file selection, cost, export actions)
```

Each step/sub-step shows:
- **Number or icon** (e.g., cube icon for 3D, layers icon for Gerber)
- **Label** (e.g., "3D View")
- **Status indicator**: pending (○), active (●), complete (✓), warning (⚠)

Navigation is **free-form** — users can click any step at any time. Steps are not locked behind completion of prior steps, except:
- Review steps are only meaningful after a successful build
- Export "Export Files" action requires at least one file type selected

### 4.4 Main Content Area

Fills remaining width. Layout varies by active step:
- **Build**: Single pane with progress stages and verification checklist
- **3D View**: Single pane, full-size 3D viewer
- **2D Render**: Single pane, SVG viewer with layer controls
- **Interactive BOM**: Full-width table
- **Gerber Viewer**: Single pane with layer selector sidebar
- **Documents**: Checklist/summary layout
- **Export**: Two-column split — file selection on left, cost estimation on right

---

## 5. Feature Specification per Step

### 5.1 Build Step

The build step orchestrates the manufacturing build and verifies its outputs.

**Pre-build:**
- Git status check via `getManufacturingGitStatus`
- If uncommitted changes: show warning banner with list of changed files, "Dismiss" button to continue anyway
- Display selected build target

**Build trigger:**
- "Start Build" button
- Runs a frozen build (`frozen: true`) with the `mfg-data` muster target
- The build should also produce SVG (2D render) if not already part of `mfg-data`

**Live progress:**
- Real-time build stage tracking from backend via WebSocket (`/ws/state`)
- Each stage shows: name, status (pending/running/done/failed), elapsed time
- Clicking on any build stage opens the corresponding debug window (same behavior as sidebar build steps)

**Post-build verification:**
- Artifact verification checklist:
  - ✓/✗ Gerbers generated
  - ✓/✗ BOM generated (CSV + JSON)
  - ✓/✗ Pick & place file generated
  - ✓/✗ 3D model generated (GLB)
  - ✓/✗ 2D render generated (SVG)
  - ✓/✗ PCB summary available
- Stock check: Fetch LCSC data via `fetchLcscParts`, flag out-of-stock or unknown parts

**On success:**
- "Next: Review" button to navigate to the first review step
- No auto-advance — user clicks to proceed

**On failure:**
- Error message display
- "Open Problems Panel" link
- "Retry Build" button

### 5.2 Review — 3D View

**Purpose:** Get a general feel for the assembled board — component placement, board shape, overall aesthetics.

**Content:**
- Full-size 3D model viewer rendering the GLB file
- Reuses existing `ModelViewer` component
- Orbit, zoom, and pan controls (already implemented in ModelViewer)

**Optional enhancements (not required for Phase 1):**
- Toggle between top/bottom view presets
- Wireframe mode toggle
- Component highlight on hover

**Review actions (provided by shell):**
- "Mark as Reviewed" button → marks this step complete in sidebar
- "Comment" button → opens text input, persists to `review_comments.md`

**Available when:** `outputs.glb` exists

### 5.3 Review — 2D Render

**Purpose:** Check silkscreen text, component placement labels, board outline, and layer artwork.

**Content:**
- 2D SVG render of the PCB (from `{target}.pcba.svg`)
- Displayed as an SVG image with zoom and pan controls
- Shows top view by default

**Optional enhancements (not required for Phase 1):**
- Toggle between top and bottom views (requires two SVGs or a flip parameter)
- Layer toggle controls (silkscreen, fab, courtyard)
- Zoom to specific area

**Review actions (provided by shell):**
- "Mark as Reviewed" button
- "Comment" button

**Available when:** `outputs.svg` exists (new field in `BuildOutputs`)

### 5.4 Review — Interactive BOM

**This is a separate project due to its size and complexity. Phase 1 uses a placeholder.**

**Phase 1 (placeholder):**
- Simple message: "Interactive BOM viewer — coming soon"
- Link to open the BOM CSV in the default application
- Still shows "Mark as Reviewed" button (user can mark it reviewed after external inspection)

**Future vision (Phase 2):**
- Rich table with columns: Designator(s), Value, Package, MPN, LCSC#, Qty, Unit Cost, Total Cost, Stock Status, Category (basic/extended)
- Search and filter by designator, value, MPN
- Sort by any column
- Out-of-stock parts highlighted in red
- Specified vs actual parameters (from variables report)
- Group by component type or LCSC category
- Total cost summary at bottom

**Available when:** always (placeholder is always shown)

### 5.5 Review — Gerber Viewer

**This is a separate project due to its size and complexity. Phase 1 uses a placeholder.**

**Phase 1 (placeholder):**
- Simple message: "Advanced Gerber viewer — coming soon"
- Falls back to existing `GerberViewer` component (basic `@tracespace` rendering) if gerber zip is available
- "Mark as Reviewed" button

**Future vision (Phase 2):**
- Layer-by-layer rendering (copper top/bottom, mask, silk, paste, edge cuts, drill)
- Individual layer toggle on/off
- High-quality rendering via pygerber (server-side) or custom GPU-based renderer
- Zoom, pan, measurement tool
- Optional DRC overlay

**Available when:** always (placeholder is always shown)

### 5.6 Review — Documents / Checklist

**Purpose:** Summary of the review process — what has been reviewed, what warnings exist, and any comments left.

**Content:**
- **Review completion summary:** Table showing each review step's completion status (✓/✗)
- **Comments summary:** All comments written across review steps, pulled from `review_comments.md`, grouped by review step with timestamps
- **Artifact inventory:** List of all generated build artifacts with file sizes
- **Warnings:** Any flagged issues (out-of-stock parts, uncommitted changes, missing artifacts)

**Behavior:**
- This page shows an "All items reviewed" confirmation when all other review steps are marked complete
- Does not block export — users can export without completing all reviews, but the documents page makes the review status visible

**Available when:** always

### 5.7 Export Step

The export step provides file selection, cost estimation, and export actions.

#### 5.7.1 Standard Exports (checkboxes)

| Export | Format | Description | Default |
|--------|--------|-------------|---------|
| Gerbers | `.zip` | PCB manufacturing files (Gerber RS-274X) | ✓ |
| BOM (CSV) | `.csv` | JLCPCB-compatible bill of materials | ✓ |
| BOM (JSON) | `.json` | Rich BOM with metadata | |
| Pick & Place | `.csv` | Component placement for assembly | ✓ |
| 3D Model (STEP) | `.step` | CAD-compatible 3D model | |
| 3D Model (GLB) | `.glb` | Web-compatible 3D model | |
| 2D Render (SVG) | `.svg` | Board artwork | |
| Board Outline (DXF) | `.dxf` | Mechanical outline | |
| KiCad PCB | `.kicad_pcb` | PCB layout file | |
| KiCad Schematic | `.kicad_sch` | Schematic file | |
| Testpoints | `.json` | Test point locations | |
| Variables Report | `.json` | Solved parameters | |
| Datasheets | `.pdf` (folder) | Component datasheets | |

Default selections: Gerbers, BOM (CSV), Pick & Place (same as current behavior).

#### 5.7.2 Advanced Exports (checkboxes, mostly placeholders)

| Export | Description | Status |
|--------|-------------|--------|
| HQ 3D Render | High-quality PNG render of assembled board | Separate project |
| Power Tree | Mermaid/SVG power distribution diagram | Separate project |
| AI-Generated README | LLM-generated project summary with specs, BOM highlights | Separate project |
| Manufacturing Notes | Auto-generated layer stackup, special requirements, assembly instructions | Separate project |

Advanced exports that are not yet implemented show a "coming soon" badge and are non-selectable.

#### 5.7.3 Export Configuration

- **Output directory**: Text input with browse button, defaults to `{project}/manufacturing`
- **Fab house selector**: Dropdown, currently only JLCPCB (extensible for future fab houses)
- **PCB quantity**: Numeric input (affects PCB fab cost)
- **PCBA quantity**: Numeric input (affects assembly + component cost)

#### 5.7.4 Cost Estimation Panel

Integrated into the export step, displayed alongside file selection.

- **Summary**: Total cost = PCB + Components + Assembly, displayed prominently
- **PCB fabrication**: Base cost by layer count, area surcharges
- **Components**: Total component cost from LCSC pricing
- **Assembly**: Setup fee, stencil, solder joints, extended part loading fees
- **Per-unit and total**: Shows both per-unit and total (per-unit × quantity) costs
- **Board summary reference**: Dimensions, layer count, total components, part categorization (basic/preferred/extended/unknown)

Cost recalculates when quantity or fab house changes.

#### 5.7.5 Export Actions

- **"Export Files" button**: Copies selected files to the output directory. Disabled if no files selected.
- **"Open Export Folder" button**: Opens the output directory in the OS file manager (Finder/Explorer)
- **"Go to {fab house}" button**: Opens the selected fab house's order page in the browser. Label and URL change based on fab house selector (e.g., "Go to JLCPCB" → `https://cart.jlcpcb.com/quote`).

**Post-export success state:**
- Confirmation message with list of exported files
- File sizes and paths

---

## 6. Client/Server Boundary

**All logic and data processing lives server-side. The client is purely a visualization and interaction layer.**

| Concern | Server (Python/FastAPI) | Client (React/TypeScript) |
|---------|------------------------|--------------------------|
| Build execution | Runs builds, tracks stages | Displays progress, shows errors |
| Artifact generation | Generates gerbers, BOM, SVG, etc. | Displays pre-rendered artifacts |
| Gerber rendering | Parses gerber files (future: pygerber) | Displays rendered images/SVG |
| BOM processing | Parses CSV/JSON, enriches with LCSC data | Displays table |
| Cost calculation | JLCPCB pricing model, all math | Displays numbers |
| Review comments | Reads/writes `review_comments.md` | Captures text input, displays comments |
| File export | Copies files to output directory | Sends user selections |
| Git status | Runs git commands | Displays status |
| Fab house config | Stores supported fab houses, URLs, pricing models | Renders dropdown, displays results |

**The client never:**
- Parses gerber files, BOM CSVs, or STEP models
- Performs cost calculations
- Writes to the filesystem directly
- Runs git commands
- Transforms or processes build artifacts

---

## 7. Review Page Architecture (Plugin System)

The dashboard shell must make adding new review pages trivial. Each review page is a self-contained module that conforms to a standard interface. The shell handles all shared concerns (navigation, review state, comments).

### 7.1 Standard Interfaces

```typescript
// Each review page registers itself via this interface
interface ReviewPageDefinition {
  id: string;                              // e.g. "3d-view", "gerber-viewer", "ibom"
  label: string;                           // Sidebar display name, e.g. "3D View"
  icon: React.ComponentType<{ size: number }>;  // Sidebar icon (Lucide or custom)
  order: number;                           // Sort order in sidebar (10, 20, 30...)

  // Determine if this page can render given the current build outputs
  isAvailable: (outputs: BuildOutputs) => boolean;
}
```

```typescript
// Props injected by the shell into every review page component
interface ReviewPageProps {
  // Build data (read-only, provided by shell)
  outputs: BuildOutputs;
  bomData: BOMData | null;
  boardSummary: BoardSummary | null;
  projectRoot: string;

  // Review state (managed by shell)
  isReviewed: boolean;
  onMarkReviewed: () => void;

  // Comment system (managed by shell)
  comments: ReviewComment[];
  onAddComment: (text: string) => void;
}
```

```typescript
interface ReviewComment {
  pageId: string;       // Which review page this comment belongs to
  text: string;         // Comment content
  timestamp: string;    // ISO timestamp
}
```

### 7.2 How the Shell Uses This

1. The shell imports a `REVIEW_PAGES` registry — an array of `{ definition: ReviewPageDefinition, component: React.ComponentType<ReviewPageProps> }` entries.
2. The left sidebar's "Review" section is generated from `REVIEW_PAGES`, filtered by `isAvailable(outputs)`. Pages with `isAvailable = false` are hidden.
3. The shell renders the active page's component, injecting standard `ReviewPageProps`.
4. The shell renders the shared "Mark as Reviewed" button and "Comment" button/dialog as chrome around (or overlaid on) the page component. Individual pages do not implement these themselves.
5. Review state (per-page `reviewed: boolean`) and comments are managed centrally in the Zustand store and persisted server-side.

### 7.3 Adding a New Review Page

To add a new review page, a developer:

1. Creates a React component that accepts `ReviewPageProps`
2. Adds an entry to the `REVIEW_PAGES` registry with a `ReviewPageDefinition`

That's it. The shell handles sidebar entry, navigation, review tracking, and comments automatically.

### 7.4 Phase 1 Review Pages

| Page ID | Component | `isAvailable` | Notes |
|---------|-----------|---------------|-------|
| `3d-view` | Wraps existing `ModelViewer` | `outputs.glb` exists | Reuse existing viewer |
| `2d-render` | `SvgViewer` (new, simple) | `outputs.svg` exists | SVG embed with zoom/pan |
| `ibom` | `PlaceholderPage` | always | Placeholder, separate project |
| `gerber` | `PlaceholderPage` | always | Placeholder, separate project |
| `documents` | `DocumentsChecklist` (new) | always | Review summary + comments |

### 7.5 Future Review Pages (Phase 2+)

| Page ID | Description | `isAvailable` |
|---------|-------------|---------------|
| `testpoints` | Testpoint location viewer | `outputs.testpoints` exists |
| `power-tree` | Power distribution diagram | `outputs.powerTree` exists |
| `i2c-tree` | I2C address tree viewer | TBD |
| `parameters` | Solved parameter comparison | `outputs.variablesReport` exists |

---

## 8. Data Requirements

### 8.1 Data Sources per View

| View | Data Source | API / WebSocket Action |
|------|------------|----------------------|
| Build | Build stages, git status | WebSocket `/ws/state`, `getManufacturingGitStatus` |
| 3D View | GLB file path | `getManufacturingOutputs` → `outputs.glb` |
| 2D Render | SVG file path | `getManufacturingOutputs` → `outputs.svg` (**new field**) |
| Interactive BOM | BOM JSON + LCSC data | `refreshBOM`, `fetchLcscParts` |
| Gerber Viewer | Gerber zip path | `getManufacturingOutputs` → `outputs.gerbers` |
| Documents | PCB summary, comments, review status | `pcb_summary.json`, `review_comments.md`, client state |
| Export | All artifact paths, fab house config | `getManufacturingOutputs`, `exportManufacturingFiles` |
| Cost | Board summary, BOM, pricing | `getDetailedCostEstimate` |

### 8.2 New Data / API Changes Required

#### Expand `BuildOutputs` type

Add fields for artifacts not currently exposed:

```typescript
interface BuildOutputs {
  // Existing
  gerbers: string | null;
  bomJson: string | null;
  bomCsv: string | null;
  pickAndPlace: string | null;
  step: string | null;
  glb: string | null;
  kicadPcb: string | null;
  kicadSch: string | null;
  pcbSummary: string | null;

  // New
  svg: string | null;              // 2D PCB render
  dxf: string | null;              // Board outline
  png: string | null;              // 3D rendered image
  testpoints: string | null;       // Testpoint locations JSON
  variablesReport: string | null;  // Solved parameters JSON
  powerTree: string | null;        // Power tree markdown
  datasheets: string | null;       // Datasheets directory path
}
```

The backend `get_build_outputs()` function must be updated to discover these additional files.

#### Expand `FileExportType`

```typescript
type FileExportType =
  | 'gerbers' | 'bom_csv' | 'bom_json' | 'pick_and_place'
  | 'step' | 'glb' | 'svg' | 'dxf' | 'png'
  | 'kicad_pcb' | 'kicad_sch'
  | 'testpoints' | 'variables_report' | 'datasheets';
```

#### Review Comments API

New server-side endpoints or WebSocket actions:

| Action | Purpose | Details |
|--------|---------|---------|
| `getReviewComments` | Read comments | Returns parsed `review_comments.md` as `ReviewComment[]` |
| `addReviewComment` | Write comment | Appends to `review_comments.md` with page ID and timestamp |

**File format** (`{build_output}/review_comments.md`):

```markdown
## Review Comments

### 3d-view — 2026-02-17T14:30:00Z
Component U3 looks too close to the board edge. Double-check clearance.

### 2d-render — 2026-02-17T14:35:00Z
Silkscreen text for J1 is overlapping the courtyard of C5.
```

Append-only. Each comment is a markdown section with the page ID and ISO timestamp in the heading.

#### Fab House Configuration

New data structure for fab house support:

```typescript
interface FabHouse {
  id: string;           // e.g. "jlcpcb"
  name: string;         // e.g. "JLCPCB"
  orderUrl: string;     // e.g. "https://cart.jlcpcb.com/quote"
  supported: boolean;   // true if cost estimation is implemented
}
```

Phase 1: Only JLCPCB. The dropdown is present but has a single option. Adding a new fab house later means:
1. Adding a pricing model in the backend
2. Adding an entry to the fab houses list

---

## 9. State Management

### 9.1 Dashboard State (Zustand store slice)

```typescript
interface ManufacturingDashboardState {
  // Navigation
  activeStep: 'build' | 'review' | 'export';
  activeReviewPage: string | null;  // Review page ID, e.g. "3d-view"

  // Build
  buildStatus: 'idle' | 'building' | 'success' | 'failed';
  buildStages: BuildStage[];        // Real-time progress
  buildId: string | null;
  artifactVerification: Record<string, boolean>;  // e.g. { gerbers: true, bom: true }

  // Git
  gitStatus: {
    checking: boolean;
    hasUncommittedChanges: boolean;
    changedFiles: string[];
    warningDismissed: boolean;
  };

  // Build outputs (from server after build completes)
  outputs: BuildOutputs | null;
  bomData: BOMData | null;
  boardSummary: BoardSummary | null;

  // Review
  reviewStatus: Record<string, boolean>;  // { "3d-view": true, "2d-render": false, ... }
  reviewComments: ReviewComment[];

  // Export
  selectedFileTypes: Set<FileExportType>;
  selectedAdvancedExports: Set<string>;
  exportDirectory: string;
  selectedFabHouse: string;  // Fab house ID, default "jlcpcb"
  pcbQuantity: number;
  pcbaQuantity: number;

  // Cost
  costEstimate: DetailedCostEstimate | null;
  costLoading: boolean;

  // Export state
  isExporting: boolean;
  exportResult: { success: boolean; files: string[]; errors?: string[] } | null;
}
```

### 9.2 State Persistence

- **Within session**: State persists across tab switches (user navigates away and back to the dashboard tab). Managed by Zustand store.
- **Across sessions**: Review comments are persisted server-side in `review_comments.md`. Review completion status and other UI state is not persisted across sessions (resets on VS Code restart).

---

## 10. Acceptance Criteria

### Core Dashboard

1. Dashboard opens as a full-screen VS Code webview tab (not sidebar panel)
2. Left sidebar shows all steps and sub-steps with visual completion indicators
3. User can navigate freely between steps (not forced linear)
4. Main content area adapts layout per step
5. Dashboard state persists within a session (not lost on tab switch)

### Build Step

6. Build step shows real-time progress from backend stages
7. Clicking a build step opens the corresponding debug window
8. Build failure shows errors with link to Problems panel and retry button
9. Build success shows "Next: Review" button (no auto-advance)
10. Post-build artifact verification checklist updates correctly

### Review Steps

11. Each review sub-step has a "Mark as Reviewed" action (provided by shell)
12. Each review sub-step has a "Comment" button that persists to `review_comments.md`
13. 3D View renders correctly with existing `ModelViewer` component
14. 2D Render displays SVG with zoom/pan
15. Interactive BOM and Gerber Viewer display graceful placeholder states
16. Documents/Checklist shows review completion status and all comments across steps

### Export Step

17. Standard export checkboxes work, with defaults pre-selected (gerbers, BOM CSV, PnP)
18. Advanced exports show "coming soon" badge for unimplemented features
19. Fab house selector dropdown works (JLCPCB default, extensible)
20. Separate PCB and PCBA quantity inputs
21. Cost estimation reflects selected fab house and quantities, recalculates on change
22. "Export Files" copies correct files to chosen directory
23. "Open Export Folder" opens OS file manager
24. "Go to {fab house}" opens correct URL based on selector

### Plugin System

25. Review pages are loaded from `REVIEW_PAGES` registry
26. Sidebar entries are generated dynamically from registry (filtered by `isAvailable`)
27. Shared review chrome (Mark as Reviewed, Comment) works identically across all pages
28. Adding a new review page requires only a component + registry entry (no shell changes)

---

## 11. Phasing

### Phase 1 — Dashboard Shell (this project)

This is the core deliverable. Everything else plugs into it.

| # | Deliverable | Description |
|---|-------------|-------------|
| 1 | Full-screen tab infrastructure | New `ManufacturingDashboardWebview` extending `BaseWebview`, registered in VS Code extension, "Manufacture" button wired to open it |
| 2 | Two-column layout | Left sidebar (step navigator) + main content area, responsive |
| 3 | Left sidebar navigation | Build / Review (sub-pages) / Export steps with completion indicators, review section generated from `REVIEW_PAGES` registry |
| 4 | Review page plugin system | `ReviewPageDefinition` + `ReviewPageProps` interfaces, `REVIEW_PAGES` registry, shell renders active page with injected props |
| 5 | Shared review chrome | "Mark as Reviewed" button and "Comment" button/dialog, rendered by shell around each page component |
| 6 | Review state + comments | Zustand store slice for per-page review status, comments persisted to `review_comments.md` via server API |
| 7 | Build step | Reuse existing build logic (git status, frozen build, stage progress, artifact verification) |
| 8 | Export step | Standard + advanced export checkboxes, fab house dropdown, PCB/PCBA quantity, directory selector, cost estimation, export action |
| 9 | Initial review pages | 3D View (existing `ModelViewer`), 2D Render (SVG embed), placeholders for iBOM and Gerber, Documents/Checklist |
| 10 | `BuildOutputs` expansion | Add `svg`, `dxf`, `png`, `testpoints`, `variablesReport`, `powerTree`, `datasheets` fields to type and backend discovery |

### Phase 2 — Separate Projects (plug into Phase 1 shell)

Each is an independent project that registers a new entry in `REVIEW_PAGES`:

- **Interactive BOM viewer** — Rich table with search/filter/sort, LCSC enrichment, stock warnings
- **Gerber Viewer** — pygerber or custom GPU renderer, layer-by-layer inspection
- **Advanced exports** — HQ 3D render, AI-generated README, manufacturing notes, power tree diagram
- **Future review pages** — Testpoints, power tree, I2C tree, parameter comparison

---

## 12. Verification

### Manual Testing

- Open dashboard, run through full Build → Review → Export flow with a real project
- Verify 3D viewer renders GLB correctly at full size
- Verify 2D render displays SVG with working zoom/pan
- Test "Comment" button on each review step, verify comments persist in `review_comments.md` and appear in Documents checklist
- Test "Mark as Reviewed" on each step, verify sidebar indicators update
- Test export with different file type selections, verify files appear in output directory
- Test fab house selector (single option for now, verify label/URL update)
- Test quantity inputs, verify cost recalculation
- Test with a project that has warnings (out-of-stock parts, uncommitted changes)
- Verify placeholder views (iBOM, Gerber) display graceful empty states with helpful messaging

### Environment Testing

- Verify full-screen tab works in VS Code webview
- Verify full-screen tab works in standalone dev mode (`npm run dev`)
- Verify dashboard state persists when switching away from and back to the tab
- Verify sidebar panel still works independently of dashboard

### Edge Cases

- Build with no GLB output (3D View should be hidden in sidebar)
- Build with no SVG output (2D Render should be hidden in sidebar)
- Export with no files selected (button should be disabled)
- Network error during cost estimation (show error, allow retry)
- Very large BOM (placeholder should still be responsive)

---

## 13. Key Files Reference

| Area | Path |
|------|------|
| Current manufacturing UI | `src/ui-server/src/components/manufacturing/` |
| Manufacturing types | `src/ui-server/src/components/manufacturing/types.ts` |
| Viewer components | `src/ui-server/src/components/ModelViewer.tsx`, `GerberViewer.tsx`, `KiCanvasEmbed.tsx`, `BOMPanel.tsx` |
| Backend routes | `src/atopile/server/routes/manufacturing.py` |
| Backend domain | `src/atopile/server/domains/manufacturing.py` |
| Cost estimation | `src/atopile/server/domains/cost_estimation.py` |
| Zustand store | `src/ui-server/src/store/index.ts` |
| VS Code webview base | `src/vscode-atopile/src/ui/webview-base.ts` |
| Existing webviews | `src/vscode-atopile/src/ui/model-viewer.ts`, `layout-editor.ts`, etc. |
| Build artifact exporters | `src/faebryk/exporters/pcb/kicad/artifacts.py` |
| SVG export function | `src/faebryk/exporters/pcb/kicad/artifacts.py` → `export_svg()` |
| BOM exporters | `src/faebryk/exporters/bom/` |
| Testpoint exporter | `src/faebryk/exporters/pcb/testpoints/testpoints.py` |
| Power tree exporter | `src/faebryk/exporters/power_tree/power_tree.py` |
| Variables exporter | `src/faebryk/exporters/parameters/parameters_to_file.py` |
| Review comments (new) | `{build_output}/review_comments.md` |
