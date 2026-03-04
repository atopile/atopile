import { createRequire } from "node:module";
import process from "node:process";

const requireFromFrontend = createRequire(
    new URL("../../src/atopile/layout_server/frontend/package.json", import.meta.url),
);
const puppeteer = requireFromFrontend("puppeteer");

function parseArgs() {
    const args = process.argv.slice(2);
    let url = "";
    for (let i = 0; i < args.length; i++) {
        if (args[i] === "--url" && i + 1 < args.length) {
            url = args[i + 1];
            i++;
        }
    }
    if (!url) {
        throw new Error("Missing required --url argument");
    }
    return { url };
}

function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

function computeModelBBox(model) {
    const points = [];
    const push = (p) => {
        if (!p) return;
        if (!Number.isFinite(p.x) || !Number.isFinite(p.y)) return;
        points.push([p.x, p.y]);
    };

    for (const edge of model.board.edges || []) {
        push(edge.start);
        push(edge.end);
        push(edge.mid);
        push(edge.center);
    }
    for (const drawing of model.drawings || []) {
        if (drawing.type === "line") {
            push(drawing.start);
            push(drawing.end);
        } else if (drawing.type === "arc") {
            push(drawing.start);
            push(drawing.mid);
            push(drawing.end);
        } else if (drawing.type === "circle") {
            push(drawing.center);
            push(drawing.end);
        } else if (drawing.type === "rect") {
            push(drawing.start);
            push(drawing.end);
        } else if (drawing.type === "polygon" || drawing.type === "curve") {
            for (const p of drawing.points || []) push(p);
        }
    }
    for (const text of model.texts || []) push(text.at);
    for (const fp of model.footprints || []) {
        push(fp.at);
        for (const pad of fp.pads || []) push({ x: fp.at.x + pad.at.x, y: fp.at.y + pad.at.y });
        for (const text of fp.texts || []) push({ x: fp.at.x + text.at.x, y: fp.at.y + text.at.y });
    }
    for (const track of model.tracks || []) {
        push(track.start);
        push(track.end);
    }

    if (points.length === 0) {
        return { x: 0, y: 0, w: 100, h: 100 };
    }
    let minX = Infinity;
    let minY = Infinity;
    let maxX = -Infinity;
    let maxY = -Infinity;
    for (const [x, y] of points) {
        if (x < minX) minX = x;
        if (y < minY) minY = y;
        if (x > maxX) maxX = x;
        if (y > maxY) maxY = y;
    }
    return { x: minX - 5, y: minY - 5, w: (maxX - minX) + 10, h: (maxY - minY) + 10 };
}

async function getVisibleStaticVertexTotals(page) {
    return page.evaluate(() => {
        const editor = window.__layoutEditor;
        const stats = editor?.renderer?.get_layer_stats?.();
        if (!stats) return null;
        let lineVertices = 0;
        let polyVertices = 0;
        for (const layer of Object.values(stats)) {
            if (!layer.visible) continue;
            lineVertices += layer.lineVertices;
            polyVertices += layer.polyVertices;
        }
        return {
            lineVertices,
            polyVertices,
            totalVertices: lineVertices + polyVertices,
        };
    });
}

async function getOverlayRatio(page) {
    return page.evaluate(() => {
        let overlayRatio = 0;
        const overlay = document.getElementById("editor-text-overlay");
        if (overlay instanceof HTMLCanvasElement) {
            const octx = overlay.getContext("2d");
            if (octx) {
                const img = octx.getImageData(0, 0, overlay.width, overlay.height).data;
                let alphaPixels = 0;
                for (let i = 3; i < img.length; i += 4) {
                    if (img[i] > 0) alphaPixels++;
                }
                overlayRatio = alphaPixels / (overlay.width * overlay.height);
            }
        }
        return overlayRatio;
    });
}

async function getFootprintPos(page, uuid) {
    return page.evaluate((uuid) => {
        const editor = window.__layoutEditor;
        const model = editor?.model;
        if (!model) return null;
        const footprint = model.footprints.find((candidate) => candidate?.uuid === uuid);
        if (!footprint) return null;
        return { x: footprint.at.x, y: footprint.at.y };
    }, uuid);
}

async function getDragWorldDelta(page, sx, sy, ex, ey) {
    return page.evaluate(({ sx, sy, ex, ey }) => {
        const editor = window.__layoutEditor;
        if (!editor?.camera) return null;
        const start = editor.camera.screen_to_world({ x: sx, y: sy });
        const end = editor.camera.screen_to_world({ x: ex, y: ey });
        return { dx: end.x - start.x, dy: end.y - start.y };
    }, { sx, sy, ex, ey });
}

async function clickLayerRow(page, label) {
    return page.evaluate((label) => {
        const rows = [...document.querySelectorAll(".layer-row")];
        const row = rows.find((candidate) => {
            const spans = candidate.querySelectorAll("span");
            const text = spans.length > 0 ? spans[spans.length - 1].textContent?.trim() : "";
            return text === label;
        });
        if (!row) return false;
        row.dispatchEvent(new MouseEvent("click", { bubbles: true }));
        return true;
    }, label);
}

