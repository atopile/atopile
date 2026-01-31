# Projects Panel - Build State Display Specification

This document defines how build state should be displayed in the Projects Panel UI.

## Overview

The Projects Panel displays projects and their build targets. Each level (project and build) has distinct behaviors for displaying build state, action buttons, and status indicators.

---

## Build Card (Individual Build Target)

### When NOT Building (`status !== 'building'`)

| Element | Behavior |
|---------|----------|
| Error indicator | Visible if `errors > 0`, clickable to filter problems |
| Warning indicator | Visible if `warnings > 0`, clickable to filter problems |
| Duration/Last build | Shows one of: build duration, or "time since last build" with status icon | # for build target, show time since last build, for stages show build duration
| Play button | Hidden by default, slides in from right on hover |
| Indicators | Slide left on hover to make room for play button |

### When Building (`status === 'building'`)

| Element | Behavior |
|---------|----------|
| Error indicator | **Hidden** |
| Warning indicator | **Hidden** |
| Duration/Last build | **Hidden** |
| Elapsed time | Visible, shows live elapsed time with clock icon |
| Stop button | Slides in from right on hover |
| Indicators | Stay in place (don't slide) |

### Button Specifications (Build Card)

| Property | Play Button | Stop Button |
|----------|-------------|-------------|
| Size | 18px diameter | 18px diameter |
| Icon size | 10px | 10px |
| Border | 1px solid var(--ato-orange) | 1px solid var(--ato-orange) |
| Color | var(--ato-orange) | var(--ato-orange) |
| Position | absolute, right: 0 | absolute, right: 0 |
| Default opacity | 0 (hidden) | 0 (hidden) |
| On card hover | opacity: 1, slides in | opacity: 1, slides in |
| On button hover | Fills with orange | Fills with orange |

---

## Project Card (Contains Multiple Builds)

### Determining Build State

```javascript
const isBuilding = project.builds.some(b => b.status === 'building')
```

A project is considered "building" if **any** of its build targets has `status === 'building'`.

### When NOT Building (`isBuilding === false`)

| Element | Behavior |
|---------|----------|
| Error indicator | Visible if total errors > 0 across all builds |
| Warning indicator | Visible if total warnings > 0 across all builds |
| Last build info | Shows timestamp and status icon of most recent build |
| Play button | Hidden by default, slides in from right on hover |
| Indicators | Slide left on hover to make room for play button |

### When Building (`isBuilding === true`)

| Element | Behavior |
|---------|----------|
| Spinner | Visible (Loader2 icon, spinning) |
| Error indicator | **Hidden** |
| Warning indicator | **Hidden** |
| Last build info | **Hidden** |
| Stop button | **Always visible** (not just on hover) |
| Indicators | Stay in place (don't slide) |

### Button Specifications (Project Card)

| Property | Play Button | Stop Button |
|----------|-------------|-------------|
| Size | 22px diameter | 22px diameter |
| Icon size | 10px (Play: 14px) | 12px |
| Border | 1.5px solid var(--ato-orange) | 1.5px solid var(--ato-orange) |
| Color | var(--ato-orange) | var(--ato-orange) |
| Position | absolute, right: 0 | absolute, right: 0 |
| Default opacity | 0 (hidden) | **1 (always visible)** |
| On card hover | opacity: 1, slides in | Already visible |
| On button hover | Fills with orange | Fills with orange |

### Stop Button Action

When clicked, the stop button should cancel **all running builds** in that project:

```javascript
project.builds
  .filter(b => b.status === 'building' && b.buildId)
  .forEach(b => onCancelBuild?.(b.buildId!))
```

---

## CSS Classes

### Project Card Classes

| Class | Condition |
|-------|-----------|
| `.project-card` | Always present |
| `.project-card.selected` | When project is selected |
| `.project-card.expanded` | When project is expanded |
| `.project-card.collapsed` | When project is collapsed |
| `.project-card.building` | When `isBuilding === true` |

### Build Card Classes

| Class | Condition |
|-------|-----------|
| `.build-card` | Always present |
| `.build-card.selected` | When build is selected |
| `.build-card.building` | When `status === 'building'` |

---

## Hover Behavior Summary

### Non-Building State
1. User hovers over card
2. Indicators slide left (transform: translateX(-26px) for project, -22px for build)
3. Indicators fade slightly (opacity: 0.7)
4. Play button slides in from right (opacity: 0 → 1, translateX(8px) → 0)

### Building State
1. Indicators stay in place (no slide)
2. Stop button is visible (project level) or slides in on hover (build level)
3. Only elapsed time is shown, no other indicators

---

## Data Flow

### Build Status Values
- `'idle'` - No build running, no previous build
- `'queued'` - Build is queued
- `'building'` - Build is actively running
- `'success'` - Last build succeeded
- `'error'` - Last build failed
- `'warning'` - Last build completed with warnings
- `'cancelled'` - Build was cancelled

### Required Properties for Building State

For a build to be properly tracked as "building":
```typescript
interface BuildTarget {
  status: 'building'  // Must be 'building'
  buildId?: string    // Required for cancellation
  elapsedSeconds?: number  // For elapsed time display
  currentStage?: string    // Optional: current stage name
}
```

---

## Known Issues / Debug Notes

### Issue: All projects show as building when only one should be

**Symptoms:**
- All project cards display the stop button
- All project cards have the spinner visible
- `isBuilding` evaluates to `true` for all projects

**Debugging Steps:**
1. Check console logs for `[ProjectNode] {name} isBuilding=true` messages
2. Check that `project.builds` array contains the correct build objects per project
3. Verify each build's `status` property is being set correctly
4. Check server/WebSocket data is sending correct status per build
5. Look for shared references (all projects pointing to same builds array)

**Debug logging already in place:**
```javascript
// In ProjectNode (line ~1707)
if (isBuilding) {
  console.log(`[ProjectNode] ${project.name} isBuilding=true, builds:`,
    project.builds.map(b => ({ name: b.name, status: b.status })))
}

// In Sidebar (line ~427)
console.log('[Sidebar] Transformed projects:', combined.map(p => ({
  id: p.id,
  name: p.name,
  buildsWithStatus: p.builds?.map((b: any) => ({
    name: b.name,
    status: b.status,
    isBuilding: b.status === 'building',
  })),
})));
```

### Issue: Packages appearing in Projects section

**Expected behavior:**
- Projects section (`filterType="projects"`) shows only items with `type === 'project'`
- Packages section (`filterType="packages"`) shows only items with `type === 'package'`

**If packages appear in Projects section:**
1. Check the `type` property on each transformed item
2. Verify Sidebar.tsx correctly sets:
   - `type: 'project'` for items from `state.projects`
   - `type: 'package'` for items from `state.packages`
3. Check ProjectsPanel filtering logic at line ~2088:
   ```javascript
   if (filterType === 'projects' && project.type !== 'project') return false
   if (filterType === 'packages' && project.type !== 'package') return false
   ```

### Data Flow

```
Dev Server WebSocket → AppState
    ↓
state.projects → transformedProjects (type: 'project')
state.packages → transformedPackages (type: 'package')
    ↓
Combined → projects array (both types)
    ↓
ProjectsPanel with filterType
    ↓
filteredProjects (filtered by type)
    ↓
Rendered as ProjectNode (type=project) or PackageCard (type=package)
```
