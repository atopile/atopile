import type { LayerModel } from "./types";

/** RGBA color tuples [r, g, b, a] in 0-1 range */
export type Color = [number, number, number, number];

const UNKNOWN_LAYER_COLOR: Color = [0.5, 0.5, 0.5, 0.5];

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
