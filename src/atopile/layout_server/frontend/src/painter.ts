import { Vec2, BBox } from "./math";
import { Renderer, RenderLayer } from "./webgl/renderer";
import { fpTransform, padTransform } from "./geometry";
import {
    getLayerColor,
    ZONE_COLOR_ALPHA,
} from "./colors";
import type {
    RenderModel,
    FootprintModel,
    HoleModel,
    PadModel,
    TrackModel,
    ViaModel,
    DrawingModel,
    Point2,
    Point3,
    LayerModel,
    TextModel,
    ZoneModel,
} from "./types";
import { footprintBBox } from "./hit-test";
import { buildPadAnnotationGeometry } from "./pad_annotations";
import { layoutKicadStrokeLine } from "./kicad_stroke_font";

const HOLE_SEGMENTS = 36;
const SELECTION_STROKE_WIDTH = 0.12;
const GROUP_SELECTION_STROKE_WIDTH = 0.1;
const HOVER_SELECTION_STROKE_WIDTH = 0.08;
const SELECTION_GROW = 0.2;
const GROUP_SELECTION_GROW = 0.16;
const HOVER_SELECTION_GROW = 0.12;

export interface DragSelection {
    footprintIndices?: Set<number>;
    trackUuids?: Set<string>;
    viaUuids?: Set<string>;
    drawingUuids?: Set<string>;
    textUuids?: Set<string>;
    zoneUuids?: Set<string>;
}

function footprintOwnerId(footprint: FootprintModel, fallbackIndex: number): string {
    return footprint.uuid ? `fp:${footprint.uuid}` : `fp_idx:${fallbackIndex}`;
}

function trackOwnerId(track: TrackModel): string | null {
    return track.uuid ? `trk:${track.uuid}` : null;
}

function viaOwnerId(via: ViaModel): string | null {
    return via.uuid ? `via:${via.uuid}` : null;
}

function drawingOwnerId(drawing: DrawingModel): string | null {
    return drawing.uuid ? `drw:${drawing.uuid}` : null;
}

function textOwnerId(text: TextModel): string | null {
    return text.uuid ? `txt:${text.uuid}` : null;
}

function zoneOwnerId(zone: ZoneModel): string | null {
    return zone.uuid ? `zon:${zone.uuid}` : null;
}

export function buildDragOwnerIds(model: RenderModel, dragged: DragSelection): Set<string> {
    const owners = new Set<string>();
    const footprintIndices = dragged.footprintIndices ?? new Set<number>();
    for (const index of footprintIndices) {
        const footprint = model.footprints[index];
        if (!footprint) continue;
        owners.add(footprintOwnerId(footprint, index));
    }
    const trackUuids = dragged.trackUuids ?? new Set<string>();
    for (const uuid of trackUuids) {
        owners.add(`trk:${uuid}`);
    }
    const viaUuids = dragged.viaUuids ?? new Set<string>();
    for (const uuid of viaUuids) {
        owners.add(`via:${uuid}`);
    }
    const drawingUuids = dragged.drawingUuids ?? new Set<string>();
    for (const uuid of drawingUuids) {
        owners.add(`drw:${uuid}`);
    }
    const textUuids = dragged.textUuids ?? new Set<string>();
    for (const uuid of textUuids) {
        owners.add(`txt:${uuid}`);
    }
    const zoneUuids = dragged.zoneUuids ?? new Set<string>();
    for (const uuid of zoneUuids) {
        owners.add(`zon:${uuid}`);
    }
    return owners;
}


function p2v(p: Point2): Vec2 {
    return new Vec2(p.x, p.y);
}

/** Approximate a 3-point arc with line segments */
function arcToPoints(start: Point2, mid: Point2, end: Point2, segments = 32): Vec2[] {
    const ax = start.x, ay = start.y;
    const bx = mid.x, by = mid.y;
    const cx = end.x, cy = end.y;

    const D = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by));
    if (Math.abs(D) < 1e-10) {
        return [new Vec2(ax, ay), new Vec2(bx, by), new Vec2(cx, cy)];
    }

    const ux = ((ax * ax + ay * ay) * (by - cy) + (bx * bx + by * by) * (cy - ay) + (cx * cx + cy * cy) * (ay - by)) / D;
    const uy = ((ax * ax + ay * ay) * (cx - bx) + (bx * bx + by * by) * (ax - cx) + (cx * cx + cy * cy) * (bx - ax)) / D;
    const radius = Math.sqrt((ax - ux) ** 2 + (ay - uy) ** 2);
    const startAngle = Math.atan2(ay - uy, ax - ux);
    const midAngle = Math.atan2(by - uy, bx - ux);
    const endAngle = Math.atan2(cy - uy, cx - ux);

    let da1 = midAngle - startAngle;
    while (da1 > Math.PI) da1 -= 2 * Math.PI;
    while (da1 < -Math.PI) da1 += 2 * Math.PI;

    const clockwise = da1 < 0;
    let sweep = endAngle - startAngle;
    if (clockwise) {
        while (sweep > 0) sweep -= 2 * Math.PI;
    } else {
        while (sweep < 0) sweep += 2 * Math.PI;
    }

    const points: Vec2[] = [];
    for (let i = 0; i <= segments; i++) {
        const t = i / segments;
        const angle = startAngle + sweep * t;
        points.push(new Vec2(ux + radius * Math.cos(angle), uy + radius * Math.sin(angle)));
    }
    return points;
}

function circleToPoints(cx: number, cy: number, radius: number, segments = HOLE_SEGMENTS): Vec2[] {
    const points: Vec2[] = [];
    if (radius <= 0) return points;
    for (let i = 0; i <= segments; i++) {
        const angle = (i / segments) * 2 * Math.PI;
        points.push(new Vec2(cx + radius * Math.cos(angle), cy + radius * Math.sin(angle)));
    }
    return points;
}

function drawFootprintSelectionBox(
    layer: RenderLayer,
    fp: FootprintModel,
    strokeWidth: number,
    strokeAlpha: number,
    grow: number,
    fillAlpha = 0,
) {
    const bbox = footprintBBox(fp).grow(grow);
    if (bbox.w <= 0 || bbox.h <= 0) return;
    const corners = [
        new Vec2(bbox.x, bbox.y),
        new Vec2(bbox.x2, bbox.y),
        new Vec2(bbox.x2, bbox.y2),
        new Vec2(bbox.x, bbox.y2),
        new Vec2(bbox.x, bbox.y),
    ];
    if (fillAlpha > 0) {
        layer.geometry.add_polygon(corners.slice(0, 4), 1.0, 1.0, 1.0, fillAlpha);
    }
    layer.geometry.add_polyline(corners, strokeWidth, 1.0, 1.0, 1.0, strokeAlpha);
}

function buildLayerMap(model: RenderModel): Map<string, LayerModel> {
    const layerById = new Map<string, LayerModel>();
    for (const layer of model.layers) {
        layerById.set(layer.id, layer);
    }
    return layerById;
}

function layerPaintOrder(layerName: string, layerById: Map<string, LayerModel>): number {
    return layerById.get(layerName)?.paint_order ?? Number.MAX_SAFE_INTEGER;
}

function layerKind(layerName: string, layerById: Map<string, LayerModel>): string {
    return (layerById.get(layerName)?.kind ?? "").toLowerCase();
}

function zoneRenderLayerName(layerName: string): string {
    return `zone:${layerName}`;
}

