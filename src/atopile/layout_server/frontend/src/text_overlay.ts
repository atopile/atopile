import { Vec2 } from "./math";
import { fpTransform } from "./geometry";
import { getLayerColor } from "./colors";
import { layoutKicadStrokeLine } from "./kicad_stroke_font";
import { buildPadAnnotationGeometry } from "./pad_annotations";
import { footprintBBox } from "./hit-test";
import type { Camera2 } from "./camera";
import type { LayerModel, RenderModel } from "./types";

const DEG_TO_RAD = Math.PI / 180;
const PAD_ANNOTATION_FONT_STACK = "\"IBM Plex Mono\", \"Roboto Mono\", \"Menlo\", \"Consolas\", \"Liberation Mono\", \"DejaVu Sans Mono\", \"Courier New\", monospace";
const PAD_ANNOTATION_NAME_WEIGHT = 550;
const PAD_ANNOTATION_NUMBER_WEIGHT = 650;
const PAD_ANNOTATION_NUMBER_COLOR = "rgba(13, 20, 31, 0.98)";

type OverlayText = {
    text: string;
    worldX: number;
    worldY: number;
    rotationDeg: number;
    textWidth: number;
    textHeight: number;
    thickness: number | null;
    layerName: string;
    justify: string[] | null;
};

type OverlayRenderOptions = {
    clearCanvas?: boolean;
    worldOffset?: Vec2;
};

function drawPadAnnotationText(
    ctx: CanvasRenderingContext2D,
    camera: Camera2,
    viewportWidth: number,
    viewportHeight: number,
    text: string,
    worldX: number,
    worldY: number,
    rotationDeg: number,
    charH: number,
    color: string,
    fontWeight: number,
) {
    const lines = text
        .split("\n")
        .map(line => line.trim())
        .filter(line => line.length > 0);
    if (lines.length === 0) return;

    const screenPos = camera.world_to_screen(new Vec2(worldX, worldY));
    if (
        screenPos.x < -100
        || screenPos.x > viewportWidth + 100
        || screenPos.y < -100
        || screenPos.y > viewportHeight + 100
    ) {
        return;
    }
    const fontPx = Math.max(charH * Math.max(camera.zoom, 1e-6), 0.8);
    ctx.save();
    ctx.translate(screenPos.x, screenPos.y);
    ctx.rotate(-(rotationDeg || 0) * DEG_TO_RAD);
    ctx.font = `${fontWeight} ${fontPx}px ${PAD_ANNOTATION_FONT_STACK}`;
    (ctx as CanvasRenderingContext2D & { fontKerning?: CanvasFontKerning }).fontKerning = "normal";
    ctx.textAlign = "left";
    ctx.fillStyle = color;
    if (lines.length === 1) {
        ctx.textBaseline = "alphabetic";
        const metrics = ctx.measureText(lines[0]!);
        const left = metrics.actualBoundingBoxLeft ?? 0;
        const right = metrics.actualBoundingBoxRight ?? metrics.width;
        const ascent = metrics.actualBoundingBoxAscent ?? fontPx * 0.78;
        const descent = metrics.actualBoundingBoxDescent ?? fontPx * 0.22;
        const x = -((left + right) / 2);
        const y = (ascent - descent) / 2;
        ctx.fillText(lines[0]!, x, y);
    } else {
        // For multiline pad labels, center each line around the same anchor.
        const lineHeight = fontPx * 1.08;
        const centerLine = (lines.length - 1) / 2;
        ctx.textBaseline = "middle";
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i]!;
            const metrics = ctx.measureText(line);
            const left = metrics.actualBoundingBoxLeft ?? 0;
            const right = metrics.actualBoundingBoxRight ?? metrics.width;
            const x = -((left + right) / 2);
            const y = (i - centerLine) * lineHeight;
            ctx.fillText(line, x, y);
        }
    }
    ctx.restore();
}

function drawStrokeText(
    ctx: CanvasRenderingContext2D,
    camera: Camera2,
    layerById: Map<string, LayerModel>,
    viewportWidth: number,
    viewportHeight: number,
    spec: OverlayText,
) {
    const screenPos = camera.world_to_screen(new Vec2(spec.worldX, spec.worldY));
    if (
        screenPos.x < -100
        || screenPos.x > viewportWidth + 100
        || screenPos.y < -100
        || screenPos.y > viewportHeight + 100
    ) {
        return;
    }

    const lines = spec.text.split("\n");
    if (lines.length === 0) return;
    const justifySet = new Set(spec.justify ?? []);

    const [r, g, b, a] = getLayerColor(spec.layerName, layerById);
    const rotation = -(spec.rotationDeg || 0) * DEG_TO_RAD;
    const linePitch = spec.textHeight * 1.62;
    const totalHeight = spec.textHeight * 1.17 + Math.max(0, lines.length - 1) * linePitch;
    let baseOffsetY = spec.textHeight;
    if (justifySet.has("center") || (!justifySet.has("top") && !justifySet.has("bottom"))) {
        baseOffsetY -= totalHeight / 2;
    } else if (justifySet.has("bottom")) {
        baseOffsetY -= totalHeight;
    }
    const minWorldStroke = 0.8 / Math.max(camera.zoom, 1e-6);
    const worldStroke = Math.max(minWorldStroke, spec.thickness ?? (spec.textHeight * 0.15));
    ctx.save();
    ctx.translate(screenPos.x, screenPos.y);
    ctx.rotate(rotation);
    ctx.scale(camera.zoom, camera.zoom);
    const color = `rgba(${Math.round(r * 255)}, ${Math.round(g * 255)}, ${Math.round(b * 255)}, ${Math.max(a, 0.55)})`;
    ctx.strokeStyle = color;
    ctx.lineWidth = worldStroke;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    for (let lineIdx = 0; lineIdx < lines.length; lineIdx++) {
        const line = lines[lineIdx]!;
        const layout = layoutKicadStrokeLine(line, spec.textWidth, spec.textHeight);
        if (layout.strokes.length === 0) {
            continue;
        }
        let lineOffsetX = 0;
        if (justifySet.has("right")) {
            lineOffsetX = -layout.advance;
        } else if (justifySet.has("center") || (!justifySet.has("left") && !justifySet.has("right"))) {
            lineOffsetX = -layout.advance / 2;
        }
        const lineOffsetY = baseOffsetY + lineIdx * linePitch;
        for (const stroke of layout.strokes) {
            if (stroke.length < 2) continue;
            ctx.beginPath();
            ctx.moveTo(stroke[0]!.x + lineOffsetX, stroke[0]!.y + lineOffsetY);
            for (let i = 1; i < stroke.length; i++) {
                ctx.lineTo(stroke[i]!.x + lineOffsetX, stroke[i]!.y + lineOffsetY);
            }
            ctx.stroke();
        }
    }
    ctx.restore();
}

