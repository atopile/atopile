/** RGBA color tuples [r, g, b, a] in 0-1 range */
export type Color = [number, number, number, number];

/** Layer name → color mapping for PCB rendering */
export const LAYER_COLORS: Record<string, Color> = {
    "F.Cu":     [0.85, 0.20, 0.20, 0.8],
    "B.Cu":     [0.20, 0.40, 0.85, 0.8],
    "In1.Cu":   [0.85, 0.85, 0.20, 0.8],
    "In2.Cu":   [0.85, 0.40, 0.85, 0.8],
    "F.SilkS":  [0.0,  0.85, 0.85, 0.9],
    "B.SilkS":  [0.85, 0.0,  0.85, 0.9],
    "F.Mask":   [0.6,  0.15, 0.6,  0.4],
    "B.Mask":   [0.15, 0.6,  0.15, 0.4],
    "F.Paste":  [0.85, 0.55, 0.55, 0.5],
    "B.Paste":  [0.55, 0.55, 0.85, 0.5],
    "F.Fab":    [0.6,  0.6,  0.2,  0.7],
    "B.Fab":    [0.2,  0.2,  0.6,  0.7],
    "F.CrtYd":  [0.4,  0.4,  0.4,  0.5],
    "B.CrtYd":  [0.3,  0.3,  0.5,  0.5],
    "Edge.Cuts": [0.9, 0.85, 0.2,  1.0],
    "Dwgs.User": [0.6, 0.6,  0.6,  0.6],
    "Cmts.User": [0.4, 0.4,  0.8,  0.6],
};

export const PAD_COLOR: Color = [0.35, 0.60, 0.35, 0.9];
export const PAD_FRONT_COLOR: Color = [0.85, 0.20, 0.20, 0.7];
export const PAD_BACK_COLOR: Color = [0.20, 0.40, 0.85, 0.7];
export const VIA_COLOR: Color = [0.6, 0.6, 0.6, 0.9];
export const VIA_DRILL_COLOR: Color = [0.15, 0.15, 0.15, 1.0];
export const SELECTION_COLOR: Color = [1.0, 1.0, 1.0, 0.3];
export const BOARD_BG: Color = [0.08, 0.08, 0.08, 1.0];
export const ZONE_COLOR_ALPHA = 0.25;

export type SignalType = "digital" | "analog" | "power" | "ground" | "nc";

/** Shared signal-type colors for pinout table badges + footprint pad overrides */
export const SIGNAL_TYPE_COLORS: Record<SignalType, { pad: Color; badgeBg: string; badgeFg: string }> = {
    digital: {
        pad: [0.30, 0.55, 0.85, 0.9],
        badgeBg: "#264f78",
        badgeFg: "#9cdcfe",
    },
    analog: {
        pad: [0.30, 0.60, 0.30, 0.9],
        badgeBg: "#2d4a2d",
        badgeFg: "#a3d9a5",
    },
    power: {
        pad: [0.80, 0.30, 0.30, 0.9],
        badgeBg: "#5c2020",
        badgeFg: "#f5a8a8",
    },
    ground: {
        pad: [0.45, 0.45, 0.45, 0.9],
        badgeBg: "#3c3c3c",
        badgeFg: "#aaa",
    },
    nc: {
        pad: [0.35, 0.35, 0.35, 0.7],
        badgeBg: "#444",
        badgeFg: "#888",
    },
};

export function getSignalColors(signalType: string | null | undefined): {
    pad: Color;
    badgeBg: string;
    badgeFg: string;
} {
    const normalized = (signalType ?? "").toLowerCase();
    return SIGNAL_TYPE_COLORS[normalized as SignalType] ?? SIGNAL_TYPE_COLORS.digital;
}

/** Color for unconnected pads (outline only) */
export const UNCONNECTED_PAD_COLOR: Color = [0.45, 0.45, 0.45, 0.7];

/** Bright highlight color for selected pads */
export const PAD_HIGHLIGHT_COLOR: Color = [1.0, 1.0, 1.0, 0.6];

export function getLayerColor(layer: string | null | undefined): Color {
    if (!layer) return [0.5, 0.5, 0.5, 0.5];
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