function sortedLayerEntries<T>(
    layerMap: Map<string, T>,
    layerById: Map<string, LayerModel>,
): Array<[string, T]> {
    return [...layerMap.entries()].sort(([a], [b]) => {
        const orderDiff = layerPaintOrder(a, layerById) - layerPaintOrder(b, layerById);
        if (orderDiff !== 0) return orderDiff;
        return a.localeCompare(b);
    });
}

function isTextHidden(hidden: Set<string>): boolean {
    return hidden.has("__type:text") || hidden.has("__type:text_shapes") || hidden.has("__type:other");
}

function isShapesHidden(hidden: Set<string>): boolean {
    return hidden.has("__type:shapes") || hidden.has("__type:text_shapes") || hidden.has("__type:other");
}

/** Internal helper to group and paint a set of objects */
function paintObjects(
    renderer: Renderer,
    layerById: Map<string, LayerModel>,
    modelDrawings: DrawingModel[],
    modelTexts: TextModel[],
    modelTracks: TrackModel[],
    modelVias: ViaModel[],
    footprints: FootprintModel[],
    hidden: Set<string>,
    footprintOwnerByRef: Map<FootprintModel, string>,
    tint?: [number, number, number]
) {
    const showText = !isTextHidden(hidden);
    const showShapes = !isShapesHidden(hidden);
    const showTracks = !hidden.has("__type:tracks");
    const showPads = !hidden.has("__type:pads");

    // Bulk group all objects by layer
    const drawingsByLayer = new Map<string, Array<{ at: Point3; d: DrawingModel; ownerId: string | null }>>();
    const tracksByLayer = new Map<string, Array<{ t: TrackModel; ownerId: string | null }>>();
    const viasByLayer = new Map<string, Array<{ v: ViaModel; ownerId: string | null }>>();
    const drillViasByLayer = new Map<string, Array<{ v: ViaModel; ownerId: string | null }>>();
    const padsByLayer = new Map<string, Array<{ at: Point3; p: PadModel; ownerId: string | null }>>();
    const padHolesByLayer = new Map<string, Array<{ at: Point3; p: PadModel; h: HoleModel; ownerId: string | null }>>();
    const textsByLayer = new Map<string, Array<{ at: Point3; t: TextModel; ownerId: string | null }>>();

    const addDrawing = (layer: string, at: Point3, d: DrawingModel, ownerId: string | null) => {
        let arr = drawingsByLayer.get(layer);
        if (!arr) { arr = []; drawingsByLayer.set(layer, arr); }
        arr.push({ at, d, ownerId });
    };

    // Drawings and texts
    const worldAt: Point3 = { x: 0, y: 0, r: 0 };
    if (showShapes) {
        for (const d of modelDrawings) {
            if (!d.layer || hidden.has(d.layer)) continue;
            addDrawing(d.layer, worldAt, d, drawingOwnerId(d));
        }
    }
    if (showText) {
        for (const t of modelTexts) {
            if (!t.layer || hidden.has(t.layer)) continue;
            let arr = textsByLayer.get(t.layer);
            if (!arr) { arr = []; textsByLayer.set(t.layer, arr); }
            arr.push({ at: worldAt, t, ownerId: textOwnerId(t) });
        }
    }

    // Tracks and Vias
    if (showTracks) {
        for (const track of modelTracks) {
            if (!track.layer || hidden.has(track.layer)) continue;
            let arr = tracksByLayer.get(track.layer);
            if (!arr) { arr = []; tracksByLayer.set(track.layer, arr); }
            arr.push({ t: track, ownerId: trackOwnerId(track) });
        }
        for (const via of modelVias) {
            const ownerId = viaOwnerId(via);
            for (const l of via.copper_layers) {
                if (hidden.has(l)) continue;
                let arr = viasByLayer.get(l);
                if (!arr) { arr = []; viasByLayer.set(l, arr); }
                arr.push({ v: via, ownerId });
            }
            for (const l of via.drill_layers) {
                if (hidden.has(l)) continue;
                let arr = drillViasByLayer.get(l);
                if (!arr) { arr = []; drillViasByLayer.set(l, arr); }
                arr.push({ v: via, ownerId });
            }
        }
    }

    // Footprints
    for (const fp of footprints) {
        const ownerId = footprintOwnerByRef.get(fp) ?? null;
        if (showShapes) {
            for (const d of fp.drawings) {
                if (!d.layer || hidden.has(d.layer)) continue;
                addDrawing(d.layer, fp.at, d, ownerId);
            }
        }
        if (showText) {
            for (const t of fp.texts) {
                if (!t.layer || hidden.has(t.layer)) continue;
                let arr = textsByLayer.get(t.layer);
                if (!arr) { arr = []; textsByLayer.set(t.layer, arr); }
                arr.push({ at: fp.at, t, ownerId });
            }
        }
        if (showPads) {
            for (const p of fp.pads) {
                const hasHole = !!p.hole && Math.max(0, p.hole.size_x || 0) > 0;
                for (const l of p.layers) {
                    if (hidden.has(l)) continue;
                    if (isDrillLayer(l, layerById)) continue;
                    if ((p.type || "").toLowerCase() === "np_thru_hole") continue;
                    if (hasHole && !isCopperLayer(l, layerById)) continue;
                    let arr = padsByLayer.get(l);
                    if (!arr) { arr = []; padsByLayer.set(l, arr); }
                    arr.push({ at: fp.at, p, ownerId });
                }
                if (p.hole) {
                    for (const dl of padDrillLayerIds(p, layerById)) {
                        if (hidden.has(dl)) continue;
                        let arr = padHolesByLayer.get(dl);
                        if (!arr) { arr = []; padHolesByLayer.set(dl, arr); }
                        arr.push({ at: fp.at, p, h: p.hole, ownerId });
                    }
                }
            }
        }
    }

    // Paint in order
    const allLayerNames = new Set([
        ...drawingsByLayer.keys(), ...tracksByLayer.keys(), ...viasByLayer.keys(),
        ...drillViasByLayer.keys(), ...padsByLayer.keys(), ...padHolesByLayer.keys(),
        ...textsByLayer.keys()
    ]);

    const sortedNames = [...allLayerNames].sort((a, b) => layerPaintOrder(a, layerById) - layerPaintOrder(b, layerById));

    for (const ln of sortedNames) {
        let [r, g, b, a] = getLayerColor(ln, layerById);
        if (tint) {
            [r, g, b] = tint;
            a = 1.0;
        }
        const layer = renderer.get_layer(ln);
        
        const tracks = tracksByLayer.get(ln);
        if (tracks) for (const { t, ownerId } of tracks) {
            const pts = t.mid ? arcToPoints(t.start, t.mid, t.end) : [p2v(t.start), p2v(t.end)];
            layer.geometry.add_polyline(pts, t.width, r, g, b, a, ownerId);
        }

        const vias = viasByLayer.get(ln);
        if (vias) for (const { v, ownerId } of vias) {
            const outerD = v.size, drillD = v.drill;
            if (drillD > 0 && outerD > drillD) {
                const ringPoints = circleToPoints(v.at.x, v.at.y, (outerD + drillD) / 4);
                layer.geometry.add_polyline(ringPoints, (outerD - drillD) / 2, r, g, b, Math.max(a, 0.78), ownerId);
            } else if (outerD > 0) {
                layer.geometry.add_circle(v.at.x, v.at.y, outerD / 2, r, g, b, Math.max(a, 0.78), ownerId);
            }
        }

        const pads = padsByLayer.get(ln);
        if (pads) for (const { at, p, ownerId } of pads) paintPad(layer, at, p, ln, layerById, ownerId);

        const drawings = drawingsByLayer.get(ln);
        if (drawings) for (const { at, d, ownerId } of drawings) paintDrawing(layer, at, d, r, g, b, a, ownerId);

        const texts = textsByLayer.get(ln);
        if (texts) for (const { at, t, ownerId } of texts) paintText(layer, at, t, r, g, b, a, ownerId);

        const dvias = drillViasByLayer.get(ln);
        if (dvias) for (const { v, ownerId } of dvias) layer.geometry.add_circle(v.at.x, v.at.y, v.drill / 2, r, g, b, a, ownerId);

        const pholes = padHolesByLayer.get(ln);
        if (pholes) for (const { at, p, h, ownerId } of pholes) paintPadHole(layer, at, p, h, r, g, b, a, ownerId);
    }
}

