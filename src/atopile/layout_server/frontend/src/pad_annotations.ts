import { fpTransform, rotatedRectExtents } from "./geometry";
import type { FootprintModel, PadModel } from "./types";

const PAD_ANNOTATION_BOX_RATIO = 0.78;
const PAD_ANNOTATION_MAJOR_FIT = 0.96;
const PAD_ANNOTATION_MINOR_FIT = 0.88;
const PAD_ANNOTATION_CHAR_SCALE = 0.60;
const PAD_ANNOTATION_MIN_CHAR_H = 0.02;
const PAD_ANNOTATION_CHAR_W_RATIO = 0.72;
const PAD_ANNOTATION_LINE_SPACING = 1.08;
const PAD_ANNOTATION_STROKE_SCALE = 0.22;
const PAD_ANNOTATION_STROKE_MIN = 0.02;
const PAD_ANNOTATION_STROKE_MAX = 0.16;
const PAD_NUMBER_BADGE_SIZE_RATIO = 0.36;
const PAD_NUMBER_BADGE_MARGIN_RATIO = 0.05;
const PAD_NUMBER_CHAR_SCALE = 0.80;
const PAD_NUMBER_MIN_CHAR_H = 0.04;

export type NameGeometry = {
    text: string;
    x: number;
    y: number;
    rotation: number;
    charW: number;
    charH: number;
    thickness: number;
};

export type NumberGeometry = {
    text: string;
    badgeCenterX: number;
    badgeCenterY: number;
    badgeRadius: number;
    labelFit: [number, number, number] | null;
};

export type LayerAnnotationGeometry = {
    names: NameGeometry[];
    numbers: NumberGeometry[];
};

function estimateStrokeTextAdvance(text: string): number {
    if (!text) return 0.6;
    const narrow = new Set(["1", "I", "i", "l", "|", "!", ".", ",", ":", ";", "'", "`"]);
    const wide = new Set(["M", "W", "@", "%", "#"]);
    let advance = 0;
    for (const ch of text) {
        if (ch === " ") advance += 0.6;
        else if (narrow.has(ch)) advance += 0.45;
        else if (wide.has(ch)) advance += 0.95;
        else advance += 0.72;
    }
    return Math.max(advance, 0.6);
}

function fitTextInsideBox(
    text: string,
    boxW: number,
    boxH: number,
    minCharH = PAD_ANNOTATION_MIN_CHAR_H,
    charScale = PAD_ANNOTATION_CHAR_SCALE,
): [number, number, number] | null {
    if (boxW <= 0 || boxH <= 0) return null;
    const lines = text
        .split("\n")
        .map(line => line.trim())
        .filter(line => line.length > 0);
    if (lines.length === 0) return null;
    const usableW = Math.max(0, boxW * PAD_ANNOTATION_BOX_RATIO);
    const usableH = Math.max(0, boxH * PAD_ANNOTATION_BOX_RATIO);
    if (usableW <= 0 || usableH <= 0) return null;
    const vertical = usableH > usableW;
    const major = vertical ? usableH : usableW;
    const minor = vertical ? usableW : usableH;
    const maxAdvance = Math.max(...lines.map(estimateStrokeTextAdvance));
    const lineHeightUnits = 1 + (lines.length - 1) * PAD_ANNOTATION_LINE_SPACING;
    const maxHByWidth = major / Math.max(maxAdvance * PAD_ANNOTATION_CHAR_W_RATIO, 1e-6);
    const maxHByHeight = minor / Math.max(lineHeightUnits, 1e-6);
    let charH = Math.min(
        maxHByWidth * PAD_ANNOTATION_MAJOR_FIT,
        maxHByHeight * PAD_ANNOTATION_MINOR_FIT,
    );
    charH *= charScale;
    if (charH < minCharH) return null;
    const charW = charH * PAD_ANNOTATION_CHAR_W_RATIO;
    const thickness = Math.min(
        PAD_ANNOTATION_STROKE_MAX,
        Math.max(PAD_ANNOTATION_STROKE_MIN, charH * PAD_ANNOTATION_STROKE_SCALE),
    );
    return [charW, charH, thickness];
}

function fitPadNameLabel(text: string, boxW: number, boxH: number): [string, [number, number, number]] | null {
    const displayText = text.trim();
    if (!displayText) return null;
    const candidates: string[] = [displayText];
    const dashIndexes: number[] = [];
    for (let i = 0; i < displayText.length; i++) {
        if (displayText[i] === "-") dashIndexes.push(i);
    }
    for (const idx of dashIndexes) {
        const left = displayText.slice(0, idx).trim();
        const right = displayText.slice(idx + 1).trim();
        if (!left || !right) continue;
        candidates.push(`${left}\n${right}`);
    }

    let best: [string, [number, number, number]] | null = null;
    for (const candidate of candidates) {
        const fit = fitTextInsideBox(candidate, boxW, boxH);
        if (!fit) continue;
        if (!best || fit[1] > best[1][1]) {
            best = [candidate, fit];
        }
    }
    return best;
}

