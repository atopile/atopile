import type {
  SchematicComponent,
  SchematicPin,
  SchematicSymbolFamily,
} from '../types/schematic';
import { getNormalizedComponentPinGeometry } from '../types/schematic';
import type { KicadSymbol } from '../types/symbol';
import { getSymbolRenderTuning, type SymbolRenderTuning } from '../symbol-catalog/symbolTuning';

export const CUSTOM_SYMBOL_BODY_BASE_Y = 0.05;

export interface CanonicalGlyphTransform {
  centerX: number;
  centerY: number;
  rotateToHorizontal: boolean;
  rotateClockwise: boolean;
  flip180: boolean;
  unit: number;
  cosBody: number;
  sinBody: number;
  bodyScaleX: number;
  bodyScaleY: number;
  bodyOffsetX: number;
  bodyOffsetY: number;
}

export interface PinAttachmentPoint {
  x: number;
  y: number;
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function normalizePinName(name: string): string {
  return name.trim().toLowerCase().replace(/[^a-z0-9]+/g, '');
}

function isAnodePinName(name: string): boolean {
  const token = normalizePinName(name);
  return token === 'a' || token === 'anode';
}

function isCathodePinName(name: string): boolean {
  const token = normalizePinName(name);
  return token === 'k' || token === 'cathode';
}

function findComponentPinBySemanticName(
  component: SchematicComponent,
  kind: 'anode' | 'cathode',
): SchematicPin | null {
  for (const pin of component.pins) {
    if (kind === 'anode' && isAnodePinName(pin.name)) return pin;
    if (kind === 'cathode' && isCathodePinName(pin.name)) return pin;
  }
  return null;
}

function findSymbolPinBySemanticName(
  symbol: KicadSymbol,
  kind: 'anode' | 'cathode',
): { x: number; y: number } | null {
  for (const pin of symbol.pins) {
    if (kind === 'anode' && isAnodePinName(pin.name)) return { x: pin.x, y: pin.y };
    if (kind === 'cathode' && isCathodePinName(pin.name)) return { x: pin.x, y: pin.y };
  }
  return null;
}

function transformCanonicalVector(
  dx: number,
  dy: number,
  rotateToHorizontal: boolean,
  rotateClockwise: boolean,
  flip180: boolean,
): { x: number; y: number } {
  const rx = rotateToHorizontal
    ? (rotateClockwise ? dy : -dy)
    : dx;
  const ry = rotateToHorizontal
    ? (rotateClockwise ? -dx : dx)
    : dy;
  if (flip180) {
    return { x: -rx, y: -ry };
  }
  return { x: rx, y: ry };
}

export function chipScale(packageCode?: string): number {
  const code = (packageCode ?? '').toUpperCase();
  if (!code) return 1;
  if (['01005', '0201', '0402'].includes(code)) return 0.82;
  if (['1206', '1210', '2010', '2512'].includes(code)) return 1.16;
  if (code.startsWith('SOD-') || code.startsWith('SOT-')) return 0.92;
  return 1;
}

export function symbolScaleFactors(
  family: SchematicSymbolFamily,
): { width: number; height: number } {
  switch (family) {
    case 'resistor':
      return { width: 0.9, height: 0.9 };
    case 'capacitor':
    case 'capacitor_polarized':
      return { width: 0.88, height: 0.94 };
    case 'inductor':
      return { width: 0.92, height: 0.9 };
    case 'diode':
      return { width: 0.9, height: 1.28 };
    case 'led':
      return { width: 0.95, height: 1.32 };
    case 'transistor_npn':
    case 'transistor_pnp':
    case 'mosfet_n':
    case 'mosfet_p':
      // Three-pin discretes use compact bodies even though the generic layout
      // may allocate an IC-like body width for pin labeling.
      return { width: 0.38, height: 0.62 };
    case 'testpoint':
      return { width: 0.74, height: 1.02 };
    case 'connector':
      return { width: 0.9, height: 0.9 };
    default:
      return { width: 0.88, height: 0.9 };
  }
}

function symbolBodyAxisScale(
  family: SchematicSymbolFamily,
): { x: number; y: number } {
  switch (family) {
    case 'capacitor':
      // Keep capacitor visual width aligned with diode/resistor families while
      // preserving plate height.
      return { x: 0.62, y: 1 };
    default:
      return { x: 1, y: 1 };
  }
}

export function getCanonicalGlyphTransform(
  component: SchematicComponent,
  family: SchematicSymbolFamily,
  symbol: KicadSymbol,
  tuning: SymbolRenderTuning,
): CanonicalGlyphTransform | null {
  if (symbol.bodyBounds.width <= 1e-6 || symbol.bodyBounds.height <= 1e-6) return null;

  const bounds = symbol.bodyBounds;
  const centerX = (bounds.minX + bounds.maxX) * 0.5;
  const centerY = (bounds.minY + bounds.maxY) * 0.5;
  const rotateToHorizontal =
    family !== 'connector'
    && family !== 'testpoint'
    && family !== 'transistor_npn'
    && family !== 'transistor_pnp'
    && family !== 'mosfet_n'
    && family !== 'mosfet_p'
    && bounds.height > bounds.width;
  let rotateClockwise = true;
  if (rotateToHorizontal && symbol.pins.length > 0 && component.pins.length > 0) {
    const componentPinsByNumber = new Map<string, { x: number; y: number }>();
    for (const cpin of component.pins) {
      const norm = getNormalizedComponentPinGeometry(component, cpin);
      componentPinsByNumber.set(cpin.number, { x: norm.x, y: norm.y });
    }

    let scoreCW = 0;
    let scoreCCW = 0;
    let matches = 0;
    for (const spin of symbol.pins) {
      const compPin = componentPinsByNumber.get(spin.number);
      if (!compPin) continue;
      matches += 1;
      const dx = spin.x - centerX;
      const dy = spin.y - centerY;
      const cwX = dy;
      const cwY = -dx;
      const ccwX = -dy;
      const ccwY = dx;
      scoreCW += cwX * compPin.x + cwY * compPin.y;
      scoreCCW += ccwX * compPin.x + ccwY * compPin.y;
    }

    if (matches > 0) {
      rotateClockwise = scoreCW >= scoreCCW;
    }
  }

  let flip180 = false;
  if (
    (family === 'diode' || family === 'led')
    && component.polarity === 'anode_cathode'
  ) {
    const compAnode = findComponentPinBySemanticName(component, 'anode');
    const compCathode = findComponentPinBySemanticName(component, 'cathode');
    const symbolAnode = findSymbolPinBySemanticName(symbol, 'anode');
    const symbolCathode = findSymbolPinBySemanticName(symbol, 'cathode');

    if (compAnode && compCathode && symbolAnode && symbolCathode) {
      const compAnodeGeom = getNormalizedComponentPinGeometry(component, compAnode);
      const compCathodeGeom = getNormalizedComponentPinGeometry(component, compCathode);
      const compVecX = compAnodeGeom.x - compCathodeGeom.x;
      const compVecY = compAnodeGeom.y - compCathodeGeom.y;
      const compLen = Math.hypot(compVecX, compVecY);

      if (compLen > 1e-6) {
        const symbolAnodeDelta = transformCanonicalVector(
          symbolAnode.x - centerX,
          symbolAnode.y - centerY,
          rotateToHorizontal,
          rotateClockwise,
          false,
        );
        const symbolCathodeDelta = transformCanonicalVector(
          symbolCathode.x - centerX,
          symbolCathode.y - centerY,
          rotateToHorizontal,
          rotateClockwise,
          false,
        );
        const symbolVecX = symbolAnodeDelta.x - symbolCathodeDelta.x;
        const symbolVecY = symbolAnodeDelta.y - symbolCathodeDelta.y;
        const symbolLen = Math.hypot(symbolVecX, symbolVecY);

        if (symbolLen > 1e-6) {
          const dot = symbolVecX * compVecX + symbolVecY * compVecY;
          flip180 = dot < 0;
        }
      }
    }
  }

  const effectiveW = rotateToHorizontal ? bounds.height : bounds.width;
  const effectiveH = rotateToHorizontal ? bounds.width : bounds.height;
  const factors = symbolScaleFactors(family);
  const scale = chipScale(component.packageCode);
  const targetW = Math.max(0.7, component.bodyWidth * factors.width * scale);
  const targetH = Math.max(0.55, component.bodyHeight * factors.height);
  const sx = targetW / Math.max(effectiveW, 1e-6);
  const sy = targetH / Math.max(effectiveH, 1e-6);
  const unit = Math.min(sx, sy);
  const rotationRad = (tuning.bodyRotationDeg * Math.PI) / 180;
  const axisScale = symbolBodyAxisScale(family);
  const tuningScaleX = clamp(tuning.bodyScaleX ?? 1, 0.1, 4);
  const tuningScaleY = clamp(tuning.bodyScaleY ?? 1, 0.1, 4);

  return {
    centerX,
    centerY,
    rotateToHorizontal,
    rotateClockwise,
    flip180,
    unit,
    cosBody: Math.cos(rotationRad),
    sinBody: Math.sin(rotationRad),
    bodyScaleX: axisScale.x * tuningScaleX,
    bodyScaleY: axisScale.y * tuningScaleY,
    bodyOffsetX: tuning.bodyOffsetX,
    bodyOffsetY: tuning.bodyOffsetY,
  };
}

export function transformCanonicalBodyPoint(
  x: number,
  y: number,
  transform: CanonicalGlyphTransform,
): { x: number; y: number } {
  const dx = x - transform.centerX;
  const dy = y - transform.centerY;
  const rotated = transformCanonicalVector(
    dx,
    dy,
    transform.rotateToHorizontal,
    transform.rotateClockwise,
    transform.flip180,
  );
  const rx = rotated.x;
  const ry = rotated.y;
  const px = rx * transform.unit;
  const py = ry * transform.unit;
  const rotatedX = px * transform.cosBody - py * transform.sinBody;
  const rotatedY = px * transform.sinBody + py * transform.cosBody;

  return {
    x: rotatedX * transform.bodyScaleX + transform.bodyOffsetX,
    y: rotatedY * transform.bodyScaleY + transform.bodyOffsetY,
  };
}

export function getCanonicalPinAttachmentMap(
  component: SchematicComponent,
  family: SchematicSymbolFamily,
  symbol: KicadSymbol,
  tuning: SymbolRenderTuning,
  bodyBaseYOffset = 0,
): Map<string, PinAttachmentPoint> {
  interface CandidatePin {
    number: string;
    name: string;
    attach: PinAttachmentPoint;
    pin: PinAttachmentPoint;
  }

  const out = new Map<string, PinAttachmentPoint>();
  const transform = getCanonicalGlyphTransform(component, family, symbol, tuning);
  if (!transform) return out;

  const candidates: CandidatePin[] = symbol.pins.map((pin) => {
    // KiCad pin orientation semantics can flip relative to our parser convention.
    // Ensure body-side attachment is the point closer to symbol center.
    const centerDistToPin = Math.hypot(pin.x - transform.centerX, pin.y - transform.centerY);
    const centerDistToBody = Math.hypot(
      pin.bodyX - transform.centerX,
      pin.bodyY - transform.centerY,
    );
    const bodyLocalX = centerDistToBody <= centerDistToPin
      ? pin.bodyX
      : (2 * pin.x - pin.bodyX);
    const bodyLocalY = centerDistToBody <= centerDistToPin
      ? pin.bodyY
      : (2 * pin.y - pin.bodyY);

    const attachRaw = transformCanonicalBodyPoint(bodyLocalX, bodyLocalY, transform);
    const pinRaw = transformCanonicalBodyPoint(pin.x, pin.y, transform);
    return {
      number: pin.number,
      name: pin.name,
      attach: { x: attachRaw.x, y: attachRaw.y + bodyBaseYOffset },
      pin: { x: pinRaw.x, y: pinRaw.y + bodyBaseYOffset },
    };
  });
  const used = new Set<number>();
  const byNumber = new Map<string, number[]>();
  for (let idx = 0; idx < candidates.length; idx += 1) {
    const key = candidates[idx].number;
    const bucket = byNumber.get(key);
    if (bucket) {
      bucket.push(idx);
    } else {
      byNumber.set(key, [idx]);
    }
  }

  const mapBySemanticPolarity = (
    semantic: 'anode' | 'cathode',
  ): void => {
    const componentPin = findComponentPinBySemanticName(component, semantic);
    if (!componentPin || out.has(componentPin.number)) return;
    const idx = candidates.findIndex((candidate, candidateIdx) => (
      !used.has(candidateIdx)
      && (
        (semantic === 'anode' && isAnodePinName(candidate.name))
        || (semantic === 'cathode' && isCathodePinName(candidate.name))
      )
    ));
    if (idx < 0) return;
    out.set(componentPin.number, candidates[idx].attach);
    used.add(idx);
  };

  if (
    (family === 'diode' || family === 'led')
    && component.polarity === 'anode_cathode'
  ) {
    mapBySemanticPolarity('anode');
    mapBySemanticPolarity('cathode');
  }

  // First pass: exact pin-number match where available.
  for (const cpin of component.pins) {
    if (out.has(cpin.number)) continue;
    const bucket = byNumber.get(cpin.number);
    if (!bucket) continue;
    const idx = bucket.find((candidateIdx) => !used.has(candidateIdx));
    if (idx == null) continue;
    out.set(cpin.number, candidates[idx].attach);
    used.add(idx);
  }

  // Second pass: nearest unassigned canonical pin by outer pin position.
  for (const cpin of component.pins) {
    if (out.has(cpin.number)) continue;
    const norm = getNormalizedComponentPinGeometry(component, cpin);
    let bestIdx = -1;
    let bestDist = Number.POSITIVE_INFINITY;
    for (let idx = 0; idx < candidates.length; idx += 1) {
      if (used.has(idx)) continue;
      const cand = candidates[idx];
      const dx = norm.x - cand.pin.x;
      const dy = norm.y - cand.pin.y;
      const dist = dx * dx + dy * dy;
      if (dist < bestDist) {
        bestDist = dist;
        bestIdx = idx;
      }
    }
    if (bestIdx >= 0) {
      used.add(bestIdx);
      out.set(cpin.number, candidates[bestIdx].attach);
    }
  }

  return out;
}

export function getTunedPinGeometry(
  component: SchematicComponent,
  pin: SchematicPin,
  symbolFamily: SchematicSymbolFamily | null,
  bodyAttachOverride?: PinAttachmentPoint | null,
  tuningOverride?: SymbolRenderTuning | null,
  bodyCenterOverride?: PinAttachmentPoint | null,
): { x: number; y: number; bodyX: number; bodyY: number } {
  const pinGeom = getNormalizedComponentPinGeometry(component, pin);
  const tuning = tuningOverride ?? getSymbolRenderTuning(symbolFamily);
  const hasOverride = !!bodyAttachOverride;
  const hasBodyTransform = Math.abs(tuning.bodyOffsetX) > 1e-6
    || Math.abs(tuning.bodyOffsetY) > 1e-6
    || Math.abs(tuning.bodyRotationDeg) > 1e-6;
  const hasLeadTuning = Math.abs(tuning.leadDelta) > 1e-6;

  if (!hasOverride && !hasBodyTransform && !hasLeadTuning) {
    return pinGeom;
  }

  let bodyX = bodyAttachOverride?.x ?? pinGeom.bodyX;
  let bodyY = bodyAttachOverride?.y ?? pinGeom.bodyY;
  let centerX = bodyCenterOverride?.x ?? 0;
  let centerY = bodyCenterOverride?.y ?? 0;

  if (!hasOverride && hasBodyTransform) {
    const angle = (tuning.bodyRotationDeg * Math.PI) / 180;
    const cosA = Math.cos(angle);
    const sinA = Math.sin(angle);
    const rx = bodyX * cosA - bodyY * sinA;
    const ry = bodyX * sinA + bodyY * cosA;
    bodyX = rx + tuning.bodyOffsetX;
    bodyY = ry + tuning.bodyOffsetY;
    centerX = tuning.bodyOffsetX;
    centerY = tuning.bodyOffsetY;
  } else if (!bodyCenterOverride && hasOverride) {
    // Canonical-body overrides already include body transform; default center
    // to tuning offset if caller did not provide one explicitly.
    centerX = tuning.bodyOffsetX;
    centerY = tuning.bodyOffsetY;
  }

  if (hasLeadTuning) {
    // Move only the body-side lead endpoint, keeping the external connection
    // point fixed. Positive leadDelta lengthens the visible lead.
    const axisX = bodyX - centerX;
    const axisY = bodyY - centerY;
    const axisLen = Math.hypot(axisX, axisY);
    if (axisLen > 1e-6) {
      const ux = axisX / axisLen;
      const uy = axisY / axisLen;
      const pinOutward = (pinGeom.x - centerX) * ux + (pinGeom.y - centerY) * uy;
      const minOutward = 0.04;
      const minLeadLength = 0.08;
      const maxOutward = pinOutward - minLeadLength;
      const targetOutward = axisLen - tuning.leadDelta;
      const outward = maxOutward > minOutward
        ? clamp(targetOutward, minOutward, maxOutward)
        : Math.max(minOutward, targetOutward);
      bodyX = centerX + ux * outward;
      bodyY = centerY + uy * outward;
    } else {
      const vx = pinGeom.x - bodyX;
      const vy = pinGeom.y - bodyY;
      const len = Math.hypot(vx, vy);
      if (len > 1e-6) {
        const ux = vx / len;
        const uy = vy / len;
        const maxShift = Math.max(len - 0.08, 0);
        const shift = clamp(tuning.leadDelta, -maxShift, maxShift);
        bodyX -= ux * shift;
        bodyY -= uy * shift;
      }
    }
  }

  return {
    x: pinGeom.x,
    y: pinGeom.y,
    bodyX,
    bodyY,
  };
}