/** Paint the entire render model into renderer layers */
export function paintStaticBoard(
    renderer: Renderer,
    model: RenderModel,
    hiddenLayers?: Set<string>,
    skipped?: DragSelection,
): void {
    const hidden = hiddenLayers ?? new Set<string>();
    const layerById = buildLayerMap(model);
    renderer.dispose_layers();
    if (!hidden.has("Edge.Cuts")) paintBoardEdges(renderer, model, layerById);

    const skipFootprints = skipped?.footprintIndices;
    const skipTracks = skipped?.trackUuids;
    const skipVias = skipped?.viaUuids;
    const skipDrawings = skipped?.drawingUuids;
    const skipTexts = skipped?.textUuids;
    const skipZones = skipped?.zoneUuids;

    const footprints: FootprintModel[] = [];
    for (let i = 0; i < model.footprints.length; i++) {
        if (!skipFootprints?.has(i)) footprints.push(model.footprints[i]!);
    }
    const tracks = skipTracks
        ? model.tracks.filter(track => !track.uuid || !skipTracks.has(track.uuid))
        : model.tracks;
    const vias = skipVias
        ? model.vias.filter(via => !via.uuid || !skipVias.has(via.uuid))
        : model.vias;
    const drawings = skipDrawings
        ? model.drawings.filter(drawing => !drawing.uuid || !skipDrawings.has(drawing.uuid))
        : model.drawings;
    const texts = skipTexts
        ? model.texts.filter(text => !text.uuid || !skipTexts.has(text.uuid))
        : model.texts;
    const zones = skipZones
        ? model.zones.filter(zone => !zone.uuid || !skipZones.has(zone.uuid))
        : model.zones;
    const footprintOwnerByRef = new Map<FootprintModel, string>();
    for (let i = 0; i < model.footprints.length; i++) {
        const footprint = model.footprints[i];
        if (!footprint) continue;
        footprintOwnerByRef.set(footprint, footprintOwnerId(footprint, i));
    }

    // Zones should render below tracks/pads for every copper layer.
    paintZones(renderer, model, hidden, layerById, zones);

    paintObjects(
        renderer,
        layerById,
        drawings,
        texts,
        tracks,
        vias,
        footprints,
        hidden,
        footprintOwnerByRef
    );
    renderer.commit_all_layers();
}

/** Paint selected objects into dynamic layers (e.g. lifted objects during drag) */
export function paintDraggedSelection(
    renderer: Renderer,
    model: RenderModel,
    dragged: DragSelection,
    layerById: Map<string, LayerModel>,
    hiddenLayers?: Set<string>,
) {
    const hidden = hiddenLayers ?? new Set<string>();
    const footprintIndices = dragged.footprintIndices ?? new Set<number>();
    const trackUuids = dragged.trackUuids ?? new Set<string>();
    const viaUuids = dragged.viaUuids ?? new Set<string>();
    const drawingUuids = dragged.drawingUuids ?? new Set<string>();
    const textUuids = dragged.textUuids ?? new Set<string>();
    const zoneUuids = dragged.zoneUuids ?? new Set<string>();

    const footprints = [...footprintIndices].map(i => model.footprints[i]!).filter(Boolean);
    const tracks = trackUuids.size > 0
        ? model.tracks.filter(track => !!track.uuid && trackUuids.has(track.uuid))
        : [];
    const vias = viaUuids.size > 0
        ? model.vias.filter(via => !!via.uuid && viaUuids.has(via.uuid))
        : [];
    const drawings = drawingUuids.size > 0
        ? model.drawings.filter(drawing => !!drawing.uuid && drawingUuids.has(drawing.uuid))
        : [];
    const texts = textUuids.size > 0
        ? model.texts.filter(text => !!text.uuid && textUuids.has(text.uuid))
        : [];
    const footprintOwnerByRef = new Map<FootprintModel, string>();
    for (let i = 0; i < model.footprints.length; i++) {
        const footprint = model.footprints[i];
        if (!footprint) continue;
        footprintOwnerByRef.set(footprint, footprintOwnerId(footprint, i));
    }

    if (zoneUuids.size > 0) {
        const draggedZones = model.zones.filter(zone => !!zone.uuid && zoneUuids.has(zone.uuid));
        if (draggedZones.length > 0) {
            paintZones(renderer, model, hidden, layerById, draggedZones);
        }
    }

    paintObjects(
        renderer,
        layerById,
        drawings,
        texts,
        tracks,
        vias,
        footprints,
        hidden,
        footprintOwnerByRef
    );
}

export function paintAll(renderer: Renderer, model: RenderModel, hiddenLayers?: Set<string>): void {
    paintStaticBoard(renderer, model, hiddenLayers);
}

function paintBoardEdges(renderer: Renderer, model: RenderModel, layerById: Map<string, LayerModel>) {
    const layer = renderer.get_layer("Edge.Cuts");
    const [r, g, b, a] = getLayerColor("Edge.Cuts", layerById);

    for (const edge of model.board.edges) {
        if (edge.type === "line" && edge.start && edge.end) {
            layer.geometry.add_polyline([p2v(edge.start), p2v(edge.end)], 0.15, r, g, b, a);
        } else if (edge.type === "arc" && edge.start && edge.mid && edge.end) {
            layer.geometry.add_polyline(arcToPoints(edge.start, edge.mid, edge.end), 0.15, r, g, b, a);
        } else if (edge.type === "circle" && edge.center && edge.end) {
            const cx = edge.center.x, cy = edge.center.y;
            const rad = Math.sqrt((edge.end.x - cx) ** 2 + (edge.end.y - cy) ** 2);
            const pts: Vec2[] = [];
            for (let i = 0; i <= 64; i++) {
                const angle = (i / 64) * 2 * Math.PI;
                pts.push(new Vec2(cx + rad * Math.cos(angle), cy + rad * Math.sin(angle)));
            }
            layer.geometry.add_polyline(pts, 0.15, r, g, b, a);
        } else if (edge.type === "rect" && edge.start && edge.end) {
            const s = edge.start, e = edge.end;
            layer.geometry.add_polyline([
                new Vec2(s.x, s.y), new Vec2(e.x, s.y), new Vec2(e.x, e.y), new Vec2(s.x, e.y), new Vec2(s.x, s.y),
            ], 0.15, r, g, b, a);
        }
    }
    }