function padLabelWorldRotation(totalPadRotationDeg: number, padW: number, padH: number): number {
    if (padW <= 0 || padH <= 0) return 0;
    if (Math.abs(padW - padH) <= 1e-6) return 0;
    const longAxisDeg = padW > padH ? totalPadRotationDeg : totalPadRotationDeg + 90;
    const axisX = Math.abs(Math.cos(longAxisDeg * Math.PI / 180));
    const axisY = Math.abs(Math.sin(longAxisDeg * Math.PI / 180));
    return axisY > axisX ? 90 : 0;
}

function resolvePad(fp: FootprintModel, padIndex: number, padName: string): PadModel | null {
    const byIndex = fp.pads[padIndex];
    if (byIndex && byIndex.name === padName) {
        return byIndex;
    }
    for (const pad of fp.pads) {
        if (pad.name === padName) return pad;
    }
    return null;
}

export function buildPadAnnotationGeometry(
    fp: FootprintModel,
    hiddenLayers?: Set<string>,
): Map<string, LayerAnnotationGeometry> {
    const hidden = hiddenLayers ?? new Set<string>();
    const layerGeometry = new Map<string, LayerAnnotationGeometry>();
    const ensureLayerGeometry = (layerName: string): LayerAnnotationGeometry => {
        let entry = layerGeometry.get(layerName);
        if (!entry) {
            entry = { names: [], numbers: [] };
            layerGeometry.set(layerName, entry);
        }
        return entry;
    };

    for (const annotation of fp.pad_names) {
        if (!annotation.text.trim()) continue;
        const pad = resolvePad(fp, annotation.pad_index, annotation.pad);
        if (!pad) continue;
        const totalRotation = (fp.at.r || 0) + (pad.at.r || 0);
        const [bboxW, bboxH] = rotatedRectExtents(pad.size.w, pad.size.h, totalRotation);
        const fitted = fitPadNameLabel(annotation.text, bboxW, bboxH);
        if (!fitted) continue;
        const [displayText, [charW, charH, thickness]] = fitted;
        const worldCenter = fpTransform(fp.at, pad.at.x, pad.at.y);
        const textRotation = padLabelWorldRotation(totalRotation, pad.size.w, pad.size.h);
        for (const layerName of annotation.layer_ids) {
            if (hidden.has(layerName)) continue;
            ensureLayerGeometry(layerName).names.push({
                text: displayText,
                x: worldCenter.x,
                y: worldCenter.y,
                rotation: textRotation,
                charW,
                charH,
                thickness,
            });
        }
    }

    for (const annotation of fp.pad_numbers) {
        if (!annotation.text.trim()) continue;
        const pad = resolvePad(fp, annotation.pad_index, annotation.pad);
        if (!pad) continue;
        const totalRotation = (fp.at.r || 0) + (pad.at.r || 0);
        const [bboxW, bboxH] = rotatedRectExtents(pad.size.w, pad.size.h, totalRotation);
        const badgeDiameter = Math.max(Math.min(bboxW, bboxH) * PAD_NUMBER_BADGE_SIZE_RATIO, 0.18);
        const badgeRadius = badgeDiameter / 2;
        const margin = Math.max(Math.min(bboxW, bboxH) * PAD_NUMBER_BADGE_MARGIN_RATIO, 0.03);
        const worldCenter = fpTransform(fp.at, pad.at.x, pad.at.y);
        const badgeCenterX = worldCenter.x - (bboxW / 2) + margin + badgeRadius;
        const badgeCenterY = worldCenter.y - (bboxH / 2) + margin + badgeRadius;
        const labelFit = fitTextInsideBox(
            annotation.text,
            badgeDiameter * 0.92,
            badgeDiameter * 0.92,
            PAD_NUMBER_MIN_CHAR_H,
            PAD_NUMBER_CHAR_SCALE,
        );
        for (const layerName of annotation.layer_ids) {
            if (hidden.has(layerName)) continue;
            ensureLayerGeometry(layerName).numbers.push({
                text: annotation.text,
                badgeCenterX,
                badgeCenterY,
                badgeRadius,
                labelFit,
            });
        }
    }

    return layerGeometry;
}
