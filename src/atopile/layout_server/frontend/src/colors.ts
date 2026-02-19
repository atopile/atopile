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

/** Interface-type colors for pinout viewer pad coloring */
export const INTERFACE_COLORS: Record<string, Color> = {
    i2c:     [0.20, 0.50, 0.85, 0.9],
    spi:     [0.60, 0.30, 0.80, 0.9],
    uart:    [0.85, 0.55, 0.15, 0.9],
    usb:     [0.20, 0.70, 0.35, 0.9],
    gpio:    [0.25, 0.60, 0.65, 0.9],
    adc:     [0.80, 0.75, 0.20, 0.9],
    dac:     [0.70, 0.60, 0.20, 0.9],
    pwm:     [0.80, 0.35, 0.55, 0.9],
    jtag:    [0.55, 0.55, 0.85, 0.9],
    can:     [0.70, 0.45, 0.20, 0.9],
    i2s:     [0.40, 0.55, 0.80, 0.9],
    sdio:    [0.50, 0.70, 0.50, 0.9],
    power:   [0.75, 0.20, 0.20, 0.9],
    ground:  [0.40, 0.40, 0.40, 0.9],
};

/** Fallback palette for unknown interface types */
const FALLBACK_PALETTE: Color[] = [
    [0.55, 0.35, 0.70, 0.9],
    [0.35, 0.65, 0.45, 0.9],
    [0.70, 0.50, 0.30, 0.9],
    [0.40, 0.50, 0.75, 0.9],
    [0.65, 0.40, 0.55, 0.9],
    [0.50, 0.65, 0.35, 0.9],
];

const _fallbackCache = new Map<string, Color>();

/** Get a color for an interface name, using preset or fallback palette */
export function getInterfaceColor(name: string): Color {
    const lower = name.toLowerCase();
    if (INTERFACE_COLORS[lower]) return INTERFACE_COLORS[lower];
    // Check if any preset key is a substring (e.g., "i2c0" matches "i2c")
    for (const [key, color] of Object.entries(INTERFACE_COLORS)) {
        if (lower.includes(key)) return color;
    }
    let cached = _fallbackCache.get(lower);
    if (cached) return cached;
    // Simple hash to pick from palette
    let hash = 0;
    for (let i = 0; i < lower.length; i++) hash = (hash * 31 + lower.charCodeAt(i)) | 0;
    cached = FALLBACK_PALETTE[Math.abs(hash) % FALLBACK_PALETTE.length]!;
    _fallbackCache.set(lower, cached);
    return cached;
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