function paintZones(
    renderer: Renderer,
    model: RenderModel,
    hidden: Set<string>,
    layerById: Map<string, LayerModel>,
    zones: ZoneModel[] = model.zones,
) {
    if (hidden.has("__type:zones")) return;
    for (const zone of zones) {
        const ownerId = zoneOwnerId(zone);
        const sortedFilledPolygons = [...zone.filled_polygons].sort(
            (a, b) => layerPaintOrder(a.layer, layerById) - layerPaintOrder(b.layer, layerById),
        );
        for (const filled of sortedFilledPolygons) {
            if (hidden.has(filled.layer)) continue;
            const [r, g, b] = getLayerColor(filled.layer, layerById);
            const layer = renderer.get_layer(zoneRenderLayerName(filled.layer));
            const pts = filled.points.map(p2v);
            if (pts.length >= 3) {
                layer.geometry.add_polygon(pts, r, g, b, ZONE_COLOR_ALPHA, ownerId);
            }
                    }

        const zoneLayersRaw = zone.layers.length > 0
            ? zone.layers
            : [...new Set(zone.filled_polygons.map(fp => fp.layer))];
        const zoneLayers = [...new Set(zoneLayersRaw)].sort(
            (a, b) => layerPaintOrder(a, layerById) - layerPaintOrder(b, layerById),
        );

        const shouldDrawFillFromOutline = (
            !zone.keepout
            && zone.fill_enabled !== false
            && zone.filled_polygons.length === 0
            && zone.outline.length >= 3
        );
        if (shouldDrawFillFromOutline) {
            const outlinePts = zone.outline.map(p2v);
            for (const layerName of zoneLayers) {
                if (!layerName || hidden.has(layerName)) continue;
                const [r, g, b] = getLayerColor(layerName, layerById);
                const layer = renderer.get_layer(zoneRenderLayerName(layerName));
                layer.geometry.add_polygon(outlinePts, r, g, b, ZONE_COLOR_ALPHA, ownerId);
                            }
        }

        const shouldDrawKeepout = zone.keepout || zone.fill_enabled === false;
        if (!shouldDrawKeepout || zone.outline.length < 3) continue;

        const outlinePts = zone.outline.map(p2v);
        const closedOutline = [...outlinePts, outlinePts[0]!.copy()];
        const hatchPitch = zone.hatch_pitch && zone.hatch_pitch > 0 ? zone.hatch_pitch : 0.5;
        const hatchSegments = hatchSegmentsForPolygon(outlinePts, hatchPitch);
        for (const layerName of zoneLayers) {
            if (!layerName || hidden.has(layerName)) continue;
            const [r, g, b, a] = getLayerColor(layerName, layerById);
            const layer = renderer.get_layer(zoneRenderLayerName(layerName));
            layer.geometry.add_polyline(closedOutline, 0.1, r, g, b, Math.max(a, 0.8), ownerId);
            for (const [start, end] of hatchSegments) {
                layer.geometry.add_polyline([start, end], 0.06, r, g, b, Math.max(a * 0.65, 0.45), ownerId);
            }
                    }
    }
}

function hatchSegmentsForPolygon(points: Vec2[], pitch: number): Array<[Vec2, Vec2]> {
    if (points.length < 3 || pitch <= 0) return [];
    const eps = 1e-6;
    const closed = [...points, points[0]!];
    let minV = Infinity;
    let maxV = -Infinity;
    for (const p of points) {
        const v = p.y - p.x;
        if (v < minV) minV = v;
        if (v > maxV) maxV = v;
    }

    const segments: Array<[Vec2, Vec2]> = [];
    for (let c = minV - pitch; c <= maxV + pitch; c += pitch) {
        const rawIntersections: Vec2[] = [];
        for (let i = 0; i < closed.length - 1; i++) {
            const a = closed[i]!;
            const b = closed[i + 1]!;
            const fa = a.y - a.x - c;
            const fb = b.y - b.x - c;
            if ((fa > eps && fb > eps) || (fa < -eps && fb < -eps)) continue;
            const denom = fa - fb;
            if (Math.abs(denom) < eps) continue;
            const t = fa / denom;
            if (t < -eps || t > 1 + eps) continue;
            rawIntersections.push(
                new Vec2(
                    a.x + (b.x - a.x) * t,
                    a.y + (b.y - a.y) * t,
                ),
            );
        }

        rawIntersections.sort((p, q) => (p.x - q.x) || (p.y - q.y));
        const intersections: Vec2[] = [];
        for (const p of rawIntersections) {
            const last = intersections[intersections.length - 1];
            if (!last || Math.abs(last.x - p.x) > eps || Math.abs(last.y - p.y) > eps) {
                intersections.push(p);
            }
        }
        for (let i = 0; i + 1 < intersections.length; i += 2) {
            segments.push([intersections[i]!, intersections[i + 1]!]);
        }
    }
    return segments;
}

function paintTracks(
    renderer: Renderer,
    model: RenderModel,
    hidden: Set<string>,
    layerById: Map<string, LayerModel>,
) {
    if (hidden.has("__type:tracks")) return;
    const byLayer = new Map<string, TrackModel[]>();
    for (const track of model.tracks) {
        const ln = track.layer;
        if (!ln) continue;
        if (hidden.has(ln)) continue;
        let arr = byLayer.get(ln);
        if (!arr) { arr = []; byLayer.set(ln, arr); }
        arr.push(track);
    }
    for (const [layerName, tracks] of sortedLayerEntries(byLayer, layerById)) {
        const [r, g, b, a] = getLayerColor(layerName, layerById);
        const layer = renderer.get_layer(layerName);
        for (const track of tracks) {
            const pts = track.mid
                ? arcToPoints(track.start, track.mid, track.end)
                : [p2v(track.start), p2v(track.end)];
            layer.geometry.add_polyline(pts, track.width, r, g, b, a);
        }
            }
}

function paintVias(
    renderer: Renderer,
    vias: ViaModel[],
    hidden: Set<string>,
    layerById: Map<string, LayerModel>,
) {
    if (hidden.has("__type:tracks")) return;
    // Copper layers: annular ring or filled circle
    const byCopperLayer = new Map<string, ViaModel[]>();
    for (const via of vias) {
        for (const layerName of via.copper_layers) {
            if (!layerName || hidden.has(layerName)) continue;
            let arr = byCopperLayer.get(layerName);
            if (!arr) { arr = []; byCopperLayer.set(layerName, arr); }
            arr.push(via);
        }
    }
    for (const [layerName, layerVias] of sortedLayerEntries(byCopperLayer, layerById)) {
        const [r, g, b, a] = getLayerColor(layerName, layerById);
        const layer = renderer.get_layer(layerName);
        for (const via of layerVias) {
            const cx = via.at.x;
            const cy = via.at.y;
            const outerD = via.size;
            const drillD = via.drill;
            if (drillD > 0 && outerD > drillD) {
                const annulus = (outerD - drillD) / 2;
                const centerlineR = (outerD + drillD) / 4;
                const pts = circleToPoints(cx, cy, centerlineR);
                if (pts.length > 1) {
                    layer.geometry.add_polyline(pts, annulus, r, g, b, Math.max(a, 0.78));
                }
            } else if (outerD > 0) {
                layer.geometry.add_circle(cx, cy, outerD / 2, r, g, b, Math.max(a, 0.78));
            }
        }
            }

    // Drill holes
    const byDrillLayer = new Map<string, ViaModel[]>();
    for (const via of vias) {
        if (via.drill <= 0) continue;
        for (const layerName of via.drill_layers) {
            if (!layerName || hidden.has(layerName)) continue;
            let arr = byDrillLayer.get(layerName);
            if (!arr) { arr = []; byDrillLayer.set(layerName, arr); }
            arr.push(via);
        }
    }
    for (const [layerName, layerVias] of sortedLayerEntries(byDrillLayer, layerById)) {
        const [r, g, b, a] = getLayerColor(layerName, layerById);
        const layer = renderer.get_layer(layerName);
        for (const via of layerVias) {
            if (via.drill <= 0) continue;
            layer.geometry.add_circle(via.at.x, via.at.y, via.drill / 2, r, g, b, a);
        }
            }
}

