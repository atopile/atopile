# Layout Editor: Make `container` Required, Remove Global DOM Fallback

## Problem

The `Editor` class in `layout_server/frontend/src/editor.ts` has two modes for placing
its text overlay canvas:

1. **With `container`** (iBOM viewer): creates an absolutely-positioned overlay inside the
   container element. Coordinates use `0,0` as origin.
2. **Without `container`** (standalone layout editor): creates a `position: fixed` overlay
   appended to `document.body` with `100vw/100vh`, or reuses a global
   `#editor-text-overlay` element by ID.

Mode 2 is a hack — it assumes the editor owns the entire page, uses global DOM IDs, and
breaks if two editors exist on the same page. The `container` option was added as a
workaround so the iBOM viewer could embed the editor in a panel.

## Proposed Fix

Make `container` a required constructor parameter. The editor should always position its
overlay relative to a container, never assume it owns the whole page.

## Callers

There are only two callers of `new Editor(...)`:

| Caller | File | Currently passes container? |
|--------|------|---------------------------|
| iBOM viewer | `src/ui-server/src/components/interactive-bom/LayoutViewerWrapper.tsx` | Yes (`containerRef.current`) |
| Standalone layout editor | `src/atopile/layout_server/frontend/src/main.ts` | No |

## Implementation Steps

### Step 1: Update `main.ts` to pass a container

**File:** `src/atopile/layout_server/frontend/src/main.ts`

Wrap the canvas in a container `<div>` or use `canvas.parentElement`:

```ts
// Before:
const canvas = document.getElementById("editor-canvas") as HTMLCanvasElement;
const editor = new Editor(canvas, baseUrl, apiPrefix, wsPath);

// After:
const canvas = document.getElementById("editor-canvas") as HTMLCanvasElement;
const container = canvas.parentElement!;
const editor = new Editor(canvas, baseUrl, apiPrefix, wsPath, { container });
```

**File:** `src/atopile/layout_server/static/layout-editor.hbs`

Wrap the canvas in a positioned container so the overlay positions correctly:

```html
<!-- Before: -->
<canvas id="editor-canvas"></canvas>

<!-- After: -->
<div id="editor-container" style="position: relative; width: 100vw; height: 100vh;">
    <canvas id="editor-canvas"></canvas>
</div>
```

The canvas CSS already uses `position: fixed; width: 100vw; height: 100vh;` — move that
to the container `<div>` and make the canvas fill its parent instead.

### Step 2: Make `container` required in `Editor`

**File:** `src/atopile/layout_server/frontend/src/editor.ts`

```ts
// Before:
export interface EditorOptions {
    readOnly?: boolean;
    container?: HTMLElement;
}

// After:
export interface EditorOptions {
    readOnly?: boolean;
}

export class Editor {
    // ...
    private readonly container: HTMLElement;

    constructor(
        canvas: HTMLCanvasElement,
        baseUrl: string,
        apiPrefix = "/api",
        wsPath = "/ws",
        container: HTMLElement,
        options?: EditorOptions,
    ) {
        this.container = container;
        // ...
    }
}
```

### Step 3: Remove the global DOM fallback from `createTextOverlay()`

**File:** `src/atopile/layout_server/frontend/src/editor.ts`

Delete the `getElementById("editor-text-overlay")` branch and the `document.body.appendChild`
branch. Keep only the container-relative path:

```ts
private createTextOverlay(): HTMLCanvasElement {
    const overlay = document.createElement("canvas");
    overlay.style.position = "absolute";
    overlay.style.top = "0";
    overlay.style.left = "0";
    overlay.style.width = "100%";
    overlay.style.height = "100%";
    overlay.style.pointerEvents = "none";
    overlay.style.zIndex = "9";
    this.container.appendChild(overlay);
    return overlay;
}
```

### Step 4: Simplify `syncTextOverlayViewport()`

Remove the `this.container ?` ternary — it's always true now:

```ts
private syncTextOverlayViewport(
    viewport = this.getCanvasViewportMetrics(),
): void {
    const width = `${viewport.width}px`;
    const height = `${viewport.height}px`;
    if (this.textOverlay.style.left !== "0px") this.textOverlay.style.left = "0px";
    if (this.textOverlay.style.top !== "0px") this.textOverlay.style.top = "0px";
    if (this.textOverlay.style.width !== width) this.textOverlay.style.width = width;
    if (this.textOverlay.style.height !== height) this.textOverlay.style.height = height;
}
```

### Step 5: Update iBOM caller

**File:** `src/ui-server/src/components/interactive-bom/LayoutViewerWrapper.tsx`

Move `container` from options to a positional argument:

```ts
// Before:
const editor = new Editor(canvas, LAYOUT_BASE_URL, LAYOUT_API_PREFIX, LAYOUT_WS_PATH, {
    readOnly: true,
    container,
});

// After:
const editor = new Editor(canvas, LAYOUT_BASE_URL, LAYOUT_API_PREFIX, LAYOUT_WS_PATH, container, {
    readOnly: true,
});
```

### Step 6: Rebuild static assets

Rebuild `editor.js` so the bundled standalone editor in `layout_server/static/` and
`vscode-atopile/resources/layout-editor/` picks up the changes.

## Verification

1. Open the standalone layout editor (`ato serve layout`) — verify text overlay renders
   correctly and tracks the canvas viewport
2. Open the iBOM viewer from VS Code sidebar — verify text overlay renders inside the
   panel, not overflowing
3. Resize the window/panel — verify overlay resizes correctly in both modes
4. Open layout editor in VS Code webview — verify it works the same as standalone
