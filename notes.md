# Specification: Manufacturing & Review Dashboard

Write a comprehensive specification document for the advanced manufacturing and review dashboard feature. The spec is a detailed technical document for the team to implement, covering the full vision, and approach-agnostic regarding implementation strategy.

---

## Spec Structure

### 1. Context & Motivation

- The manufacturing step is the final step in a user's project build process
- Currently exists as a sidebar panel (`ManufacturingPanel.tsx`) with Build → Review → Export flow
- Current limitations: cramped sidebar layout, only 3 review tabs (Gerbers/BOM/3D), no step-by-step guided review, limited export options
- Goal: full-screen dashboard experience with structured review workflow and rich export capabilities

### 2. Current State (Reference)

Document what already exists and works:

- `ManufacturingPanel.tsx` (1325 lines) - full panel with stage progress, git status, build steps, review tabs, cost estimation, export
- `ManufacturingWizard.tsx` - older 3-step accordion wizard (likely to be superseded)
- Existing viewer components: `ModelViewer` (GLB/STEP 3D), `GerberViewer` (Gerber zip rendering via @tracespace), `KiCanvasEmbed` (KiCad PCB/schematic), `BOMPanel`
- Backend APIs: `/api/manufacturing/*` endpoints (git-status, outputs, cost estimate, export)
- Build artifacts available: gerbers, BOM (CSV/JSON), pick & place, STEP, GLB, PNG render, SVG, DXF, KiCad files, PCB summary, testpoints, power tree, datasheets, variables report
- Cost estimation: JLCPCB pricing model with PCB/component/assembly breakdown

### 3. Goals & Non-Goals

**Goals:**

- Full-screen tab layout (like the 3D viewer tab) with left sidebar (step navigator) navigation
- Guided step-by-step review workflow with completion tracking
- 5+ review sub-views: 3D PCBA, 2D PCB render, Interactive BOM, Gerber viewer, Documents checklist, later we will add more views (like a testpoint viewer, a power tree viewer, i2c tree viewer, etc.)
- Selectable standard exports (gerber, STEP, DXF, BOM, PnP, etc.)
- Advanced/optional exports (HQ render, AI-generated README, manufacturing notes)
- Cost estimation integrated into the flow
- Git status awareness for reproducibility (uncommitted changes warning)

**Non-Goals:**

- Direct PCB editing within the dashboard
- Real-time collaboration features
- Ordering integration (beyond linking to JLCPCB)

### 4. UI Layout

**Top-level:** Full-screen tab (opened from sidebar "Manufacture" button, replaces current panel behavior)

**Layout:** Two-column

- **Left sidebar** (~250px): Vertical step navigator with completion indicators
- **Main content area**: Renders the active step's content, full-width
  - The main content area will mostly be split into 2, but depending on the step, it will be split into more or less sections.

**Left Sidebar Steps:**

```
1. Build
   └ (build progress, git status)
2. Review
   ├ 3D View
   ├ 2D Render
   ├ Interactive BOM
   ├ Gerber Viewer
   └ Documents
3. Export
   └ (file selection, cost, export actions)
```

Each step/sub-step shows: number/icon, label, status indicator (pending/active/complete/warning)

### 5. Feature Specification per Step

#### 5.1 Build Step

- Pre-build: Git status check (uncommitted changes warning)
- Build trigger: "Start Build" button, runs frozen build with `mfg-data` muster target
- Live progress: Real-time build stage tracking (from backend stages via WebSocket)
- Post-build: Artifact verification checklist (gerbers generated? BOM? PnP?)
- Stock check: Fetch LCSC data, flag out-of-stock or unknown parts
- On success: Show next button to navigate to Review step
- On failure: Show errors, link to Problems panel, retry button
- Clicking on any of the build steps will open the corresponding debug window (same as the build step in the sidebar).

#### 5.2 Review - 3D View