function isDrillLayer(layerName: string | null | undefined, layerById: Map<string, LayerModel>): boolean {
    return layerName !== null && layerName !== undefined && layerKind(layerName, layerById) === "drill";
}

function isCopperLayer(layerName: string | null | undefined, layerById: Map<string, LayerModel>): boolean {
    return layerName !== null && layerName !== undefined && layerKind(layerName, layerById) === "cu";
}

function orderedCopperLayers(layerById: Map<string, LayerModel>): string[] {
    return [...layerById.values()]
        .filter(layer => layer.kind === "Cu")
        .sort((a, b) => a.panel_order - b.panel_order)
        .map(layer => layer.id);
}

function orderedDrillLayers(layerById: Map<string, LayerModel>): string[] {
    return [...layerById.values()]
        .filter(layer => layer.kind === "Drill")
        .sort((a, b) => a.panel_order - b.panel_order)
        .map(layer => layer.id);
}

function drillLayerByRoot(layerById: Map<string, LayerModel>): Map<string, string> {
    const byRoot = new Map<string, string>();
    for (const drillLayerId of orderedDrillLayers(layerById)) {
        const root = layerById.get(drillLayerId)?.root;
        if (!root) continue;
        if (!byRoot.has(root)) {
            byRoot.set(root, drillLayerId);
        }
    }
    return byRoot;
}

function expandCopperLayerSpan(
    layers: string[],
    layerById: Map<string, LayerModel>,
    includeBetween = false,
): string[] {
    const copperOrder = orderedCopperLayers(layerById);
    const selected = new Set(layers.filter(layer => isCopperLayer(layer, layerById)));
    if (selected.size === 0) return [];

    const expanded = new Set(selected);
    if (includeBetween) {
        const selectedIndices = copperOrder
            .map((layerName, index) => ({ layerName, index }))
            .filter(({ layerName }) => selected.has(layerName))
            .map(({ index }) => index)
            .sort((a, b) => a - b);
        if (selectedIndices.length >= 2) {
            const first = selectedIndices[0]!;
            const last = selectedIndices[selectedIndices.length - 1]!;
            for (let i = first; i <= last; i++) {
                expanded.add(copperOrder[i]!);
            }
        }
    }

    return copperOrder.filter(layerName => expanded.has(layerName));
}

function padDrillLayerIds(
    pad: PadModel,
    layerById: Map<string, LayerModel>,
): string[] {
    const copperLayers = expandCopperLayerSpan(pad.layers, layerById, true);
    const allDrillLayers = orderedDrillLayers(layerById);
    if (copperLayers.length > 0) {
        const drillByRoot = drillLayerByRoot(layerById);
        const resolved: string[] = [];
        const seen = new Set<string>();
        for (const copperLayer of copperLayers) {
            const root = layerById.get(copperLayer)?.root;
            let drillLayer = root ? drillByRoot.get(root) : undefined;
            // Fallback for older layer metadata that only exposes id naming.
            if (!drillLayer && copperLayer.endsWith(".Cu")) {
                drillLayer = `${copperLayer.slice(0, -3)}.Drill`;
            }
            if (!drillLayer || seen.has(drillLayer)) continue;
            seen.add(drillLayer);
            resolved.push(drillLayer);
        }
        if (resolved.length > 0) return resolved;
    }
    return allDrillLayers;
}

function paintPadHole(
    layer: RenderLayer,
    fpAt: Point3,
    pad: PadModel,
    hole: HoleModel,
    r: number,
    g: number,
    b: number,
    a: number,
    ownerId: string | null = null,
) {
    const sx = Math.max(0, hole.size_x || 0);
    const sy = Math.max(0, hole.size_y || 0);
    if (sx <= 0 || sy <= 0) return;

    const offset = hole.offset ?? { x: 0, y: 0 };
    const center = padTransform(fpAt, pad.at, offset.x, offset.y);
    const isOval = (hole.shape ?? "").toLowerCase() === "oval" || Math.abs(sx - sy) > 1e-6;
    if (!isOval) {
        layer.geometry.add_circle(center.x, center.y, sx / 2, r, g, b, a, ownerId);
        return;
    }

    const major = Math.max(sx, sy);
    const minor = Math.min(sx, sy);
    const focal = Math.max(0, (major - minor) / 2);
    const p1 = sx >= sy
        ? padTransform(fpAt, pad.at, offset.x - focal, offset.y)
        : padTransform(fpAt, pad.at, offset.x, offset.y - focal);
    const p2 = sx >= sy
        ? padTransform(fpAt, pad.at, offset.x + focal, offset.y)
        : padTransform(fpAt, pad.at, offset.x, offset.y + focal);
    layer.geometry.add_polyline([p1, p2], minor, r, g, b, a, ownerId);
}

type GlobalDrawingPaintMode = "drill" | "copper" | "non_copper";

function shouldPaintGlobalDrawing(
    layerName: string,
    mode: GlobalDrawingPaintMode,
    layerById: Map<string, LayerModel>,
): boolean {
    const drill = isDrillLayer(layerName, layerById);
    const copper = isCopperLayer(layerName, layerById);
    if (mode === "drill") return drill;
    if (mode === "copper") return !drill && copper;
    return !drill && !copper;
}

function paintGlobalDrawings(
    renderer: Renderer,
    model: RenderModel,
    hidden: Set<string>,
    mode: GlobalDrawingPaintMode,
    layerById: Map<string, LayerModel>,
) {
    const showText = !isTextHidden(hidden);
    const showShapes = !isShapesHidden(hidden);
    if (!showShapes && !(mode === "non_copper" && showText)) return;
    const byLayer = new Map<string, DrawingModel[]>();
    if (showShapes) {
        for (const drawing of model.drawings) {
            const ln = drawing.layer;
            if (!ln) continue;
            if (!shouldPaintGlobalDrawing(ln, mode, layerById)) continue;
            if (hidden.has(ln)) continue;
            let arr = byLayer.get(ln);
            if (!arr) { arr = []; byLayer.set(ln, arr); }
            arr.push(drawing);
        }
    }
    const worldAt: Point3 = { x: 0, y: 0, r: 0 };
    for (const [layerName, drawings] of sortedLayerEntries(byLayer, layerById)) {
        const [r, g, b, a] = getLayerColor(layerName, layerById);
        const layer = renderer.get_layer(layerName);
        for (const drawing of drawings) {
            paintDrawing(layer, worldAt, drawing, r, g, b, a);
        }
    }

    if (mode === "non_copper" && showText) {
        const textsByLayer = new Map<string, TextModel[]>();
        for (const text of model.texts) {
            const ln = text.layer;
            if (!ln || hidden.has(ln)) continue;
            let arr = textsByLayer.get(ln);
            if (!arr) { arr = []; textsByLayer.set(ln, arr); }
            arr.push(text);
        }
        for (const [layerName, texts] of sortedLayerEntries(textsByLayer, layerById)) {
            const [r, g, b, a] = getLayerColor(layerName, layerById);
            const layer = renderer.get_layer(layerName);
            for (const text of texts) {
                paintText(layer, worldAt, text, r, g, b, a);
            }
        }
    }
}

