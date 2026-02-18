/** RGBA color tuples [r, g, b, a] in 0-1 range */
export type Color = [number, number, number, number];

/** Layer name → color mapping for PCB rendering */
export const LAYER_COLORS: Record<string, Color> = {
    "F.Cu":      [0.86, 0.23, 0.22, 0.88],
    "B.Cu":      [0.16, 0.28, 0.47, 0.88],
    "In1.Cu":    [0.70, 0.58, 0.24, 0.78],
    "In2.Cu":    [0.53, 0.40, 0.70, 0.78],
    "F.SilkS":   [0.92, 0.90, 0.62, 0.95],
    "B.SilkS":   [0.78, 0.86, 0.87, 0.92],
    "F.Mask":    [0.70, 0.35, 0.48, 0.42],
    "B.Mask":    [0.12, 0.19, 0.34, 0.38],
    "F.Paste":   [0.90, 0.80, 0.60, 0.48],
    "B.Paste":   [0.66, 0.74, 0.86, 0.48],
    "F.Fab":     [0.95, 0.62, 0.45, 0.90],
    "B.Fab":     [0.62, 0.73, 0.90, 0.90],
    "F.CrtYd":   [0.91, 0.91, 0.91, 0.62],
    "B.CrtYd":   [0.80, 0.85, 0.93, 0.62],
    "Edge.Cuts": [0.93, 0.95, 0.95, 1.00],
    "Dwgs.User": [0.70, 0.70, 0.72, 0.65],
    "Cmts.User": [0.74, 0.66, 0.84, 0.65],
};

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

export function getLayerColor(layer: string | null | undefined): Color {
    if (!layer) return [0.5, 0.5, 0.5, 0.5];
    if (layer.endsWith(".PadNumbers")) return [1.0, 1.0, 1.0, 1.0];
    if (layer.endsWith(".Nets")) return [1.0, 1.0, 1.0, 1.0];
    if (layer.endsWith(".Drill")) return [0.89, 0.82, 0.15, 1.0];
    return LAYER_COLORS[layer] ?? [0.5, 0.5, 0.5, 0.5];
}

export function getPadColor(layers: string[]): Color {
    const hasFront = layers.some(l => l === "F.Cu" || l === "*.Cu");
    const hasBack = layers.some(l => l === "B.Cu" || l === "*.Cu");
    if (hasFront && hasBack) return PAD_COLOR;
    if (hasFront) return PAD_FRONT_COLOR;
    if (hasBack) return PAD_BACK_COLOR;
    return PAD_COLOR;
}