- Full-size 3D model viewer (GLB) with orbit/zoom/pan controls
- Purpose: Get a general feel for the assembled board
- Shows: Fully assembled PCBA with components
- Optional: Toggle between top/bottom view, wireframe mode
- "Mark as reviewed" button to advance
- "Comment" button to write comment to project_build_folder/review_comments.md

#### 5.3 Review - 2D Render

- 2D SVG render of the PCB (top and bottom views)
- Purpose: Check silkscreen text, component placement, board outline
- Shows: Silkscreen layer, component outlines, board edge
- Optional: Layer toggle (silkscreen, fab, courtyard), zoom to area
- "Mark as reviewed" button to advance
- "Comment" button to write comment to project_build_folder/review_comments.md

#### 5.4 Review - Interactive BOM

- Rich table view of all components
- Columns: Designator(s), Value, Package, MPN, LCSC#, Qty, Unit Cost, Total Cost, Stock, Category (basic/extended)
- Features:
  - Search/filter by designator, value, MPN
  - Sort by any column
  - Highlight out-of-stock parts in red
  - Show specified vs actual parameters (from variables report)
  - Group by component type or LCSC category
  - Total cost summary at bottom
- "Mark as reviewed" button to advance
- "Comment" button to write comment to project_build_folder/review_comments.md
- This is a separate project due to its size and complexity. It is ok to use a placeholder for now.

#### 5.5 Review - Gerber Viewer