export function paintFootprint(
    renderer: Renderer,
    fp: FootprintModel,
    hidden: Set<string>,
    layerById: Map<string, LayerModel>,
) {
    const drawingsByLayer = new Map<string, DrawingModel[]>();
    const drillDrawingsByLayer = new Map<string, DrawingModel[]>();
    const padHolesByLayer = new Map<string, Array<{ pad: PadModel; hole: HoleModel }>>();
    for (const drawing of fp.drawings) {
        const ln = drawing.layer;
        if (!ln) continue;
        if (hidden.has(ln)) continue;
        const map = isDrillLayer(ln, layerById) ? drillDrawingsByLayer : drawingsByLayer;
        let arr = map.get(ln);
        if (!arr) {
            arr = [];
            map.set(ln, arr);
        }
        arr.push(drawing);
    }
    for (const pad of fp.pads) {
        const hole = pad.hole;
        if (!hole) continue;
        for (const drillLayer of padDrillLayerIds(pad, layerById)) {
            if (!drillLayer || hidden.has(drillLayer)) continue;
            let arr = padHolesByLayer.get(drillLayer);
            if (!arr) {
                arr = [];
                padHolesByLayer.set(drillLayer, arr);
            }
            arr.push({ pad, hole });
        }
    }
    if (!isShapesHidden(hidden)) {
        for (const [layerName, drawings] of sortedLayerEntries(drawingsByLayer, layerById)) {
            const [r, g, b, a] = getLayerColor(layerName, layerById);
            const layer = renderer.get_layer(layerName);
            for (const drawing of drawings) {
                paintDrawing(layer, fp.at, drawing, r, g, b, a);
            }
        }
    }

    if (!isTextHidden(hidden)) {
        const textsByLayer = new Map<string, TextModel[]>();
        for (const text of fp.texts) {
            const ln = text.layer;
            if (!ln || hidden.has(ln)) continue;
            let arr = textsByLayer.get(ln);
            if (!arr) { arr = []; textsByLayer.set(ln, arr); }
            arr.push(text);
        }
        for (const [layerName, texts] of sortedLayerEntries(textsByLayer, layerById)) {
            const [r, g, b, a] = getLayerColor(layerName, layerById);
            const layer = renderer.get_layer(layerName);
            for (const text of texts) {
                paintText(layer, fp.at, text, r, g, b, a);
            }
        }
    }
    const padsByLayer = new Map<string, PadModel[]>();
    for (const pad of fp.pads) {
        const hole = pad.hole;
        const hasHole = !!hole && Math.max(0, hole.size_x || 0) > 0 && Math.max(0, hole.size_y || 0) > 0;
        const padType = (pad.type || "").toLowerCase();
        for (const layerName of pad.layers) {
            if (!layerName || hidden.has(layerName) || isDrillLayer(layerName, layerById)) continue;
            if (padType === "np_thru_hole") continue;
            if (hasHole && !isCopperLayer(layerName, layerById)) continue;
            let layerPads = padsByLayer.get(layerName);
            if (!layerPads) {
                layerPads = [];
                padsByLayer.set(layerName, layerPads);
            }
            layerPads.push(pad);
        }
    }
    if (!hidden.has("__type:pads")) {
        for (const [layerName, layerPads] of sortedLayerEntries(padsByLayer, layerById)) {
            const layer = renderer.get_layer(layerName);
            for (const pad of layerPads) {
                paintPad(layer, fp.at, pad, layerName, layerById);
            }
                    }
        for (const [layerName, holeEntries] of sortedLayerEntries(padHolesByLayer, layerById)) {
            const [r, g, b, a] = getLayerColor(layerName, layerById);
            const layer = renderer.get_layer(layerName);
            for (const { pad, hole } of holeEntries) {
                paintPadHole(layer, fp.at, pad, hole, r, g, b, a);
            }
                    }
    }
    if (!isShapesHidden(hidden)) {
        for (const [layerName, drawings] of sortedLayerEntries(drillDrawingsByLayer, layerById)) {
            const [r, g, b, a] = getLayerColor(layerName, layerById);
            const layer = renderer.get_layer(layerName);
            for (const drawing of drawings) {
                paintDrawing(layer, fp.at, drawing, r, g, b, a);
            }
                    }
    }
    paintPadAnnotations(renderer, fp, hidden, layerById);
}

function paintPadAnnotations(
    renderer: Renderer,
    fp: FootprintModel,
    hidden: Set<string>,
    layerById: Map<string, LayerModel>,
) {
    if (hidden.has("__type:pads")) return;
    if (fp.pads.length === 0) return;
    if (fp.pad_names.length === 0 && fp.pad_numbers.length === 0) return;
    const layerGeometry = buildPadAnnotationGeometry(fp, hidden);

    const orderedAnnotationLayers = [...layerGeometry.keys()].sort(
        (a, b) => layerPaintOrder(a, layerById) - layerPaintOrder(b, layerById),
    );
    for (const layerName of orderedAnnotationLayers) {
        const geometry = layerGeometry.get(layerName);
        if (!geometry) continue;
        if (geometry.numbers.length === 0) continue;
        const layer = renderer.get_layer(layerName);
        const [r, g, b, a] = getLayerColor(layerName, layerById);

        for (const number of geometry.numbers) {
            layer.geometry.add_circle(number.badgeCenterX, number.badgeCenterY, number.badgeRadius, r, g, b, Math.max(a, 0.98));
            const outlinePoints = circleToPoints(number.badgeCenterX, number.badgeCenterY, number.badgeRadius);
            if (outlinePoints.length > 1) {
                layer.geometry.add_polyline(outlinePoints, Math.max(number.badgeRadius * 0.18, 0.04), 0.05, 0.08, 0.12, 0.8);
            }
        }

            }
}

function paintDrawing(
    layer: RenderLayer,
    fpAt: Point3,
    drawing: DrawingModel,
    r: number,
    g: number,
    b: number,
    a: number,
    ownerId: string | null = null,
) {
    const rawWidth = Number.isFinite(drawing.width) ? drawing.width : 0;
    const strokeWidth = rawWidth > 0 ? rawWidth : (drawing.filled ? 0 : 0.12);

    switch (drawing.type) {
        case "line": {
            const p1 = fpTransform(fpAt, drawing.start.x, drawing.start.y);
            const p2 = fpTransform(fpAt, drawing.end.x, drawing.end.y);
            layer.geometry.add_polyline([p1, p2], strokeWidth, r, g, b, a, ownerId);
            break;
        }
        case "arc": {
            const localPts = arcToPoints(drawing.start, drawing.mid, drawing.end);
            const worldPts = localPts.map(p => fpTransform(fpAt, p.x, p.y));
            layer.geometry.add_polyline(worldPts, strokeWidth, r, g, b, a, ownerId);
            break;
        }
        case "circle": {
            const cx = drawing.center.x;
            const cy = drawing.center.y;
            const rad = Math.sqrt((drawing.end.x - cx) ** 2 + (drawing.end.y - cy) ** 2);
            const pts: Vec2[] = [];
            for (let i = 0; i <= 48; i++) {
                const angle = (i / 48) * 2 * Math.PI;
                pts.push(new Vec2(cx + rad * Math.cos(angle), cy + rad * Math.sin(angle)));
            }
            const worldPts = pts.map(p => fpTransform(fpAt, p.x, p.y));
            if (drawing.filled && worldPts.length >= 3) {
                layer.geometry.add_polygon(worldPts, r, g, b, a, ownerId);
            }
            if (strokeWidth > 0) {
                layer.geometry.add_polyline(worldPts, strokeWidth, r, g, b, a, ownerId);
            }
            break;
        }
        case "rect": {
            const s = drawing.start;
            const e = drawing.end;
            const corners = [
                fpTransform(fpAt, s.x, s.y), fpTransform(fpAt, e.x, s.y),
                fpTransform(fpAt, e.x, e.y), fpTransform(fpAt, s.x, e.y),
            ];
            if (drawing.filled) {
                layer.geometry.add_polygon(corners, r, g, b, a, ownerId);
            }
            if (strokeWidth > 0) {
                layer.geometry.add_polyline([...corners, corners[0]!.copy()], strokeWidth, r, g, b, a, ownerId);
            }
            break;
        }
        case "polygon": {
            const worldPts = drawing.points.map(p => fpTransform(fpAt, p.x, p.y));
            if (worldPts.length >= 3) {
                if (drawing.filled) {
                    layer.geometry.add_polygon(worldPts, r, g, b, a, ownerId);
                }
                if (strokeWidth > 0) {
                    layer.geometry.add_polyline([...worldPts, worldPts[0]!.copy()], strokeWidth, r, g, b, a, ownerId);
                }
            }
            break;
        }
        case "curve": {
            const worldPts = drawing.points.map(p => fpTransform(fpAt, p.x, p.y));
            if (worldPts.length >= 2) {
                layer.geometry.add_polyline(worldPts, strokeWidth, r, g, b, a, ownerId);
            }
            break;
        }
    }
}