async function checkZoneDepthInvariant(page) {
    return page.evaluate(() => {
        const editor = window.__layoutEditor;
        if (!editor || !editor.renderer) {
            return { ok: false, violations: ["editor_not_exposed"] };
        }
        const layers = editor.renderer.layers;
        const copperLayers = editor
            .getLayerModels()
            .filter((layer) => layer.kind === "Cu")
            .map((layer) => layer.id);
        const violations = [];
        for (const layerName of copperLayers) {
            const zoneLayer = layers.get(`zone:${layerName}`);
            const copperLayer = layers.get(layerName);
            if (!zoneLayer || !copperLayer) continue;
            if (!(zoneLayer.depth < copperLayer.depth)) {
                violations.push(layerName);
            }
        }
        return { ok: violations.length === 0, violations };
    });
}

async function main() {
    const { url } = parseArgs();
    const browser = await puppeteer.launch({ headless: "new", args: ["--no-sandbox"] });
    const page = await browser.newPage();
    await page.setViewport({ width: 1440, height: 920 });

    const t0 = Date.now();
    await page.goto(url, { waitUntil: "networkidle2", timeout: 120000 });
    await page.waitForSelector("#editor-canvas", { timeout: 120000 });
    await sleep(500);

    const model = await page.evaluate(async () => (await fetch("/api/render-model")).json());
    const bbox = computeModelBBox(model);
    const fp = model.footprints.find((candidate) => (candidate.pads || []).length > 0) || model.footprints[0];
    if (!fp) {
        throw new Error("No footprint found in render model");
    }

    const viewport = page.viewport();
    const vw = viewport?.width || 1440;
    const vh = viewport?.height || 920;
    const zoom = Math.min(vw / bbox.w, vh / bbox.h);
    const centerX = bbox.x + bbox.w / 2;
    const centerY = bbox.y + bbox.h / 2;
    const sx = ((fp.at.x - centerX) * zoom) + (vw / 2);
    const sy = ((fp.at.y - centerY) * zoom) + (vh / 2);
    const dragDx = 64;
    const dragDy = 38;
    const ex = sx + dragDx;
    const ey = sy + dragDy;

    await page.mouse.move(sx, sy);
    for (let i = 0; i < 14; i++) {
        await page.mouse.wheel({ deltaY: -240 });
    }
    await sleep(900);

    const baseVertices = await getVisibleStaticVertexTotals(page);
    const padsToggleOk = await clickLayerRow(page, "Pads");
    await sleep(250);
    const padsOffVertices = await getVisibleStaticVertexTotals(page);
    const padsRestoreOk = await clickLayerRow(page, "Pads");
    await sleep(250);
    const padsOnVertices = await getVisibleStaticVertexTotals(page);

    const zonesToggleOk = await clickLayerRow(page, "Zones");
    await sleep(250);
    const zonesOffVertices = await getVisibleStaticVertexTotals(page);
    const zonesRestoreOk = await clickLayerRow(page, "Zones");
    await sleep(250);
    const zonesOnVertices = await getVisibleStaticVertexTotals(page);

    const zOrder = await checkZoneDepthInvariant(page);
    const overlayBeforeRatio = await getOverlayRatio(page);
    const expectedDelta = await getDragWorldDelta(page, sx, sy, ex, ey);
    const startPos = await getFootprintPos(page, fp.uuid);
    const downStart = Date.now();
    await page.mouse.down();
    const downMs = Date.now() - downStart;
    await page.mouse.move(ex, ey, { steps: 1 });
    await sleep(120);
    const overlayDuringRatio = await getOverlayRatio(page);
    await page.mouse.up();
    const posAfterImmediate = await getFootprintPos(page, fp.uuid);
    const overlayAfterRatio = await getOverlayRatio(page);
    await sleep(220);
    const posAfterSettled = await getFootprintPos(page, fp.uuid);

    const result = {
        timings: {
            initialLoadMs: Date.now() - t0,
            downMs,
        },
        drag: {
            startPos,
            expectedDelta,
            posAfterImmediate,
            posAfterSettled,
            overlayBeforeRatio: overlayBeforeRatio ?? 0,
            overlayDuringRatio: overlayDuringRatio ?? 0,
            overlayAfterRatio: overlayAfterRatio ?? 0,
        },
        filters: {
            padsToggleOk,
            padsRestoreOk,
            zonesToggleOk,
            zonesRestoreOk,
            baseVertices,
            padsOffVertices,
            padsOnVertices,
            zonesOffVertices,
            zonesOnVertices,
        },
        zOrder,
    };

    console.log(JSON.stringify(result));
    await browser.close();
}

main().catch(async (err) => {
    console.error(String(err?.stack || err));
    process.exit(1);
});
