import type { LayerModel } from "./types";

/** RGBA color tuples [r, g, b, a] in 0-1 range */
export type Color = [number, number, number, number];

const UNKNOWN_LAYER_COLOR: Color = [0.5, 0.5, 0.5, 0.5];

export const PAD_COLOR: Color = [0.57, 0.57, 0.30, 0.90];
export const PAD_FRONT_COLOR: Color = [0.86, 0.23, 0.22, 0.78];
export const PAD_BACK_COLOR: Color = [0.16, 0.28, 0.47, 0.78];
export const PAD_THROUGH_HOLE_COLOR: Color = [0.89, 0.72, 0.18, 0.96];
export const HOLE_CORE_COLOR: Color = [0.04, 0.06, 0.10, 1.0];
export const PAD_PLATED_HOLE_COLOR: Color = HOLE_CORE_COLOR;
export const NON_PLATED_HOLE_COLOR: Color = [0.10, 0.77, 0.83, 0.98];
export const PAD_HOLE_WALL_COLOR: Color = [0.74, 0.74, 0.76, 0.98];
export const VIA_COLOR: Color = [0.74, 0.74, 0.76, 0.98];
export const VIA_BLIND_BURIED_COLOR: Color = [0.67, 0.67, 0.70, 0.98];
export const VIA_MICRO_COLOR: Color = [0.56, 0.70, 0.74, 0.98];
export const VIA_DRILL_COLOR: Color = HOLE_CORE_COLOR;
export const VIA_HOLE_WALL_COLOR: Color = [0.78, 0.78, 0.80, 0.98];
export const SELECTION_COLOR: Color = [1.0, 1.0, 1.0, 0.3];
export const BOARD_BG: Color = [0.02, 0.10, 0.22, 1.0];
export const ZONE_COLOR_ALPHA = 0.25;

export function getLayerColor(
    layer: string | null | undefined,
    layerById?: Map<string, LayerModel>,
): Color {
    if (!layer) return UNKNOWN_LAYER_COLOR;
    const fromModel = layerById?.get(layer)?.color;
    if (fromModel) return fromModel;
    return UNKNOWN_LAYER_COLOR;
}

function withPadAlpha(color: Color): Color {
    return [color[0], color[1], color[2], Math.max(0.78, color[3])];
}

export function getPadColor(
    layers: string[],
    layerById?: Map<string, LayerModel>,
): Color {
    const infos = layers
        .map((layer) => layerById?.get(layer))
        .filter((info): info is LayerModel => Boolean(info));
    const copperInfos = infos.filter((info) => info.kind === "Cu");
    const roots = new Set(copperInfos.map((info) => info.root).filter((root): root is string => Boolean(root)));

    if (roots.size === 1 && copperInfos[0]) {
        return withPadAlpha(copperInfos[0].color);
    }

    const hasFront = copperInfos.some((info) => info.root === "F");
    const hasBack = copperInfos.some((info) => info.root === "B");
    if (hasFront && hasBack) return PAD_COLOR;
    if (hasFront) return PAD_FRONT_COLOR;
    if (hasBack) return PAD_BACK_COLOR;
    return PAD_COLOR;
}