function paintText(
    layer: RenderLayer,
    fpAt: Point3,
    text: TextModel,
    r: number,
    g: number,
    b: number,
    a: number,
    ownerId: string | null = null,
) {
    if (!text.text.trim()) return;
    const lines = text.text.split("\n");
    const justifySet = new Set(text.justify ?? []);
    const textWidth = text.size?.w ?? 1.0;
    const textHeight = text.size?.h ?? 1.0;
    const linePitch = textHeight * 1.62;
    const totalHeight = textHeight * 1.17 + Math.max(0, lines.length - 1) * linePitch;

    let baseOffsetY = textHeight;
    if (justifySet.has("center") || (!justifySet.has("top") && !justifySet.has("bottom"))) {
        baseOffsetY -= totalHeight / 2;
    } else if (justifySet.has("bottom")) {
        baseOffsetY -= totalHeight;
    }

    const textRotation = (fpAt.r || 0) + (text.at.r || 0);
    const worldPos = fpTransform(fpAt, text.at.x, text.at.y);
    const rad = -textRotation * DEG_TO_RAD;
    const cos = Math.cos(rad);
    const sin = Math.sin(rad);

    const thickness = text.thickness ?? (textHeight * 0.15);

    for (let lineIdx = 0; lineIdx < lines.length; lineIdx++) {
        const line = lines[lineIdx]!;
        const layout = layoutKicadStrokeLine(line, textWidth, textHeight);
        if (layout.strokes.length === 0) continue;

        let lineOffsetX = 0;
        if (justifySet.has("right")) {
            lineOffsetX = -layout.advance;
        } else if (justifySet.has("center") || (!justifySet.has("left") && !justifySet.has("right"))) {
            lineOffsetX = -layout.advance / 2;
        }
        const lineOffsetY = baseOffsetY + lineIdx * linePitch;

        for (const stroke of layout.strokes) {
            if (stroke.length < 2) continue;
            // Optimize: Avoid allocating Vec2 objects in the inner loop
            const worldPoints: Vec2[] = [];
            for (const p of stroke) {
                const lx = p.x + lineOffsetX;
                const ly = p.y + lineOffsetY;
                worldPoints.push(new Vec2(
                    worldPos.x + lx * cos - ly * sin,
                    worldPos.y + lx * sin + ly * cos
                ));
            }
            layer.geometry.add_polyline(worldPoints, thickness, r, g, b, a, ownerId);
        }
    }
}

function paintPad(
    layer: RenderLayer,
    fpAt: Point3,
    pad: PadModel,
    layerName: string,
    layerById: Map<string, LayerModel>,
    ownerId: string | null = null,
) {
    if (pad.layers.length === 0) {
        return;
    }
    const layerIsCopper = isCopperLayer(layerName, layerById);
    const [lr, lg, lb, la] = getLayerColor(layerName, layerById);
    const cr = lr;
    const cg = lg;
    const cb = lb;
    const ca = Math.max(la, 0.78);
    const hw = pad.size.w / 2;
    const hh = pad.size.h / 2;

    const hole = pad.hole;
    const isThroughHole = (pad.type || "").toLowerCase() === "thru_hole";
    const isNpThroughHole = (pad.type || "").toLowerCase() === "np_thru_hole";
    const holeSx = hole ? Math.max(0, hole.size_x || 0) : 0;
    const holeSy = hole ? Math.max(0, hole.size_y || 0) : 0;
    const hasPadHole = holeSx > 0 && holeSy > 0;
    if (hasPadHole && !layerIsCopper) {
        return;
    }
    if (isNpThroughHole) {
        return;
    }
    const renderAsAnnularRing =
        isThroughHole
        && hasPadHole
        && layerIsCopper;
    if (renderAsAnnularRing) {
        if (pad.shape === "circle") {
            const center = fpTransform(fpAt, pad.at.x, pad.at.y);
            const outerDiameter = Math.max(pad.size.w, pad.size.h);
            const holeDiameter = Math.max(holeSx, holeSy);
            const annulus = (outerDiameter - holeDiameter) / 2;
            const centerlineRadius = (outerDiameter + holeDiameter) / 4;
            if (annulus > 0 && centerlineRadius > 0) {
                const ringPoints = circleToPoints(center.x, center.y, centerlineRadius);
                if (ringPoints.length > 1) {
                    layer.geometry.add_polyline(ringPoints, annulus, cr, cg, cb, ca, ownerId);
                    return;
                }
            }
        } else if (pad.shape === "oval") {
            const outerMajor = Math.max(pad.size.w, pad.size.h);
            const outerMinor = Math.min(pad.size.w, pad.size.h);
            const holeMajor = Math.max(holeSx, holeSy);
            const holeMinor = Math.min(holeSx, holeSy);
            const annulus = Math.min(
                (outerMajor - holeMajor) / 2,
                (outerMinor - holeMinor) / 2,
            );
            if (annulus > 0) {
                const centerMajor = outerMajor - annulus;
                const centerMinor = outerMinor - annulus;
                if (centerMajor > 0 && centerMinor > 0) {
                    const horizontal = pad.size.w >= pad.size.h;
                    const radius = centerMinor / 2;
                    const halfSpan = Math.max(0, (centerMajor - centerMinor) / 2);
                    const arcSegments = 18;
                    const localPoints: Vec2[] = [];
                    for (let i = 0; i <= arcSegments; i++) {
                        const angle = Math.PI / 2 - (Math.PI * i / arcSegments);
                        localPoints.push(
                            horizontal
                                ? new Vec2(
                                    halfSpan + radius * Math.cos(angle),
                                    radius * Math.sin(angle),
                                )
                                : new Vec2(
                                    -radius * Math.sin(angle),
                                    halfSpan + radius * Math.cos(angle),
                                ),
                        );
                    }
                    for (let i = 0; i <= arcSegments; i++) {
                        const angle = -Math.PI / 2 + (Math.PI * i / arcSegments);
                        localPoints.push(
                            horizontal
                                ? new Vec2(
                                    -halfSpan - radius * Math.cos(angle),
                                    radius * Math.sin(angle),
                                )
                                : new Vec2(
                                    -radius * Math.sin(angle),
                                    -halfSpan - radius * Math.cos(angle),
                                ),
                        );
                    }
                    if (localPoints.length > 2) {
                        // Closed centerline loop for oval annulus ring (prevents C/U-shaped artifacts).
                        localPoints.push(localPoints[0]!.copy());
                        const ringPoints = localPoints.map(p => padTransform(fpAt, pad.at, p.x, p.y));
                        layer.geometry.add_polyline(ringPoints, annulus, cr, cg, cb, ca, ownerId);
                        return;
                    }
                }
            }
        }
    }

    if (pad.shape === "circle") {
        const center = fpTransform(fpAt, pad.at.x, pad.at.y);
        layer.geometry.add_circle(center.x, center.y, hw, cr, cg, cb, ca, ownerId);
    } else if (pad.shape === "oval") {
        const longAxis = Math.max(hw, hh);
        const shortAxis = Math.min(hw, hh);
        const focalDist = longAxis - shortAxis;
        let p1: Vec2, p2: Vec2;
        if (hw >= hh) {
            p1 = padTransform(fpAt, pad.at, -focalDist, 0);
            p2 = padTransform(fpAt, pad.at, focalDist, 0);
        } else {
            p1 = padTransform(fpAt, pad.at, 0, -focalDist);
            p2 = padTransform(fpAt, pad.at, 0, focalDist);
        }
        layer.geometry.add_polyline([p1, p2], shortAxis * 2, cr, cg, cb, ca, ownerId);
    } else {
        const corners = [
            padTransform(fpAt, pad.at, -hw, -hh), padTransform(fpAt, pad.at, hw, -hh),
            padTransform(fpAt, pad.at, hw, hh), padTransform(fpAt, pad.at, -hw, hh),
        ];
        layer.geometry.add_polygon(corners, cr, cg, cb, ca, ownerId);
    }

    // Pad holes are rendered in dedicated depth layers (see paintFootprint).
}

