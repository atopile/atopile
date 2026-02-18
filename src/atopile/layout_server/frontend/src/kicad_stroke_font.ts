import { Vec2 } from "./math";
import {
    KICAD_STROKE_GLYPHS_32_255,
    UNICODE_CODEPOINT_ALIASES,
    UNICODE_EXTRA_GLYPHS,
} from "./kicad_stroke_font_data";

const CP437_MIN = 32;
const CP437_MAX = 255;
const CP437_QMARK = 63;
const REF_CHAR_CODE = "R".charCodeAt(0);
const FONT_SCALE = 1 / 21;
const FONT_OFFSET = -10;
const INTERLINE_PITCH = 1.62;

type Glyph = {
    advance: number;
    strokes: Vec2[][];
    minY: number;
    maxY: number;
};

export type StrokeTextLayout = {
    strokes: Vec2[][];
    advance: number;
    minX: number;
    minY: number;
    maxX: number;
    maxY: number;
};

const glyphCache = new Map<number, Glyph>();
const layoutCache = new Map<string, StrokeTextLayout>();

function decodeCoord(c: string): number {
    return c.charCodeAt(0) - REF_CHAR_CODE;
}

function decodeGlyph(encoded: string): Glyph {
    const left = decodeCoord(encoded[0] ?? "R") * FONT_SCALE;
    const right = decodeCoord(encoded[1] ?? "R") * FONT_SCALE;

    const strokes: Vec2[][] = [];
    let currentStroke: Vec2[] | null = null;
    let minY = Number.POSITIVE_INFINITY;
    let maxY = Number.NEGATIVE_INFINITY;

    for (let i = 2; i + 1 < encoded.length; i += 2) {
        const xChar = encoded[i]!;
        const yChar = encoded[i + 1]!;
        if (xChar === " " && yChar === "R") {
            currentStroke = null;
            continue;
        }

        const x = decodeCoord(xChar) * FONT_SCALE - left;
        const y = (decodeCoord(yChar) + FONT_OFFSET) * FONT_SCALE;
        const point = new Vec2(x, y);
        if (currentStroke == null) {
            currentStroke = [];
            strokes.push(currentStroke);
        }
        currentStroke.push(point);
        minY = Math.min(minY, y);
        maxY = Math.max(maxY, y);
    }

    if (!Number.isFinite(minY)) {
        minY = 0;
        maxY = 0;
    }

    return {
        advance: right - left,
        strokes,
        minY,
        maxY,
    };
}

function getGlyph(charCode: number): Glyph {
    const cached = glyphCache.get(charCode);
    if (cached) {
        return cached;
    }

    const qmarkIndex = CP437_QMARK - CP437_MIN;
    let encoded: string | undefined;

    if (charCode >= CP437_MIN && charCode <= CP437_MAX) {
        encoded = KICAD_STROKE_GLYPHS_32_255[charCode - CP437_MIN];
    } else {
        encoded = UNICODE_EXTRA_GLYPHS[charCode];
    }
    encoded ??= KICAD_STROKE_GLYPHS_32_255[qmarkIndex]!;

    const glyph = decodeGlyph(encoded);
    glyphCache.set(charCode, glyph);
    return glyph;
}

function glyphCodeForChar(ch: string): number {
    const code = ch.codePointAt(0);
    if (code === undefined) {
        return CP437_QMARK;
    }

    const aliased = UNICODE_CODEPOINT_ALIASES[code];
    if (aliased !== undefined) {
        return aliased;
    }

    if (code >= CP437_MIN && code <= CP437_MAX) {
        return code;
    }

    const normalized = ch.normalize("NFKC");
    if (normalized.length === 1) {
        const normalizedCode = normalized.codePointAt(0);
        if (normalizedCode !== undefined) {
            const normalizedAliased = UNICODE_CODEPOINT_ALIASES[normalizedCode];
            return normalizedAliased ?? normalizedCode;
        }
    }

    return code;
}

export function layoutKicadStrokeText(text: string, charWidth: number, charHeight: number): StrokeTextLayout {
    const cacheKey = `${text}|${charWidth}|${charHeight}`;
    const cached = layoutCache.get(cacheKey);
    if (cached) {
        return cached;
    }

    const strokes: Vec2[][] = [];
    let cursorX = 0;
    let cursorY = 0;
    let minX = Number.POSITIVE_INFINITY;
    let minY = Number.POSITIVE_INFINITY;
    let maxX = Number.NEGATIVE_INFINITY;
    let maxY = Number.NEGATIVE_INFINITY;
    let lineMaxX = 0;
    const linePitch = charHeight * INTERLINE_PITCH;

    for (const ch of text) {
        if (ch === "\n") {
            lineMaxX = Math.max(lineMaxX, cursorX);
            cursorX = 0;
            cursorY += linePitch;
            continue;
        }
        if (ch === "\t") {
            const tab = charWidth * 3.28;
            const rem = cursorX % tab;
            cursorX += tab - rem;
            lineMaxX = Math.max(lineMaxX, cursorX);
            continue;
        }
        if (ch === " ") {
            cursorX += charWidth * 0.6;
            lineMaxX = Math.max(lineMaxX, cursorX);
            continue;
        }

        const glyph = getGlyph(glyphCodeForChar(ch));
        for (const stroke of glyph.strokes) {
            if (stroke.length === 0) {
                continue;
            }
            const transformed: Vec2[] = [];
            for (const p of stroke) {
                const tx = cursorX + p.x * charWidth;
                const ty = cursorY + p.y * charHeight;
                transformed.push(new Vec2(tx, ty));
                minX = Math.min(minX, tx);
                minY = Math.min(minY, ty);
                maxX = Math.max(maxX, tx);
                maxY = Math.max(maxY, ty);
            }
            strokes.push(transformed);
        }

        minY = Math.min(minY, cursorY + glyph.minY * charHeight);
        maxY = Math.max(maxY, cursorY + glyph.maxY * charHeight);
        cursorX += glyph.advance * charWidth;
        lineMaxX = Math.max(lineMaxX, cursorX);
    }

    if (!Number.isFinite(minX)) {
        minX = 0;
        maxX = lineMaxX;
        minY = 0;
        maxY = charHeight;
    } else {
        maxX = Math.max(maxX, lineMaxX);
    }

    const layout = { strokes, advance: lineMaxX, minX, minY, maxX, maxY };
    layoutCache.set(cacheKey, layout);
    return layout;
}

export function layoutKicadStrokeLine(text: string, charWidth: number, charHeight: number): StrokeTextLayout {
    return layoutKicadStrokeText(text, charWidth, charHeight);
}
