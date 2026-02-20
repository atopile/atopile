import { Vec2 } from "./math";
import { fpTransform } from "./geometry";
import { getLayerColor } from "./colors";
import { layoutKicadStrokeLine } from "./kicad_stroke_font";
import type { Camera2 } from "./camera";
import type { LayerModel, RenderModel } from "./types";

const DEG_TO_RAD = Math.PI / 180;

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
) {
    const dpr = Math.max(window.devicePixelRatio || 1, 1);
    const width = window.innerWidth;
    const height = window.innerHeight;
    ctx.canvas.width = Math.floor(width * dpr);
    ctx.canvas.height = Math.floor(height * dpr);
    ctx.canvas.style.width = `${width}px`;
    ctx.canvas.style.height = `${height}px`;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, width, height);
    if (!model || camera.zoom < 0.2) return;

    for (const text of model.texts) {
        if (!text.text.trim()) continue;
        const layerName = text.layer;
        if (!layerName) continue;
        if (hiddenLayers.has(layerName)) continue;
        drawStrokeText(ctx, camera, layerById, width, height, {
            text: text.text,
            worldX: text.at.x,
            worldY: text.at.y,
            rotationDeg: text.at.r || 0,
            textWidth: text.size?.w ?? 1.0,
            textHeight: text.size?.h ?? 1.0,
            thickness: text.thickness ?? null,
            layerName,
            justify: text.justify,
        });
    }

    for (const fp of model.footprints) {
        for (const text of fp.texts) {
            if (!text.text.trim()) continue;
            const layerName = text.layer;
            if (!layerName) continue;
            if (hiddenLayers.has(layerName)) continue;
            const worldPos = fpTransform(fp.at, text.at.x, text.at.y);
            const textRotation = (fp.at.r || 0) + (text.at.r || 0);
            drawStrokeText(ctx, camera, layerById, width, height, {
                text: text.text,
                worldX: worldPos.x,
                worldY: worldPos.y,
                rotationDeg: textRotation,
                textWidth: text.size?.w ?? 1.0,
                textHeight: text.size?.h ?? 1.0,
                thickness: text.thickness ?? null,
                layerName,
                justify: text.justify,
            });
        }
    }
}