export function renderTextOverlay(
    ctx: CanvasRenderingContext2D,
    model: RenderModel | null,
    camera: Camera2,
    hiddenLayers: Set<string>,
    layerById: Map<string, LayerModel>,
    vpWidth?: number,
    vpHeight?: number,
    visibleFpIndices?: number[],
    options?: OverlayRenderOptions,
) {
    const dpr = Math.max(window.devicePixelRatio || 1, 1);
    // Prefer caller-supplied dimensions (from the WebGL canvas) so text and
    // geometry share the same coordinate space in VS Code webviews where
    // window.innerWidth/Height can differ from the actual canvas dimensions.
    const width = vpWidth ?? window.innerWidth;
    const height = vpHeight ?? window.innerHeight;
    const pixelWidth = Math.floor(width * dpr);
    const pixelHeight = Math.floor(height * dpr);
    let resized = false;
    if (ctx.canvas.width !== pixelWidth) {
        ctx.canvas.width = pixelWidth;
        resized = true;
    }
    if (ctx.canvas.height !== pixelHeight) {
        ctx.canvas.height = pixelHeight;
        resized = true;
    }
    const styleWidth = `${width}px`;
    const styleHeight = `${height}px`;
    if (ctx.canvas.style.width !== styleWidth) {
        ctx.canvas.style.width = styleWidth;
    }
    if (ctx.canvas.style.height !== styleHeight) {
        ctx.canvas.style.height = styleHeight;
    }
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    if (resized || options?.clearCanvas !== false) {
        ctx.clearRect(0, 0, width, height);
    }
    if (!model || camera.zoom < 1.5 || hiddenLayers.has("__type:pads")) return;
    const offset = options?.worldOffset ?? new Vec2(0, 0);

    const fpIndices = visibleFpIndices ?? [...Array(model.footprints.length).keys()];
    const minScreenSize = 60; // Increased threshold for tiny footprints

    for (const idx of fpIndices) {
        const fp = model.footprints[idx];
        if (!fp) continue;

        // Aggressive culling: if footprint is too small on screen, skip annotations
        const bbox = footprintBBox(fp);
        if (Math.max(bbox.w, bbox.h) * camera.zoom < minScreenSize) continue;

        // Note: buildPadAnnotationGeometry is already cached via WeakMap internally
        const annotationsByLayer = buildPadAnnotationGeometry(fp, hiddenLayers);
        
        // Sorting layers is still needed for correct overlap, but Map iteration is fast
        const layerNames = Array.from(annotationsByLayer.keys());
        if (layerNames.length > 1) {
            layerNames.sort((a, b) => {
                const orderA = layerById.get(a)?.paint_order ?? 999;
                const orderB = layerById.get(b)?.paint_order ?? 999;
                return orderA - orderB;
            });
        }

        for (const layerName of layerNames) {
            const geometry = annotationsByLayer.get(layerName)!;
            const [r, g, b, a] = getLayerColor(layerName, layerById);
            const color = `rgba(${Math.round(r * 255)}, ${Math.round(g * 255)}, ${Math.round(b * 255)}, ${Math.max(a, 0.7)})`;

            for (const name of geometry.names) {
                drawPadAnnotationText(
                    ctx,
                    camera,
                    width,
                    height,
                    name.text,
                    name.x + offset.x,
                    name.y + offset.y,
                    name.rotation,
                    name.charH,
                    color,
                    PAD_ANNOTATION_NAME_WEIGHT,
                );
            }

            for (const number of geometry.numbers) {
                const badgeX = number.badgeCenterX + offset.x;
                const badgeY = number.badgeCenterY + offset.y;
                const screenPos = camera.world_to_screen(new Vec2(badgeX, badgeY));
                const screenRadius = Math.max(number.badgeRadius * camera.zoom, 2); // Minimum 2px radius
                
                // Draw badge circle
                ctx.beginPath();
                ctx.arc(screenPos.x, screenPos.y, screenRadius, 0, 2 * Math.PI);
                ctx.fillStyle = color;
                ctx.fill();
                
                // Draw badge outline
                ctx.lineWidth = Math.max(screenRadius * 0.18, 0.8);
                ctx.strokeStyle = "rgba(13, 20, 31, 0.85)";
                ctx.stroke();

                if (!number.labelFit) continue;
                const [, charH] = number.labelFit;
                drawPadAnnotationText(
                    ctx,
                    camera,
                    width,
                    height,
                    number.text,
                    badgeX,
                    badgeY,
                    0,
                    charH,
                    PAD_ANNOTATION_NUMBER_COLOR,
                    PAD_ANNOTATION_NUMBER_WEIGHT,
                );
            }
        }
    }
}
