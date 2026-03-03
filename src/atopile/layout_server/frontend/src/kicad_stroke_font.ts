import { Vec2 } from "./math";
import { glyph_data as NEWSTROKE_GLYPH_DATA, shared_glyphs as NEWSTROKE_SHARED_GLYPHS } from "./kicad_newstroke_glyphs";

const SPACE_CHAR_CODE = " ".charCodeAt(0);
const QMARK_GLYPH_INDEX = "?".charCodeAt(0) - SPACE_CHAR_CODE;
const PRELOAD_GLYPH_COUNT = 256;
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
let hasPreloadedGlyphs = false;

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

function loadGlyph(glyphIndex: number): Glyph | null {
    const data = NEWSTROKE_GLYPH_DATA[glyphIndex];
    if (data === undefined) {
        return null;
    }

    let encoded: string | undefined;
    if (typeof data === "string") {
        encoded = data;
    } else if (typeof data === "number") {
        encoded = NEWSTROKE_SHARED_GLYPHS[data];
    }
    if (encoded === undefined) {
        return null;
    }

    const glyph = decodeGlyph(encoded);
    glyphCache.set(glyphIndex, glyph);
    // Match KiCanvas behavior: free source data once decoded.
    NEWSTROKE_GLYPH_DATA[glyphIndex] = undefined;
    return glyph;
}

function preloadGlyphs(): void {
    if (hasPreloadedGlyphs) {
        return;
    }

    const count = Math.min(PRELOAD_GLYPH_COUNT, NEWSTROKE_GLYPH_DATA.length);
    for (let i = 0; i < count; i += 1) {
        if (!glyphCache.has(i)) {
            loadGlyph(i);
        }
    }

    hasPreloadedGlyphs = true;
}

function getGlyphByIndex(glyphIndex: number): Glyph {
    preloadGlyphs();

    if (glyphIndex < 0 || glyphIndex >= NEWSTROKE_GLYPH_DATA.length) {
        return getGlyphByIndex(QMARK_GLYPH_INDEX);
    }

    const cached = glyphCache.get(glyphIndex);
    if (cached) {
        return cached;
    }

    const loaded = loadGlyph(glyphIndex);
    if (loaded) {
        return loaded;
    }

    if (glyphIndex !== QMARK_GLYPH_INDEX) {
        return getGlyphByIndex(QMARK_GLYPH_INDEX);
    }

    // Ultimate fallback if '?' glyph cannot be loaded for any reason.
    return decodeGlyph("JZ");
}

function getGlyphForChar(ch: string): Glyph {
    const glyphIndex = ch.charCodeAt(0) - SPACE_CHAR_CODE;
    return getGlyphByIndex(glyphIndex);
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

        const glyph = getGlyphForChar(ch);
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