- Layer-by-layer Gerber rendering (using https://github.com/Argmaster/pygerber or self developed (gpu) gerber renderer)
- Purpose: Detailed inspection of every PCB layer
- Features:
  - Layer selector (copper top/bottom, mask, silk, paste, edge cuts, drill)
  - Toggle individual layers on/off
  - Zoom and pan
  - Optional: measurement tool, DRC overlay
- "Mark as reviewed" button to advance
- "Comment" button to write comment to project_build_folder/review_comments.md
- This is a separate project due to its size and complexity. It is ok to use a placeholder for now.

#### 5.6 Review - Documents / Checklist

- Summary checklist of all reviewed items
- Shows: Which review steps completed, any warnings flagged
- Shows: Any comments written to project_build_folder/review_comments.md
- "All items reviewed" confirmation to unlock Export

#### 5.7 Export Step

**Standard Exports (checkboxes):**

| Export                      | Format     | Description                              |
| --------------------------- | ---------- | ---------------------------------------- |
| Gerbers                     | .zip       | PCB manufacturing files (Gerber RS-274X) |
| BOM (CSV)                   | .csv       | JLCPCB-compatible bill of materials      |
| BOM (JSON)                  | .json      | Rich BOM with metadata                   |
| Pick & Place                | .csv       | Component placement for assembly         |
| 3D Model (STEP)             | .step      | CAD-compatible 3D model                  |
| 3D Model (GLB)              | .glb       | Web-compatible 3D model                  |
| 2D Render (SVG)             | .svg       | Board artwork                            |
| Board Outline (DXF)         | .dxf       | Mechanical outline                       |
| KiCad PCB                   | .kicad_pcb | PCB layout file                          |
| KiCad Schematic             | .kicad_sch | Schematic file                           |
| Testpoints                  | .json      | Test point locations                     |
| Variables Report            | .json      | Solved parameters                        |
| Datasheets                  | .pdf       | Component datasheets                     |
| more will be added later... |            |                                          |

**Advanced Exports (checkboxes):**
These are mostly placeholders for now.

| Export                                 | Description                                                                       |
| -------------------------------------- | --------------------------------------------------------------------------------- |
| HQ 3D Render (separate project)        | High-quality PNG render of assembled board                                        |
| Power Tree (separate project)          | Mermaid/SVG power distribution diagram                                            |
| AI-Generated README (separate project) | LLM-generated project summary with specs, BOM highlights, notes                   |
| Manufacturing Notes (separate project) | Auto-generated notes (layer stackup, special requirements, assembly instructions) |

**Export Configuration:**

- Output directory selector (browse button, defaults to `{project}/manufacturing`)
- fab house selector dropdown (currently only JLCPCB is supported)
- PCB and PCBA quantity input for cost scaling

**Cost Estimation Panel:**

- Integrated into export step
- Fabhouse pricing breakdown: PCB fabrication, components, assembly
- Detailed sub-breakdowns (setup fee, stencil, loading fees, solder joints) (will be added later...)
- Board summary reference (dimensions, layers, parts categorization)
- Per-unit and total cost display
- Warning for out-of-stock or extended parts (might be added later...)

**Export Actions:**

- "Export Files" button → copies selected files to output directory
- "Open Export Folder" → reveals in Finder/Explorer
- "Go to [fabhouse_name_from_selector]" → opens fabhouse order page
- Success state with file listing

### 6. Client/Server Boundary

**All logic and data processing lives server-side. The client is purely a visualization and interaction layer.**

- **Server (Python/FastAPI)**: Runs builds, generates artifacts, parses gerbers, computes cost estimates, resolves BOM data, fetches LCSC stock/pricing, reads/writes review comments, manages fab house configurations, performs exports. All "thinking" happens here.
- **Client (React/TypeScript)**: Renders UI components, displays data received from the server, captures user interactions (mark as reviewed, add comment, select exports), and sends actions back to the server via WebSocket/HTTP. No data transformation, file parsing, or business logic on the client.

This means:

- Review pages receive **pre-processed, ready-to-display data** from the server
- The client never parses gerber files, BOM CSVs, or STEP models directly — the server provides renderable formats (images, JSON, GLB)
- Cost calculations happen server-side; the client only displays the result
- Comment persistence is a server-side file operation
- Export file selection and copying is server-side; the client sends the user's choices

---

### 7. Review Page Architecture (Plugin System)

The dashboard shell must make adding new review pages trivial. Each review page is a self-contained module that conforms to a standard interface. The shell handles all shared concerns (navigation, review state, comments).

**Standard Review Page Interface:**

```typescript
// Each review page registers itself via this interface
interface ReviewPageDefinition {
  id: string; // e.g. "3d-view", "gerber-viewer", "ibom"
  label: string; // Sidebar display name, e.g. "3D View"
  icon: React.ComponentType<{ size: number }>; // Sidebar icon (Lucide or custom)
  order: number; // Sort order in sidebar (10, 20, 30...)

  // Determine if this page can render given the current build outputs
  isAvailable: (outputs: BuildOutputs) => boolean;
}

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

interface ReviewComment {
  pageId: string;
  text: string;
  timestamp: string;
}
```

**How the shell uses this:**

1. The shell imports a `REVIEW_PAGES` registry (array of `{ definition, component }` pairs)
2. The left sidebar is generated from `REVIEW_PAGES`, filtered by `isAvailable(outputs)`
3. The shell renders the active page's component, injecting standard `ReviewPageProps`
4. The shell renders the shared "Mark as Reviewed" and "Comment" UI chrome around (or overlaid on) the page component
5. Review state and comments are managed centrally in the Zustand store

**Adding a new review page requires only:**

1. Create a React component that accepts `ReviewPageProps`
2. Add an entry to the `REVIEW_PAGES` registry with a `ReviewPageDefinition`
3. That's it — the shell handles sidebar entry, navigation, review tracking, and comments

**Initial review pages (Phase 1 — dashboard shell):**

| Page ID     | Component              | Available when       | Notes                          |
| ----------- | ---------------------- | -------------------- | ------------------------------ |
| `3d-view`   | `<ModelViewer>`        | `outputs.glb` exists | Reuse existing viewer          |
| `2d-render` | `<SvgViewer>`          | `outputs.svg` exists | Simple SVG embed with zoom/pan |
| `ibom`      | `<PlaceholderPage>`    | always               | Placeholder, separate project  |
| `gerber`    | `<PlaceholderPage>`    | always               | Placeholder, separate project  |
| `documents` | `<DocumentsChecklist>` | always               | Review summary + comments      |

**Future review pages (added by registering in `REVIEW_PAGES`):**

| Page ID      | Description                 |
| ------------ | --------------------------- |
| `testpoints` | Testpoint location viewer   |
| `power-tree` | Power distribution diagram  |
| `i2c-tree`   | I2C address tree viewer     |
| `parameters` | Solved parameter comparison |

---

### 7. Data Requirements

Each view needs specific data from the build system:

| View            | Data Source                                            | API                                                                   |
| --------------- | ------------------------------------------------------ | --------------------------------------------------------------------- |
| Build           | Build stages, git status                               | WebSocket `/ws/state`, `getManufacturingGitStatus`                    |
| 3D View         | GLB file                                               | `getManufacturingOutputs` → `outputs.glb`                             |
| 2D Render       | SVG file                                               | `getManufacturingOutputs` → new `outputs.svg` field                   |
| Interactive BOM | BOM JSON + LCSC data                                   | `refreshBOM`, `fetchLcscParts` (placeholder initially)                |
| Gerber Viewer   | Gerber files (individual layers or ZIP)                | `getManufacturingOutputs` → `outputs.gerbers` (placeholder initially) |
| Documents       | PCB summary, review comments, review completion status | `pcb_summary.json`, `review_comments.md`                              |
| Export          | All artifact paths, fab house config                   | `getManufacturingOutputs`, `exportManufacturingFiles`                 |
| Cost            | Board summary, BOM, fab house pricing                  | `getDetailedCostEstimate` (parameterized by fab house)                |

**New data/APIs needed:**

- SVG render path in `BuildOutputs` type (add `svg` field)
- Review comments file: `{build_output}/review_comments.md` — append-only markdown file with timestamped comments per review step
- API to read/write review comments (or handle client-side via file API)
- Fab house configuration: supported fab houses list, pricing model per house, order page URL per house
- Gerber Viewer: will need a different rendering approach than current `@tracespace` — either pygerber (Python-based, server-side rendering) or a custom GPU-based renderer (separate project)

### 7. State Management

Dashboard state to track:

- **Navigation**: Current active step/sub-step
- **Build**: Build status, progress stages, build ID, artifact verification results
- **Git**: Uncommitted changes status, changed files list
- **Review**:
  - Per-review-step completion status (`reviewed: boolean` per sub-step)
  - Per-review-step comments (text entered via "Comment" button, persisted to `review_comments.md`)
- **Export**:
  - Selected standard export file types (checkbox state)
  - Selected advanced export file types (checkbox state)
  - Output directory path
  - Selected fab house (dropdown value, default: JLCPCB)
  - PCB quantity (for fab cost)
  - PCBA quantity (for assembly + component cost)
- **Cost**: Estimate data (PCB, components, assembly, total), board summary
- **BOM**: Enriched component data with LCSC stock/price info

### 8. Acceptance Criteria

**Core dashboard:**

1. Dashboard opens as a full-screen tab (not sidebar panel)
2. Left sidebar shows all steps/sub-steps with visual completion indicators
3. User can navigate freely between steps (not forced linear)
4. Main content area adapts layout per step (single pane, split view, etc.)

**Build step:** 5. Build step shows real-time progress from backend stages 6. Clicking a build step opens the corresponding debug window 7. Build failure shows errors with link to Problems panel and retry button 8. Build success shows "Next" button (no auto-advance)

**Review steps:** 9. Each review sub-step has a "Mark as Reviewed" action 10. Each review sub-step has a "Comment" button that persists to `review_comments.md` 11. 3D View and 2D Render work with existing viewer components 12. Interactive BOM and Gerber Viewer can be placeholders initially (separate projects) 13. Documents/Checklist shows review completion status and all comments

**Export step:** 14. Export step shows selectable standard and advanced export checkboxes 15. Fab house selector dropdown works (JLCPCB default, extensible) 16. Separate PCB and PCBA quantity inputs 17. Cost estimation reflects selected fab house and quantities 18. Files are correctly exported to the chosen directory 19. "Go to [fab house]" button uses selected fab house URL

**General:** 20. Dashboard state persists within a session (not lost on tab switch)

### 10. Phasing

**The dashboard shell is the first and most important deliverable.** It establishes the full-screen layout, navigation, review page plugin system, and export flow. All review pages (including future ones) plug into this shell. Getting the shell right means every subsequent page is trivial to add.

**Phase 1 — Dashboard Shell (this project):**

This is the core deliverable. Everything else plugs into it.

1. **Full-screen tab infrastructure**: Register new webview tab type in VS Code extension, create entry point HTML, wire up the "Manufacture" button to open it
2. **Two-column layout**: Left sidebar (step navigator) + main content area
3. **Left sidebar navigation**: Renders Build / Review (sub-pages) / Export steps with completion indicators, generated from `REVIEW_PAGES` registry for the review section
4. **Review page plugin system**: Implement `ReviewPageDefinition` / `ReviewPageProps` interfaces, `REVIEW_PAGES` registry, shell renders active page component with injected props
5. **Shared review chrome**: "Mark as Reviewed" button and "Comment" button/dialog, rendered by the shell around each page component
6. **Review state + comments**: Zustand store slice for per-page review status, comments persisted to `review_comments.md`
7. **Build step**: Reuse existing build logic from `ManufacturingPanel.tsx` (git status, frozen build, stage progress, artifact verification)
8. **Export step**: Standard + advanced export checkboxes, fab house dropdown, PCB/PCBA quantity, directory selector, cost estimation, export action
9. **Initial review pages**: 3D View (existing `ModelViewer`), 2D Render (SVG embed), placeholder pages for iBOM and Gerber, Documents/Checklist page
10. **Documents/Checklist page**: Shows all review completion statuses, all comments, generated artifact list

**Phase 2 — Separate Projects (plug into Phase 1 shell):**

Each of these is an independent project that registers a new entry in `REVIEW_PAGES`:

- Interactive BOM viewer (rich table with search/filter/sort, LCSC enrichment)
- Gerber Viewer (pygerber or custom GPU renderer)
- Advanced exports (HQ render, AI README, manufacturing notes, power tree)
- Future review pages (testpoints, power tree, i2c tree, parameters)

### 10. Verification

- Manual testing: Open dashboard, run through full Build → Review → Export flow
- Verify 3D and 2D viewers render correctly with real build output
- Test "Comment" button on each review step, verify comments persist in `review_comments.md`
- Test export with different fab house selections
- Test with projects that have warnings (out-of-stock, uncommitted changes)
- Verify full-screen tab works in both VS Code webview and standalone dev mode
- Verify placeholder views (iBOM, Gerber) display graceful empty states

### Key Files Reference

- Current manufacturing UI: `src/ui-server/src/components/manufacturing/`
- Viewer components: `src/ui-server/src/components/ModelViewer.tsx`, `GerberViewer.tsx`, `KiCanvasEmbed.tsx`, `BOMPanel.tsx`
- Backend routes: `src/atopile/server/routes/manufacturing.py`
- Backend domain: `src/atopile/server/domains/manufacturing.py`, `cost_estimation.py`
- Store: `src/ui-server/src/store/index.ts`
- Types: `src/ui-server/src/components/manufacturing/types.ts`
- Build artifacts: `src/faebryk/exporters/` (bom, pcb, parameters, power_tree, documentation, testpoints)
- VS Code tab infrastructure: `src/vscode-atopile/src/ui/webview-base.ts`
- Review comments: `{build_output}/review_comments.md` (new file, created by dashboard)
