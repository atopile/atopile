import { BBox, Vec2 } from "./math";
import type { DrawingModel, RenderModel } from "./types";

export interface UiFootprintGroup {
    id: string;
    uuid: string | null;
    name: string | null;
    memberUuids: string[];
    memberIndices: number[];
    trackMemberUuids: string[];
    viaMemberUuids: string[];
    graphicMemberUuids: string[];
    textMemberUuids: string[];
    zoneMemberUuids: string[];
    /** Bounding box of all graphic members; non-null when graphicMemberUuids is non-empty. */
    graphicBBox: BBox | null;
}

/** Collect representative Vec2 points for a drawing (used for bbox computation). */
function drawingPoints(drawing: DrawingModel): Vec2[] {
    switch (drawing.type) {
        case "line":
            return [new Vec2(drawing.start.x, drawing.start.y), new Vec2(drawing.end.x, drawing.end.y)];
        case "arc":
            return [
                new Vec2(drawing.start.x, drawing.start.y),
                new Vec2(drawing.mid.x, drawing.mid.y),
                new Vec2(drawing.end.x, drawing.end.y),
            ];
        case "circle": {
            const cx = drawing.center.x, cy = drawing.center.y;
            const r = Math.hypot(drawing.end.x - cx, drawing.end.y - cy);
            return [new Vec2(cx - r, cy - r), new Vec2(cx + r, cy + r)];
        }
        case "rect":
            return [new Vec2(drawing.start.x, drawing.start.y), new Vec2(drawing.end.x, drawing.end.y)];
        case "polygon":
        case "curve":
            return drawing.points.map(p => new Vec2(p.x, p.y));
        default:
            return [];
    }
}

export function buildGroupIndex(model: RenderModel): {
    groupsById: Map<string, UiFootprintGroup>;
    groupIdByFpIndex: Map<number, string>;
    trackIndexByUuid: Map<string, number>;
    viaIndexByUuid: Map<string, number>;
    drawingIndexByUuid: Map<string, number>;
    textIndexByUuid: Map<string, number>;
    zoneIndexByUuid: Map<string, number>;
} {
    const groupsById = new Map<string, UiFootprintGroup>();
    const groupIdByFpIndex = new Map<number, string>();

    const indexByUuid = new Map<string, number>();
    for (let i = 0; i < model.footprints.length; i++) {
        const uuid = model.footprints[i]!.uuid;
        if (uuid) indexByUuid.set(uuid, i);
    }

    const trackIndexByUuid = new Map<string, number>();
    for (let i = 0; i < model.tracks.length; i++) {
        const uuid = model.tracks[i]!.uuid;
        if (uuid) trackIndexByUuid.set(uuid, i);
    }

    const viaIndexByUuid = new Map<string, number>();
    for (let i = 0; i < model.vias.length; i++) {
        const uuid = model.vias[i]!.uuid;
        if (uuid) viaIndexByUuid.set(uuid, i);
    }

    const drawingIndexByUuid = new Map<string, number>();
    for (let i = 0; i < model.drawings.length; i++) {
        const uuid = model.drawings[i]!.uuid;
        if (uuid) drawingIndexByUuid.set(uuid, i);
    }

    const textIndexByUuid = new Map<string, number>();
    for (let i = 0; i < model.texts.length; i++) {
        const uuid = model.texts[i]!.uuid;
        if (uuid) textIndexByUuid.set(uuid, i);
    }

    const zoneIndexByUuid = new Map<string, number>();
    for (let i = 0; i < model.zones.length; i++) {
        const uuid = model.zones[i]!.uuid;
        if (uuid) zoneIndexByUuid.set(uuid, i);
    }

    const usedIds = new Set<string>();
    for (let i = 0; i < model.footprint_groups.length; i++) {
        const group = model.footprint_groups[i]!;
        const memberIndices: number[] = [];
        const memberUuids: string[] = [];
        for (const memberUuid of group.member_uuids) {
            if (!memberUuid) continue;
            const fpIndex = indexByUuid.get(memberUuid);
            if (fpIndex === undefined) continue;
            memberIndices.push(fpIndex);
            memberUuids.push(memberUuid);
        }

        const trackMemberUuids: string[] = [];
        for (const trackUuid of (group.track_member_uuids ?? [])) {
            if (trackUuid && trackIndexByUuid.has(trackUuid)) {
                trackMemberUuids.push(trackUuid);
            }
        }

        const viaMemberUuids: string[] = [];
        for (const viaUuid of (group.via_member_uuids ?? [])) {
            if (viaUuid && viaIndexByUuid.has(viaUuid)) {
                viaMemberUuids.push(viaUuid);
            }
        }

        const graphicMemberUuids: string[] = [];
        for (const uuid of (group.graphic_member_uuids ?? [])) {
            if (uuid && drawingIndexByUuid.has(uuid)) graphicMemberUuids.push(uuid);
        }

        const textMemberUuids: string[] = [];
        for (const uuid of (group.text_member_uuids ?? [])) {
            if (uuid && textIndexByUuid.has(uuid)) textMemberUuids.push(uuid);
        }

        const zoneMemberUuids: string[] = [];
        for (const uuid of (group.zone_member_uuids ?? [])) {
            if (uuid && zoneIndexByUuid.has(uuid)) zoneMemberUuids.push(uuid);
        }

        // Require ≥2 footprints OR at least one graphic/text/zone member.
        const rawGraphicUuids = (group.graphic_member_uuids ?? []).filter(Boolean);
        if (rawGraphicUuids.length > 0 && graphicMemberUuids.length === 0) {
            console.warn("[layout] Group has graphic_member_uuids but none matched drawingIndexByUuid:", {
                groupId: group.uuid || group.name,
                rawGraphicUuids,
                drawingCount: model.drawings.length,
                drawingsWithUuid: [...Array(model.drawings.length).keys()].filter(i => model.drawings[i]?.uuid).length,
            });
        }
        if (memberIndices.length < 2 && graphicMemberUuids.length === 0 && textMemberUuids.length === 0 && zoneMemberUuids.length === 0) continue;

        // Compute bounding box of all graphic members (used for hit-testing graphic-only groups).
        let graphicBBox: BBox | null = null;
        if (graphicMemberUuids.length > 0) {
            const pts: Vec2[] = [];
            for (const uuid of graphicMemberUuids) {
                const idx = drawingIndexByUuid.get(uuid);
                if (idx === undefined) continue;
                const d = model.drawings[idx];
                if (d) pts.push(...drawingPoints(d));
            }
            if (pts.length > 0) graphicBBox = BBox.from_points(pts).grow(0.5);
        }

        let id = group.uuid || group.name || `group-${i + 1}`;
        if (usedIds.has(id)) {
            let suffix = 2;
            while (usedIds.has(`${id}:${suffix}`)) suffix++;
            id = `${id}:${suffix}`;
        }
        usedIds.add(id);

        const uiGroup: UiFootprintGroup = {
            id,
            uuid: group.uuid,
            name: group.name,
            memberUuids,
            memberIndices,
            trackMemberUuids,
            viaMemberUuids,
            graphicMemberUuids,
            textMemberUuids,
            zoneMemberUuids,
            graphicBBox,
        };
        groupsById.set(id, uiGroup);
        for (const fpIndex of memberIndices) {
            if (!groupIdByFpIndex.has(fpIndex)) {
                groupIdByFpIndex.set(fpIndex, id);
            }
        }
    }

    return { groupsById, groupIdByFpIndex, trackIndexByUuid, viaIndexByUuid, drawingIndexByUuid, textIndexByUuid, zoneIndexByUuid };
}
