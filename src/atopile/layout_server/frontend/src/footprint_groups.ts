import type { RenderModel } from "./types";

export interface UiFootprintGroup {
    id: string;
    uuid: string | null;
    name: string | null;
    memberUuids: string[];
    memberIndices: number[];
    trackMemberUuids: string[];
    viaMemberUuids: string[];
}

export function buildGroupIndex(model: RenderModel): {
    groupsById: Map<string, UiFootprintGroup>;
    groupIdByFpIndex: Map<number, string>;
    trackIndexByUuid: Map<string, number>;
    viaIndexByUuid: Map<string, number>;
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
        if (memberIndices.length < 2) continue;

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
        };
        groupsById.set(id, uiGroup);
        for (const fpIndex of memberIndices) {
            if (!groupIdByFpIndex.has(fpIndex)) {
                groupIdByFpIndex.set(fpIndex, id);
            }
        }
    }

    return { groupsById, groupIdByFpIndex, trackIndexByUuid, viaIndexByUuid };
}