/** Paint a selection highlight around a footprint */
export function paintSelection(renderer: Renderer, fp: FootprintModel): void {
    const layer = renderer.start_dynamic_layer("selection");
    drawFootprintSelectionBox(layer, fp, SELECTION_STROKE_WIDTH, 0.85, SELECTION_GROW, 0.12);
    renderer.commit_dynamic_layer(layer);
}

/** Paint per-member halos for a selected/hovered footprint group. */
export function paintGroupHalos(
    renderer: Renderer,
    footprints: FootprintModel[],
    memberIndices: number[],
    mode: "selected" | "hover",
): null {
    if (memberIndices.length === 0) return null;
    const layer = renderer.start_dynamic_layer(mode === "selected" ? "group-selection" : "group-hover");
    const strokeWidth = mode === "selected" ? GROUP_SELECTION_STROKE_WIDTH : HOVER_SELECTION_STROKE_WIDTH;
    const alpha = mode === "selected" ? 0.7 : 0.45;
    const grow = mode === "selected" ? GROUP_SELECTION_GROW : HOVER_SELECTION_GROW;
    const fillAlpha = mode === "selected" ? 0.09 : 0.055;
    for (const index of memberIndices) {
        const fp = footprints[index];
        if (!fp) continue;
        drawFootprintSelectionBox(layer, fp, strokeWidth, alpha, grow, fillAlpha);
    }
    renderer.commit_dynamic_layer(layer);
    return null;
}

/** Paint a single bounding box encompassing all footprints in a group. */
export function paintGroupBBox(
    renderer: Renderer,
    footprints: FootprintModel[],
    memberIndices: number[],
    mode: "selected" | "hover",
): void {
    if (memberIndices.length === 0) return;
    const grow = mode === "selected" ? 0.4 : 0.28;
    const strokeWidth = mode === "selected" ? 0.12 : 0.09;
    const alpha = mode === "selected" ? 0.8 : 0.4;
    const fillAlpha = mode === "selected" ? 0.06 : 0.025;

    const boxes: BBox[] = [];
    for (const index of memberIndices) {
        const fp = footprints[index];
        if (!fp) continue;
        const b = footprintBBox(fp);
        if (b.w > 0 || b.h > 0) boxes.push(b);
    }
    if (boxes.length === 0) return;

    const combined = BBox.combine(boxes).grow(grow);
    if (combined.w <= 0 || combined.h <= 0) return;

    const layer = renderer.start_dynamic_layer(mode === "selected" ? "group-bbox-selected" : "group-bbox-hover");
    const corners = [
        new Vec2(combined.x, combined.y),
        new Vec2(combined.x2, combined.y),
        new Vec2(combined.x2, combined.y2),
        new Vec2(combined.x, combined.y2),
        new Vec2(combined.x, combined.y),
    ];
    if (fillAlpha > 0) {
        layer.geometry.add_polygon(corners.slice(0, 4), 0.4, 0.75, 1.0, fillAlpha);
    }
    layer.geometry.add_polyline(corners, strokeWidth, 0.4, 0.75, 1.0, alpha);
    renderer.commit_dynamic_layer(layer);
}

/** Paint a pre-computed bounding box outline (e.g. for graphic-only groups). */
export function paintBBoxOutline(renderer: Renderer, bbox: BBox, mode: "selected" | "hover"): void {
    const grow = mode === "selected" ? 0.4 : 0.28;
    const strokeWidth = mode === "selected" ? 0.12 : 0.09;
    const alpha = mode === "selected" ? 0.8 : 0.4;
    const fillAlpha = mode === "selected" ? 0.06 : 0.025;
    const grown = bbox.grow(grow);
    if (grown.w <= 0 || grown.h <= 0) return;
    const layer = renderer.start_dynamic_layer(mode === "selected" ? "group-bbox-selected" : "group-bbox-hover");
    const corners = [
        new Vec2(grown.x, grown.y),
        new Vec2(grown.x2, grown.y),
        new Vec2(grown.x2, grown.y2),
        new Vec2(grown.x, grown.y2),
        new Vec2(grown.x, grown.y),
    ];
    if (fillAlpha > 0) {
        layer.geometry.add_polygon(corners.slice(0, 4), 0.4, 0.75, 1.0, fillAlpha);
    }
    layer.geometry.add_polyline(corners, strokeWidth, 0.4, 0.75, 1.0, alpha);
    renderer.commit_dynamic_layer(layer);
}

/** Compute a bounding box for the full render model */
export function computeBBox(model: RenderModel): BBox {
    const points: Vec2[] = [];
    for (const edge of model.board.edges) {
        if (edge.start) points.push(p2v(edge.start));
        if (edge.end) points.push(p2v(edge.end));
        if (edge.mid) points.push(p2v(edge.mid));
        if (edge.center) points.push(p2v(edge.center));
    }
    for (const drawing of model.drawings) {
        switch (drawing.type) {
            case "line":
                points.push(p2v(drawing.start));
                points.push(p2v(drawing.end));
                break;
            case "arc":
                points.push(p2v(drawing.start));
                points.push(p2v(drawing.mid));
                points.push(p2v(drawing.end));
                break;
            case "circle":
                points.push(p2v(drawing.center));
                points.push(p2v(drawing.end));
                break;
            case "rect":
                points.push(p2v(drawing.start));
                points.push(p2v(drawing.end));
                break;
            case "polygon":
            case "curve":
                for (const p of drawing.points) points.push(p2v(p));
                break;
        }
    }
    for (const text of model.texts) {
        points.push(new Vec2(text.at.x, text.at.y));
    }
    for (const fp of model.footprints) {
        points.push(new Vec2(fp.at.x, fp.at.y));
        for (const pad of fp.pads) {
            points.push(fpTransform(fp.at, pad.at.x, pad.at.y));
        }
        for (const text of fp.texts) {
            points.push(fpTransform(fp.at, text.at.x, text.at.y));
        }
    }
    for (const track of model.tracks) {
        points.push(p2v(track.start));
        points.push(p2v(track.end));
    }
    if (points.length === 0) return new BBox(0, 0, 100, 100);
    return BBox.from_points(points).grow(5);
}
