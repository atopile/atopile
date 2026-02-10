import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type PointerEvent as ReactPointerEvent,
} from 'react';
import { getCanonicalKicadSymbol } from '../../src/schematic-viewer/symbol-catalog/canonicalSymbolCatalog';
import {
  SYMBOL_RENDER_TUNING,
  type SymbolRenderTuning,
} from '../../src/schematic-viewer/symbol-catalog/symbolTuning';
import {
  getSymbolVisualTuning,
  type SymbolLabelVisualTuning,
  type SymbolPackageLabelVisualTuning,
  type SymbolVisualTuning,
} from '../../src/schematic-viewer/symbol-catalog/symbolVisualTuning';
import type { KicadArc, KicadSymbol } from '../../src/schematic-viewer/types/symbol';
import {
  getComponentGridAlignmentOffset,
  POWER_PORT_H,
  POWER_PORT_W,
  type SchematicComponent,
  type SchematicPin,
  type SchematicSymbolFamily,
  transformPinOffset,
} from '../../src/schematic-viewer/types/schematic';
import { getUprightTextTransform } from '../../src/schematic-viewer/lib/itemTransform';
import {
  CUSTOM_SYMBOL_BODY_BASE_Y,
  getCanonicalGlyphTransform,
  getCanonicalPinAttachmentMap,
  getTunedPinGeometry,
  transformCanonicalBodyPoint,
} from '../../src/schematic-viewer/three/symbolRenderGeometry';

type ComponentFamily = Exclude<SchematicSymbolFamily, 'connector'>;
type PowerFamily = 'vcc' | 'gnd';
type Family = ComponentFamily | PowerFamily;

type Point = { x: number; y: number };

type SymbolTuning = SymbolRenderTuning;
type LabelTuning = SymbolLabelVisualTuning;
type PackageLabelTuning = SymbolPackageLabelVisualTuning;
type VisualTuning = SymbolVisualTuning;

interface PreviewModel {
  bodyPolylines: Point[][];
  bodyFillPolygons: Point[][];
  bodyCircles: Array<{ center: Point; radius: number }>;
  leads: Array<{ attach: Point; pin: Point; rawPin: Point; number: string; name: string }>;
  centerCross: { h0: Point; h1: Point; v0: Point; v1: Point };
  viewBox: { x: number; y: number; width: number; height: number };
  gridOffset: Point;
}

interface DragState {
  target: 'designator' | 'value' | 'package';
  pointerId: number;
  startClientX: number;
  startClientY: number;
  startOffsetX: number;
  startOffsetY: number;
}

const FAMILIES: Family[] = [
  'resistor',
  'capacitor',
  'capacitor_polarized',
  'inductor',
  'diode',
  'led',
  'transistor_npn',
  'transistor_pnp',
  'mosfet_n',
  'mosfet_p',
  'testpoint',
  'vcc',
  'gnd',
];

const PIN_COUNT_BY_FAMILY: Record<Family, number> = {
  resistor: 2,
  capacitor: 2,
  capacitor_polarized: 2,
  inductor: 2,
  diode: 2,
  led: 2,
  transistor_npn: 3,
  transistor_pnp: 3,
  mosfet_n: 3,
  mosfet_p: 3,
  testpoint: 2,
  vcc: 1,
  gnd: 1,
};

function isPowerFamily(family: Family): family is PowerFamily {
  return family === 'vcc' || family === 'gnd';
}

function isComponentFamily(family: Family): family is ComponentFamily {
  return !isPowerFamily(family);
}

const BASE_TWO_PINS: SchematicPin[] = [
  {
    number: '1',
    name: 'pin1',
    side: 'left',
    electricalType: 'passive',
    category: 'signal',
    x: -3.81,
    y: 0,
    bodyX: -1.27,
    bodyY: 0,
  },
  {
    number: '2',
    name: 'pin2',
    side: 'right',
    electricalType: 'passive',
    category: 'signal',
    x: 3.81,
    y: 0,
    bodyX: 1.27,
    bodyY: 0,
  },
];

const BASE_SINGLE_PIN: SchematicPin = {
  number: '1',
  name: 'pin1',
  side: 'left',
  electricalType: 'passive',
  category: 'signal',
  x: -5.08,
  y: 0,
  bodyX: -2.54,
  bodyY: 0,
};

const BASE_THREE_PINS: SchematicPin[] = [
  {
    number: '1',
    name: 'pin1',
    side: 'left',
    electricalType: 'passive',
    category: 'signal',
    x: -5.08,
    y: 0,
    bodyX: -2.54,
    bodyY: 0,
  },
  {
    number: '2',
    name: 'pin2',
    side: 'right',
    electricalType: 'passive',
    category: 'signal',
    x: 2.54,
    y: 5.08,
    bodyX: 2.54,
    bodyY: 2.54,
  },
  {
    number: '3',
    name: 'pin3',
    side: 'right',
    electricalType: 'passive',
    category: 'signal',
    x: 2.54,
    y: -5.08,
    bodyX: 2.54,
    bodyY: -2.54,
  },
];

function fixtureComponent(
  family: ComponentFamily,
  packageCode: string,
  designator: string,
  pinNames?: [string, string],
): SchematicComponent {
  const [p1, p2] = pinNames ?? ['pin1', 'pin2'];
  const pins: SchematicPin[] = BASE_TWO_PINS.map((pin) => ({
    ...pin,
    name: pin.number === '1' ? p1 : p2,
  }));

  return {
    kind: 'component',
    id: `fixture_${family}`,
    name: `fixture_${family}`,
    designator,
    reference: designator[0] ?? 'X',
    symbolFamily: family,
    packageCode,
    pins,
    bodyWidth: 2.54,
    bodyHeight: 2.04,
  };
}

function fixtureThreePinComponent(
  family: ComponentFamily,
  packageCode: string,
  designator: string,
  pinNames?: [string, string, string],
): SchematicComponent {
  const [p1, p2, p3] = pinNames ?? ['pin1', 'pin2', 'pin3'];
  const pins: SchematicPin[] = BASE_THREE_PINS.map((pin) => ({
    ...pin,
    name: pin.number === '1' ? p1 : (pin.number === '2' ? p2 : p3),
  }));

  return {
    kind: 'component',
    id: `fixture_${family}`,
    name: `fixture_${family}`,
    designator,
    reference: designator[0] ?? 'X',
    symbolFamily: family,
    packageCode,
    pins,
    bodyWidth: 14,
    bodyHeight: 7.08,
  };
}

function fixturePowerSymbol(
  family: PowerFamily,
  label: string,
): SchematicComponent {
  const pinY = family === 'gnd' ? POWER_PORT_H / 2 : -POWER_PORT_H / 2;
  return {
    kind: 'component',
    id: `fixture_${family}`,
    name: `fixture_${family}`,
    designator: label,
    reference: 'P',
    pins: [
      {
        ...BASE_SINGLE_PIN,
        x: 0,
        y: pinY,
        bodyX: 0,
        bodyY: pinY,
        name: 'pin',
      },
    ],
    bodyWidth: POWER_PORT_W,
    bodyHeight: POWER_PORT_H,
  };
}

const FIXTURE_BY_FAMILY: Record<Family, SchematicComponent> = {
  resistor: fixtureComponent('resistor', '0402', 'R1', ['A', 'B']),
  capacitor: fixtureComponent('capacitor', '0603', 'C1', ['VCC', 'GND']),
  capacitor_polarized: fixtureComponent('capacitor_polarized', '1206', 'C2', ['positive', 'negative']),
  inductor: fixtureComponent('inductor', '0805', 'L1', ['A', 'B']),
  diode: fixtureComponent('diode', 'SOD-123', 'D1', ['anode', 'cathode']),
  led: fixtureComponent('led', '0603', 'D2', ['anode', 'cathode']),
  transistor_npn: fixtureThreePinComponent('transistor_npn', 'SOT-23', 'Q1', ['B', 'C', 'E']),
  transistor_pnp: fixtureThreePinComponent('transistor_pnp', 'SOT-23', 'Q2', ['B', 'C', 'E']),
  mosfet_n: fixtureThreePinComponent('mosfet_n', 'SOT-23', 'Q3', ['G', 'D', 'S']),
  mosfet_p: fixtureThreePinComponent('mosfet_p', 'SOT-23', 'Q4', ['G', 'D', 'S']),
  // Keep testpoint fixture geometry aligned to exported schematic data:
  // two-pin compact body, with runtime rendering only showing pin "1".
  testpoint: fixtureComponent('testpoint', 'TESTPOINT', 'TP1', ['contact', 'unused']),
  vcc: fixturePowerSymbol('vcc', 'VCC'),
  gnd: fixturePowerSymbol('gnd', 'GND'),
};

const STORAGE_KEY = 'atopile.symbol_tuner.v2';
const VISUAL_STORAGE_KEY = 'atopile.symbol_tuner.visual.v1';

function shouldRestoreStoredTunings(): boolean {
  if (typeof window === 'undefined') return false;
  try {
    const params = new URLSearchParams(window.location.search);
    return params.get('restore') === '1';
  } catch {
    return false;
  }
}

const DEFAULT_TUNINGS: Record<Family, SymbolTuning> = {
  resistor: { ...SYMBOL_RENDER_TUNING.resistor },
  capacitor: { ...SYMBOL_RENDER_TUNING.capacitor },
  capacitor_polarized: { ...SYMBOL_RENDER_TUNING.capacitor_polarized },
  inductor: { ...SYMBOL_RENDER_TUNING.inductor },
  diode: { ...SYMBOL_RENDER_TUNING.diode },
  led: { ...SYMBOL_RENDER_TUNING.led },
  transistor_npn: { ...SYMBOL_RENDER_TUNING.transistor_npn },
  transistor_pnp: { ...SYMBOL_RENDER_TUNING.transistor_pnp },
  mosfet_n: { ...SYMBOL_RENDER_TUNING.mosfet_n },
  mosfet_p: { ...SYMBOL_RENDER_TUNING.mosfet_p },
  testpoint: { ...SYMBOL_RENDER_TUNING.testpoint },
  vcc: {
    bodyOffsetX: 0,
    bodyOffsetY: 1.2,
    bodyRotationDeg: 0,
    bodyScaleX: 2,
    bodyScaleY: 2,
    leadDelta: 0,
  },
  gnd: {
    bodyOffsetX: 0,
    bodyOffsetY: 0.15,
    bodyRotationDeg: 0,
    bodyScaleX: 2,
    bodyScaleY: 2,
    leadDelta: 0,
  },
};

function defaultVisualTuning(family: Family, component: SchematicComponent): VisualTuning {
  if (isComponentFamily(family)) {
    return getSymbolVisualTuning(family, component);
  }

  return {
    symbolStrokeWidth: 0.26,
    leadStrokeWidth: 0.28,
    connectionDotRadius: 0.17,
    designator: {
      offsetX: 0,
      offsetY: -Math.min(component.bodyHeight * 0.36, 0.96),
      fontSize: 0.62,
      rotationDeg: 0,
    },
    value: {
      offsetX: 0,
      offsetY: 0,
      fontSize: 0.5,
      rotationDeg: 0,
    },
    package: {
      offsetX: 0,
      offsetY: 0,
      fontSize: 0.52,
      rotationDeg: 0,
      followInstanceRotation: true,
    },
  };
}

const DEFAULT_VISUAL_TUNINGS: Record<Family, VisualTuning> = (() => {
  const out = Object.fromEntries(
    FAMILIES.map((family) => [family, defaultVisualTuning(family, FIXTURE_BY_FAMILY[family])]),
  ) as Record<Family, VisualTuning>;
  out.vcc = {
    ...out.vcc,
    designator: {
      ...out.vcc.designator,
      offsetX: 0,
      offsetY: 1.05,
      fontSize: 0.54,
    },
  };
  out.gnd = {
    ...out.gnd,
    designator: {
      ...out.gnd.designator,
      offsetX: 0,
      offsetY: 1.1,
      fontSize: 0.54,
    },
  };
  return out;
})();

function clamp(v: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, v));
}

function normalizeAngle(theta: number): number {
  const twoPi = Math.PI * 2;
  let out = theta % twoPi;
  if (out < 0) out += twoPi;
  return out;
}

function isAngleOnCCWPath(start: number, target: number, end: number): boolean {
  const twoPi = Math.PI * 2;
  const se = (end - start + twoPi) % twoPi;
  const st = (target - start + twoPi) % twoPi;
  return st <= se;
}

function arcCircleFromThreePoints(
  start: Point,
  mid: Point,
  end: Point,
): { cx: number; cy: number; radius: number } | null {
  const x1 = start.x;
  const y1 = start.y;
  const x2 = mid.x;
  const y2 = mid.y;
  const x3 = end.x;
  const y3 = end.y;

  const d = 2 * (
    x1 * (y2 - y3)
    + x2 * (y3 - y1)
    + x3 * (y1 - y2)
  );
  if (Math.abs(d) < 1e-9) return null;

  const cx = (
    (x1 * x1 + y1 * y1) * (y2 - y3)
    + (x2 * x2 + y2 * y2) * (y3 - y1)
    + (x3 * x3 + y3 * y3) * (y1 - y2)
  ) / d;
  const cy = (
    (x1 * x1 + y1 * y1) * (x3 - x2)
    + (x2 * x2 + y2 * y2) * (x1 - x3)
    + (x3 * x3 + y3 * y3) * (x2 - x1)
  ) / d;

  return { cx, cy, radius: Math.hypot(x1 - cx, y1 - cy) };
}

function kicadArcPoints(arc: KicadArc, segments = 20): Point[] {
  const start: Point = { x: arc.startX, y: arc.startY };
  const mid: Point = { x: arc.midX, y: arc.midY };
  const end: Point = { x: arc.endX, y: arc.endY };
  const circle = arcCircleFromThreePoints(start, mid, end);
  if (!circle) return [start, mid, end];

  const { cx, cy, radius } = circle;
  const a0 = normalizeAngle(Math.atan2(start.y - cy, start.x - cx));
  const am = normalizeAngle(Math.atan2(mid.y - cy, mid.x - cx));
  const a1 = normalizeAngle(Math.atan2(end.y - cy, end.x - cx));
  const ccw = isAngleOnCCWPath(a0, am, a1);
  const twoPi = Math.PI * 2;
  const span = ccw ? (a1 - a0 + twoPi) % twoPi : (a0 - a1 + twoPi) % twoPi;

  const pts: Point[] = [];
  for (let i = 0; i <= segments; i += 1) {
    const t = i / segments;
    const angle = ccw ? a0 + span * t : a0 - span * t;
    pts.push({ x: cx + Math.cos(angle) * radius, y: cy + Math.sin(angle) * radius });
  }
  return pts;
}

function pointsToBounds(points: Point[]): { minX: number; maxX: number; minY: number; maxY: number } {
  if (points.length === 0) {
    return { minX: -1, maxX: 1, minY: -1, maxY: 1 };
  }
  const xs = points.map((p) => p.x);
  const ys = points.map((p) => p.y);
  return {
    minX: Math.min(...xs),
    maxX: Math.max(...xs),
    minY: Math.min(...ys),
    maxY: Math.max(...ys),
  };
}

function parseStoredTunings(raw: string): Record<Family, SymbolTuning> | null {
  try {
    const parsed = JSON.parse(raw) as Record<string, SymbolTuning>;
    const out: Record<Family, SymbolTuning> = { ...DEFAULT_TUNINGS };
    for (const family of FAMILIES) {
      const item = parsed[family];
      if (!item) continue;
      out[family] = {
        bodyOffsetX: Number.isFinite(item.bodyOffsetX) ? item.bodyOffsetX : 0,
        bodyOffsetY: Number.isFinite(item.bodyOffsetY) ? item.bodyOffsetY : 0,
        bodyRotationDeg: Number.isFinite(item.bodyRotationDeg) ? item.bodyRotationDeg : 0,
        bodyScaleX: Number.isFinite(item.bodyScaleX) ? item.bodyScaleX : 1,
        bodyScaleY: Number.isFinite(item.bodyScaleY) ? item.bodyScaleY : 1,
        leadDelta: Number.isFinite(item.leadDelta) ? item.leadDelta : 0,
      };
    }
    return out;
  } catch {
    return null;
  }
}

function initialTunings(): Record<Family, SymbolTuning> {
  if (!shouldRestoreStoredTunings()) return { ...DEFAULT_TUNINGS };
  if (typeof window === 'undefined') return { ...DEFAULT_TUNINGS };
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) return { ...DEFAULT_TUNINGS };
  return parseStoredTunings(raw) ?? { ...DEFAULT_TUNINGS };
}

function parseStoredVisualTunings(raw: string): Record<Family, VisualTuning> | null {
  try {
    const parsed = JSON.parse(raw) as Record<string, Partial<VisualTuning>>;
    const out: Record<Family, VisualTuning> = { ...DEFAULT_VISUAL_TUNINGS };
    for (const family of FAMILIES) {
      const item = parsed[family];
      if (!item) continue;
      const defaults = DEFAULT_VISUAL_TUNINGS[family];
      out[family] = {
        symbolStrokeWidth: Number.isFinite(item.symbolStrokeWidth)
          ? item.symbolStrokeWidth as number
          : defaults.symbolStrokeWidth,
        leadStrokeWidth: Number.isFinite(item.leadStrokeWidth)
          ? item.leadStrokeWidth as number
          : defaults.leadStrokeWidth,
        connectionDotRadius: Number.isFinite(item.connectionDotRadius)
          ? item.connectionDotRadius as number
          : defaults.connectionDotRadius,
        designator: {
          offsetX: Number.isFinite(item.designator?.offsetX)
            ? item.designator!.offsetX as number
            : defaults.designator.offsetX,
          offsetY: Number.isFinite(item.designator?.offsetY)
            ? item.designator!.offsetY as number
            : defaults.designator.offsetY,
          fontSize: Number.isFinite(item.designator?.fontSize)
            ? item.designator!.fontSize as number
            : defaults.designator.fontSize,
          rotationDeg: Number.isFinite(item.designator?.rotationDeg)
            ? item.designator!.rotationDeg as number
            : defaults.designator.rotationDeg,
        },
        value: {
          offsetX: Number.isFinite(item.value?.offsetX)
            ? item.value!.offsetX as number
            : defaults.value.offsetX,
          offsetY: Number.isFinite(item.value?.offsetY)
            ? item.value!.offsetY as number
            : defaults.value.offsetY,
          fontSize: Number.isFinite(item.value?.fontSize)
            ? item.value!.fontSize as number
            : defaults.value.fontSize,
          rotationDeg: Number.isFinite(item.value?.rotationDeg)
            ? item.value!.rotationDeg as number
            : defaults.value.rotationDeg,
        },
        package: {
          offsetX: Number.isFinite(item.package?.offsetX)
            ? item.package!.offsetX as number
            : defaults.package.offsetX,
          offsetY: Number.isFinite(item.package?.offsetY)
            ? item.package!.offsetY as number
            : defaults.package.offsetY,
          fontSize: Number.isFinite(item.package?.fontSize)
            ? item.package!.fontSize as number
            : defaults.package.fontSize,
          rotationDeg: Number.isFinite(item.package?.rotationDeg)
            ? item.package!.rotationDeg as number
            : defaults.package.rotationDeg,
          followInstanceRotation: typeof item.package?.followInstanceRotation === 'boolean'
            ? item.package!.followInstanceRotation
            : defaults.package.followInstanceRotation,
        },
      };
    }
    return out;
  } catch {
    return null;
  }
}

function initialVisualTunings(): Record<Family, VisualTuning> {
  if (!shouldRestoreStoredTunings()) return { ...DEFAULT_VISUAL_TUNINGS };
  if (typeof window === 'undefined') return { ...DEFAULT_VISUAL_TUNINGS };
  const raw = window.localStorage.getItem(VISUAL_STORAGE_KEY);
  if (!raw) return { ...DEFAULT_VISUAL_TUNINGS };
  return parseStoredVisualTunings(raw) ?? { ...DEFAULT_VISUAL_TUNINGS };
}
function applyInstanceTransform(
  point: Point,
  rotationDeg: number,
  mirrorX: boolean,
  mirrorY: boolean,
): Point {
  const transformed = transformPinOffset(
    point.x,
    point.y,
    rotationDeg,
    mirrorX,
    mirrorY,
  );
  return { x: transformed.x, y: transformed.y };
}

function applyInverseInstanceTransform(
  point: Point,
  rotationDeg: number,
  mirrorX: boolean,
  mirrorY: boolean,
): Point {
  const rot = ((rotationDeg % 360) + 360) % 360;
  let x = point.x;
  let y = point.y;

  // Inverse of rotate-CCW is rotate-CW.
  switch (rot) {
    case 90:
      [x, y] = [y, -x];
      break;
    case 180:
      [x, y] = [-x, -y];
      break;
    case 270:
      [x, y] = [-y, x];
      break;
    default:
      break;
  }

  // Mirrors are self-inverse.
  if (mirrorX) x = -x;
  if (mirrorY) y = -y;
  return { x, y };
}

function labelPositionToWorld(
  local: Point,
  preview: PreviewModel,
  rotationDeg: number,
  mirrorX: boolean,
  mirrorY: boolean,
): Point {
  return applyInstanceTransform(
    { x: local.x + preview.gridOffset.x, y: local.y + preview.gridOffset.y },
    rotationDeg,
    mirrorX,
    mirrorY,
  );
}

function estimateTextHalfWidth(text: string, fontSize: number): number {
  return Math.max(0.3, text.length * fontSize * 0.28);
}

function expandViewBoxWithLabels(
  viewBox: PreviewModel['viewBox'],
  labels: Array<{ position: Point; text: string; fontSize: number }>,
): PreviewModel['viewBox'] {
  let minX = viewBox.x;
  let maxX = viewBox.x + viewBox.width;
  let minY = -viewBox.y - viewBox.height;
  let maxY = -viewBox.y;

  for (const label of labels) {
    const halfW = estimateTextHalfWidth(label.text, label.fontSize);
    const halfH = Math.max(0.35, label.fontSize * 0.65);
    minX = Math.min(minX, label.position.x - halfW - 0.4);
    maxX = Math.max(maxX, label.position.x + halfW + 0.4);
    minY = Math.min(minY, label.position.y - halfH - 0.4);
    maxY = Math.max(maxY, label.position.y + halfH + 0.4);
  }

  return {
    x: minX,
    y: -maxY,
    width: maxX - minX,
    height: maxY - minY,
  };
}

function isDiodeCenterBridgePolyline(
  family: Family,
  poly: { points: Array<{ x: number; y: number }> },
): boolean {
  if (family !== 'diode' && family !== 'led') return false;
  if (poly.points.length !== 2) return false;
  const [a, b] = poly.points;
  const horizontal = Math.abs(a.y - b.y) <= 1e-6;
  if (!horizontal) return false;
  if (Math.abs(a.y) > 1e-3 || Math.abs(b.y) > 1e-3) return false;
  const span = Math.abs(a.x - b.x);
  return span > 2.4 && span < 2.7;
}

function pointsNear(
  a: { x: number; y: number },
  b: { x: number; y: number },
  epsilon = 1e-6,
): boolean {
  return Math.abs(a.x - b.x) <= epsilon && Math.abs(a.y - b.y) <= epsilon;
}

function isDiodeBodyTrianglePolyline(
  family: Family,
  poly: { points: Array<{ x: number; y: number }> },
): boolean {
  if (family !== 'diode' && family !== 'led') return false;
  if (poly.points.length < 4) return false;
  const first = poly.points[0];
  const last = poly.points[poly.points.length - 1];
  if (!pointsNear(first, last)) return false;

  const unique: Array<{ x: number; y: number }> = [];
  for (const p of poly.points.slice(0, -1)) {
    if (!unique.some((u) => pointsNear(u, p))) unique.push(p);
  }
  return unique.length === 3;
}

function inferLedFillColor(component: SchematicComponent): string {
  const haystack = [
    component.name,
    component.symbolVariant,
    component.packageCode,
    component.designator,
  ]
    .join(' ')
    .toLowerCase();

  const palette: Array<{ re: RegExp; color: string }> = [
    { re: /\b(infrared|ir)\b/, color: '#b58288' },
    { re: /\b(ultra[\s_-]?violet|uv)\b/, color: '#9f8fca' },
    { re: /\b(warm[\s_-]?white)\b/, color: '#cec0a6' },
    { re: /\b(cold[\s_-]?white)\b/, color: '#b2bfd0' },
    { re: /\b(natural[\s_-]?white)\b/, color: '#c0c6c5' },
    { re: /\bwhite\b/, color: '#b8bfd0' },
    { re: /\bred\b/, color: '#c77b86' },
    { re: /\bgreen\b/, color: '#8fb68a' },
    { re: /\bblue\b/, color: '#87a7ca' },
    { re: /\b(amber|orange)\b/, color: '#c69a72' },
    { re: /\byellow\b/, color: '#c7b784' },
    { re: /\b(violet|purple)\b/, color: '#ad98cf' },
    { re: /\b(magenta|pink)\b/, color: '#c996b7' },
    { re: /\bcyan\b/, color: '#8fbec3' },
    { re: /\blime\b/, color: '#aac690' },
    { re: /\bemerald\b/, color: '#7eb59b' },
  ];
  for (const entry of palette) {
    if (entry.re.test(haystack)) return entry.color;
  }
  return '#c77b86';
}

function normalizeTextRotationUpright(rotationDeg: number): number {
  let rot = ((rotationDeg % 360) + 360) % 360;
  if (rot > 180) rot -= 360;
  if (rot > 90) rot -= 180;
  if (rot <= -90) rot += 180;
  return rot;
}

function buildPreviewModel(
  component: SchematicComponent,
  family: ComponentFamily,
  symbol: KicadSymbol,
  tuning: SymbolTuning,
  rotationDeg: number,
  mirrorX: boolean,
  mirrorY: boolean,
): PreviewModel | null {
  const bodyPolylines: Point[][] = [];
  const bodyFillPolygons: Point[][] = [];
  const bodyCircles: Array<{ center: Point; radius: number }> = [];
  const leads: Array<{ attach: Point; pin: Point; rawPin: Point; number: string; name: string }> = [];
  const renderedPins = family === 'testpoint'
    ? (() => {
      const primaryPin = component.pins.find((pin) => pin.number === '1') ?? component.pins[0];
      return primaryPin ? [primaryPin] : [];
    })()
    : component.pins;

  const gridOffset = getComponentGridAlignmentOffset(component);
  const glyphTransform = getCanonicalGlyphTransform(component, family, symbol, tuning);
  if (!glyphTransform) return null;
  const pinAttachOverrides = getCanonicalPinAttachmentMap(
    component,
    family,
    symbol,
    tuning,
    CUSTOM_SYMBOL_BODY_BASE_Y,
  );
  const bodyCenter: Point = {
    x: tuning.bodyOffsetX,
    y: tuning.bodyOffsetY + CUSTOM_SYMBOL_BODY_BASE_Y,
  };

  const toWorld = (p: Point): Point => {
    const translated = { x: p.x + gridOffset.x, y: p.y + gridOffset.y };
    return applyInstanceTransform(translated, rotationDeg, mirrorX, mirrorY);
  };

  const toWorldBody = (p: Point): Point => {
    return toWorld({ x: p.x, y: p.y + CUSTOM_SYMBOL_BODY_BASE_Y });
  };

  let polarizedNegativeRectIdx = -1;
  if (family === 'capacitor_polarized' && symbol.rectangles.length > 0) {
    let minCenterY = Number.POSITIVE_INFINITY;
    for (let idx = 0; idx < symbol.rectangles.length; idx += 1) {
      const rect = symbol.rectangles[idx];
      const centerY = (rect.startY + rect.endY) * 0.5;
      if (centerY < minCenterY) {
        minCenterY = centerY;
        polarizedNegativeRectIdx = idx;
      }
    }
  }

  for (let idx = 0; idx < symbol.rectangles.length; idx += 1) {
    const rect = symbol.rectangles[idx];
    const rectPoints = [
      toWorldBody(transformCanonicalBodyPoint(rect.startX, rect.startY, glyphTransform)),
      toWorldBody(transformCanonicalBodyPoint(rect.endX, rect.startY, glyphTransform)),
      toWorldBody(transformCanonicalBodyPoint(rect.endX, rect.endY, glyphTransform)),
      toWorldBody(transformCanonicalBodyPoint(rect.startX, rect.endY, glyphTransform)),
      toWorldBody(transformCanonicalBodyPoint(rect.startX, rect.startY, glyphTransform)),
    ];
    bodyPolylines.push(rectPoints);
    if (idx === polarizedNegativeRectIdx) {
      bodyFillPolygons.push(rectPoints.slice(0, 4));
    }
  }

  for (const poly of symbol.polylines) {
    if (isDiodeCenterBridgePolyline(family, poly)) continue;
    const worldPoints = poly.points.map((p) =>
      toWorldBody(transformCanonicalBodyPoint(p.x, p.y, glyphTransform)));
    bodyPolylines.push(worldPoints);
    if (isDiodeBodyTrianglePolyline(family, poly) && worldPoints.length >= 4) {
      bodyFillPolygons.push(worldPoints.slice(0, -1));
    }
  }

  for (const arc of symbol.arcs) {
    bodyPolylines.push(
      kicadArcPoints(arc, 22).map((p) =>
        toWorldBody(transformCanonicalBodyPoint(p.x, p.y, glyphTransform)),
      ),
    );
  }

  for (const circle of symbol.circles) {
    const center = toWorldBody(
      transformCanonicalBodyPoint(circle.centerX, circle.centerY, glyphTransform),
    );
    bodyCircles.push({ center, radius: circle.radius * glyphTransform.unit });
  }

  for (const pin of renderedPins) {
    const tuned = getTunedPinGeometry(
      component,
      pin,
      family,
      pinAttachOverrides.get(pin.number),
      tuning,
      bodyCenter,
    );
    const rawPin = toWorld({ x: pin.x, y: pin.y });
    const attach = toWorld({ x: tuned.bodyX, y: tuned.bodyY });
    const pinPoint = toWorld({ x: tuned.x, y: tuned.y });
    leads.push({
      attach,
      pin: pinPoint,
      rawPin,
      number: pin.number,
      name: pin.name,
    });
  }

  const allPoints: Point[] = [];
  for (const poly of bodyPolylines) allPoints.push(...poly);
  for (const circle of bodyCircles) {
    allPoints.push(
      { x: circle.center.x - circle.radius, y: circle.center.y },
      { x: circle.center.x + circle.radius, y: circle.center.y },
      { x: circle.center.x, y: circle.center.y - circle.radius },
      { x: circle.center.x, y: circle.center.y + circle.radius },
    );
  }
  for (const lead of leads) {
    allPoints.push(lead.attach, lead.pin, lead.rawPin);
  }

  const bounds = pointsToBounds(allPoints);
  const pad = 2.8;
  const minX = bounds.minX - pad;
  const maxX = bounds.maxX + pad;
  const minY = bounds.minY - pad;
  const maxY = bounds.maxY + pad;

  const center = toWorld({ x: 0, y: 0 });
  const crossSize = 0.5;
  const centerCross = {
    h0: { x: center.x - crossSize, y: center.y },
    h1: { x: center.x + crossSize, y: center.y },
    v0: { x: center.x, y: center.y - crossSize },
    v1: { x: center.x, y: center.y + crossSize },
  };

  return {
    bodyPolylines,
    bodyFillPolygons,
    bodyCircles,
    leads,
    centerCross,
    gridOffset,
    viewBox: {
      x: minX,
      y: -maxY,
      width: maxX - minX,
      height: maxY - minY,
    },
  };
}

function transformPowerBodyPoint(point: Point, tuning: SymbolTuning): Point {
  const sx = clamp(tuning.bodyScaleX ?? 1, 0.1, 4);
  const sy = clamp(tuning.bodyScaleY ?? 1, 0.1, 4);
  const xScaled = point.x * sx;
  const yScaled = point.y * sy;
  const angle = (tuning.bodyRotationDeg * Math.PI) / 180;
  const cosA = Math.cos(angle);
  const sinA = Math.sin(angle);
  return {
    x: xScaled * cosA - yScaled * sinA + tuning.bodyOffsetX,
    y: xScaled * sinA + yScaled * cosA + tuning.bodyOffsetY,
  };
}

function buildPowerPreviewModel(
  family: PowerFamily,
  component: SchematicComponent,
  tuning: SymbolTuning,
  rotationDeg: number,
  mirrorX: boolean,
  mirrorY: boolean,
): PreviewModel {
  const bodyPolylines: Point[][] = [];
  const bodyFillPolygons: Point[][] = [];
  const bodyCircles: Array<{ center: Point; radius: number }> = [];
  const leads: Array<{ attach: Point; pin: Point; rawPin: Point; number: string; name: string }> = [];
  const gridOffset = getComponentGridAlignmentOffset(component);

  const toWorld = (p: Point): Point => {
    const translated = { x: p.x + gridOffset.x, y: p.y + gridOffset.y };
    return applyInstanceTransform(translated, rotationDeg, mirrorX, mirrorY);
  };

  const BAR_HALF = POWER_PORT_W / 2;
  if (family === 'vcc') {
    bodyPolylines.push(
      [
        { x: -BAR_HALF, y: 0.4 },
        { x: BAR_HALF, y: 0.4 },
      ].map((p) => toWorld(transformPowerBodyPoint(p, tuning))),
    );

    const attach = toWorld(transformPowerBodyPoint({ x: 0, y: 0.4 }, tuning));
    const pin = toWorld(transformPowerBodyPoint({ x: 0, y: -0.6 }, tuning));
    leads.push({
      attach,
      pin,
      rawPin: pin,
      number: '1',
      name: '',
    });
  } else {
    const WIDTHS = [BAR_HALF, BAR_HALF * 0.6, BAR_HALF * 0.25];
    const GAP = 0.4;
    for (let i = 0; i < WIDTHS.length; i += 1) {
      const halfW = WIDTHS[i];
      const y = -0.1 - i * GAP;
      bodyPolylines.push(
        [
          { x: -halfW, y },
          { x: halfW, y },
        ].map((p) => toWorld(transformPowerBodyPoint(p, tuning))),
      );
    }

    const attach = toWorld(transformPowerBodyPoint({ x: 0, y: -0.1 }, tuning));
    const pin = toWorld(transformPowerBodyPoint({ x: 0, y: 0.6 }, tuning));
    leads.push({
      attach,
      pin,
      rawPin: pin,
      number: '1',
      name: '',
    });
  }

  const allPoints: Point[] = [];
  for (const poly of bodyPolylines) allPoints.push(...poly);
  for (const lead of leads) allPoints.push(lead.attach, lead.pin, lead.rawPin);
  const bounds = pointsToBounds(allPoints);
  const pad = 2.8;
  const minX = bounds.minX - pad;
  const maxX = bounds.maxX + pad;
  const minY = bounds.minY - pad;
  const maxY = bounds.maxY + pad;

  const center = toWorld({ x: 0, y: 0 });
  const crossSize = 0.5;
  const centerCross = {
    h0: { x: center.x - crossSize, y: center.y },
    h1: { x: center.x + crossSize, y: center.y },
    v0: { x: center.x, y: center.y - crossSize },
    v1: { x: center.x, y: center.y + crossSize },
  };

  return {
    bodyPolylines,
    bodyFillPolygons,
    bodyCircles,
    leads,
    centerCross,
    gridOffset,
    viewBox: {
      x: minX,
      y: -maxY,
      width: maxX - minX,
      height: maxY - minY,
    },
  };
}

function fmt(n: number): string {
  return n.toFixed(2);
}

function pt(p: Point): string {
  return `${p.x.toFixed(3)},${(-p.y).toFixed(3)}`;
}

function SliderField({
  label,
  value,
  min,
  max,
  step,
  onChange,
  onSetAll,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (next: number) => void;
  onSetAll?: () => void;
}) {
  return (
    <label className="symbol-tuner-field">
      <div className="symbol-tuner-field-row">
        <span className="symbol-tuner-label">{label}</span>
        <div className="symbol-tuner-field-controls">
          {onSetAll && (
            <button
              type="button"
              className="symbol-tuner-set-all-btn"
              onClick={(event) => {
                event.preventDefault();
                onSetAll();
              }}
            >
              Set All
            </button>
          )}
          <input
            type="number"
            className="symbol-tuner-number"
            value={value}
            min={min}
            max={max}
            step={step}
            onChange={(event) => {
              const next = Number.parseFloat(event.target.value);
              if (!Number.isFinite(next)) return;
              onChange(clamp(next, min, max));
            }}
          />
        </div>
      </div>
      <input
        type="range"
        className="symbol-tuner-slider"
        value={value}
        min={min}
        max={max}
        step={step}
        onChange={(event) => {
          const next = Number.parseFloat(event.target.value);
          if (!Number.isFinite(next)) return;
          onChange(next);
        }}
      />
    </label>
  );
}

export function SymbolTunerApp() {
  const [family, setFamily] = useState<Family>('resistor');
  const [tunings, setTunings] = useState<Record<Family, SymbolTuning>>(initialTunings);
  const [visualTunings, setVisualTunings] = useState<Record<Family, VisualTuning>>(initialVisualTunings);
  const [copyState, setCopyState] = useState<'idle' | 'done' | 'error'>('idle');
  const [instanceRotation, setInstanceRotation] = useState<number>(0);
  const [mirrorX, setMirrorX] = useState(false);
  const [mirrorY, setMirrorY] = useState(false);
  const [showDebugOverlays, setShowDebugOverlays] = useState(false);
  const [selectedLabel, setSelectedLabel] = useState<'designator' | 'value' | 'package' | null>('designator');
  const [dragState, setDragState] = useState<DragState | null>(null);
  const svgRef = useRef<SVGSVGElement | null>(null);
  const isPowerSymbol = isPowerFamily(family);
  const valuePreviewText = isPowerSymbol ? '' : '100nF';
  const textTf = useMemo(
    () => getUprightTextTransform(instanceRotation, mirrorX, mirrorY),
    [instanceRotation, mirrorX, mirrorY],
  );
  const textTfRotationDeg = useMemo(
    () => (-textTf.rotationZ * 180) / Math.PI,
    [textTf.rotationZ],
  );

  useEffect(() => {
    if (typeof window === 'undefined') return;
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(tunings));
  }, [tunings]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    window.localStorage.setItem(VISUAL_STORAGE_KEY, JSON.stringify(visualTunings));
  }, [visualTunings]);

  const tuning = tunings[family];
  const visualTuning = visualTunings[family];
  const fixture = useMemo(() => FIXTURE_BY_FAMILY[family], [family]);
  const symbol = useMemo(
    () => (
      isComponentFamily(family)
        ? getCanonicalKicadSymbol(family, PIN_COUNT_BY_FAMILY[family])
        : null
    ),
    [family],
  );
  const preview = useMemo(
    () => {
      if (isPowerFamily(family)) {
        return buildPowerPreviewModel(
          family,
          fixture,
          tuning,
          instanceRotation,
          mirrorX,
          mirrorY,
        );
      }
      if (!symbol) return null;
      return buildPreviewModel(
        fixture,
        family,
        symbol,
        tuning,
        instanceRotation,
        mirrorX,
        mirrorY,
      );
    },
    [symbol, fixture, family, tuning, instanceRotation, mirrorX, mirrorY],
  );

  useEffect(() => {
    if (!isPowerSymbol) return;
    if (selectedLabel === 'designator') return;
    setSelectedLabel('designator');
  }, [isPowerSymbol, selectedLabel]);

  const designatorWorld = useMemo(
    () => (
      preview
        ? labelPositionToWorld(
          { x: visualTuning.designator.offsetX, y: visualTuning.designator.offsetY },
          preview,
          instanceRotation,
          mirrorX,
          mirrorY,
        )
        : null
    ),
    [preview, visualTuning.designator, instanceRotation, mirrorX, mirrorY],
  );

  const valueWorld = useMemo(
    () => (
      preview
        ? labelPositionToWorld(
          { x: visualTuning.value.offsetX, y: visualTuning.value.offsetY },
          preview,
          instanceRotation,
          mirrorX,
          mirrorY,
        )
        : null
    ),
    [preview, visualTuning.value, instanceRotation, mirrorX, mirrorY],
  );

  const packageWorld = useMemo(
    () => (
      preview
        ? labelPositionToWorld(
          { x: visualTuning.package.offsetX, y: visualTuning.package.offsetY },
          preview,
          instanceRotation,
          mirrorX,
          mirrorY,
        )
        : null
    ),
    [preview, visualTuning.package, instanceRotation, mirrorX, mirrorY],
  );

  const packageLabelRotationDeg = useMemo(() => {
    const raw = visualTuning.package.rotationDeg
      + (visualTuning.package.followInstanceRotation ? instanceRotation : 0);
    if (!visualTuning.package.followInstanceRotation) return raw;
    return normalizeTextRotationUpright(raw);
  }, [visualTuning.package, instanceRotation]);

  const previewViewBox = useMemo(() => {
    if (!preview || !designatorWorld) return preview?.viewBox ?? null;
    const labels: Array<{ position: Point; text: string; fontSize: number }> = [
      {
        position: designatorWorld,
        text: fixture.designator,
        fontSize: visualTuning.designator.fontSize,
      },
    ];
    if (!isPowerSymbol && valueWorld) {
      labels.push({
        position: valueWorld,
        text: valuePreviewText,
        fontSize: visualTuning.value.fontSize,
      });
    }
    if (!isPowerSymbol && packageWorld && fixture.packageCode) {
      labels.push({
        position: packageWorld,
        text: fixture.packageCode,
        fontSize: visualTuning.package.fontSize,
      });
    }
    return expandViewBoxWithLabels(preview.viewBox, labels);
  }, [
    preview,
    designatorWorld,
    valueWorld,
    packageWorld,
    isPowerSymbol,
    fixture.designator,
    fixture.packageCode,
    valuePreviewText,
    visualTuning.designator.fontSize,
    visualTuning.value.fontSize,
    visualTuning.package.fontSize,
  ]);

  const tuningJson = useMemo(
    () => JSON.stringify(tunings, null, 2),
    [tunings],
  );
  const visualTuningJson = useMemo(
    () => JSON.stringify(visualTunings, null, 2),
    [visualTunings],
  );

  const setTuning = (partial: Partial<SymbolTuning>) => {
    setTunings((prev) => ({
      ...prev,
      [family]: {
        ...prev[family],
        ...partial,
      },
    }));
  };

  const setVisualTuning = (partial: Partial<VisualTuning>) => {
    setVisualTunings((prev) => ({
      ...prev,
      [family]: {
        ...prev[family],
        ...partial,
      },
    }));
  };

  const setLabelTuning = (
    target: 'designator' | 'value' | 'package',
    partial: Partial<LabelTuning>,
  ) => {
    setVisualTunings((prev) => ({
      ...prev,
      [family]: {
        ...prev[family],
        [target]: {
          ...prev[family][target],
          ...partial,
        },
      },
    }));
  };

  const applyVisualFieldToAll = (
    key: 'symbolStrokeWidth' | 'leadStrokeWidth' | 'connectionDotRadius',
    value: number,
  ) => {
    setVisualTunings((prev) => {
      const out = { ...prev };
      for (const f of FAMILIES) {
        out[f] = {
          ...out[f],
          [key]: value,
        };
      }
      return out;
    });
  };

  const resetFamily = () => {
    setTunings((prev) => ({
      ...prev,
      [family]: { ...DEFAULT_TUNINGS[family] },
    }));
    setVisualTunings((prev) => ({
      ...prev,
      [family]: { ...DEFAULT_VISUAL_TUNINGS[family] },
    }));
  };

  const resetAll = () => {
    setTunings({ ...DEFAULT_TUNINGS });
    setVisualTunings({ ...DEFAULT_VISUAL_TUNINGS });
  };

  const copyJson = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopyState('done');
      window.setTimeout(() => setCopyState('idle'), 1400);
    } catch {
      setCopyState('error');
      window.setTimeout(() => setCopyState('idle'), 1800);
    }
  };

  const startLabelDrag = (
    event: ReactPointerEvent<SVGTextElement>,
    target: 'designator' | 'value' | 'package',
  ) => {
    event.preventDefault();
    event.stopPropagation();
    setSelectedLabel(target);
    const current = visualTuning[target];
    setDragState({
      target,
      pointerId: event.pointerId,
      startClientX: event.clientX,
      startClientY: event.clientY,
      startOffsetX: current.offsetX,
      startOffsetY: current.offsetY,
    });
  };

  useEffect(() => {
    if (!dragState || !previewViewBox) return;

    const onPointerMove = (event: PointerEvent) => {
      if (event.pointerId !== dragState.pointerId) return;
      const svg = svgRef.current;
      if (!svg) return;
      const rect = svg.getBoundingClientRect();
      if (rect.width <= 0 || rect.height <= 0) return;

      const dxPx = event.clientX - dragState.startClientX;
      const dyPx = event.clientY - dragState.startClientY;
      const dxWorld = dxPx * (previewViewBox.width / rect.width);
      const dyWorld = -dyPx * (previewViewBox.height / rect.height);
      const localDelta = applyInverseInstanceTransform(
        { x: dxWorld, y: dyWorld },
        instanceRotation,
        mirrorX,
        mirrorY,
      );
      setLabelTuning(dragState.target, {
        offsetX: clamp(dragState.startOffsetX + localDelta.x, -24, 24),
        offsetY: clamp(dragState.startOffsetY + localDelta.y, -24, 24),
      });
    };

    const onPointerEnd = (event: PointerEvent) => {
      if (event.pointerId !== dragState.pointerId) return;
      setDragState(null);
    };

    window.addEventListener('pointermove', onPointerMove);
    window.addEventListener('pointerup', onPointerEnd);
    window.addEventListener('pointercancel', onPointerEnd);
    return () => {
      window.removeEventListener('pointermove', onPointerMove);
      window.removeEventListener('pointerup', onPointerEnd);
      window.removeEventListener('pointercancel', onPointerEnd);
    };
  }, [
    dragState,
    previewViewBox,
    instanceRotation,
    mirrorX,
    mirrorY,
  ]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key.toLowerCase() !== 'r') return;
      if (event.metaKey || event.ctrlKey || event.altKey) return;
      if (!selectedLabel) return;
      const active = document.activeElement;
      if (
        active
        && (active.tagName === 'INPUT' || active.tagName === 'SELECT' || active.tagName === 'TEXTAREA')
      ) {
        return;
      }
      event.preventDefault();
      const delta = event.shiftKey ? -90 : 90;
      const current = visualTuning[selectedLabel].rotationDeg;
      const next = ((current + delta + 540) % 360) - 180;
      setLabelTuning(selectedLabel, { rotationDeg: next });
    };

    window.addEventListener('keydown', onKeyDown);
    return () => {
      window.removeEventListener('keydown', onKeyDown);
    };
  }, [selectedLabel, visualTuning, family]);

  return (
    <div className="symbol-tuner-root">
      <aside className="symbol-tuner-controls">
        <h1>Symbol Tuner</h1>
        <p className="symbol-tuner-subtitle">
          Uses the exact canvas pipeline: canonical glyph transform, pin-grid normalization, lead tuning, and
          instance rotation/mirroring.
        </p>
        <p className="symbol-tuner-hint">
          Defaults mirror runtime code. Append <code>?restore=1</code> to reload previously saved local tuning edits.
        </p>

        <label className="symbol-tuner-field">
          <span className="symbol-tuner-label">Symbol Type</span>
          <select
            className="symbol-tuner-select"
            value={family}
            onChange={(event) => setFamily(event.target.value as Family)}
          >
            {FAMILIES.map((candidate) => (
              <option key={candidate} value={candidate}>
                {candidate}
              </option>
            ))}
          </select>
        </label>

        <label className="symbol-tuner-field">
          <span className="symbol-tuner-label">Instance Rotation</span>
          <select
            className="symbol-tuner-select"
            value={instanceRotation}
            onChange={(event) => setInstanceRotation(Number.parseInt(event.target.value, 10))}
          >
            <option value={0}>0 deg</option>
            <option value={90}>90 deg</option>
            <option value={180}>180 deg</option>
            <option value={270}>270 deg</option>
          </select>
        </label>

        <div className="symbol-tuner-row">
          <label className="symbol-tuner-check">
            <input
              type="checkbox"
              checked={mirrorX}
              onChange={(event) => setMirrorX(event.target.checked)}
            />
            <span>Mirror X</span>
          </label>
          <label className="symbol-tuner-check">
            <input
              type="checkbox"
              checked={mirrorY}
              onChange={(event) => setMirrorY(event.target.checked)}
            />
            <span>Mirror Y</span>
          </label>
        </div>

        <label className="symbol-tuner-check symbol-tuner-check-block">
          <input
            type="checkbox"
            checked={showDebugOverlays}
            onChange={(event) => setShowDebugOverlays(event.target.checked)}
          />
          <span>Show Debug Overlays</span>
        </label>

        <SliderField
          label="Move Body X"
          value={tuning.bodyOffsetX}
          min={-6}
          max={6}
          step={0.05}
          onChange={(next) => setTuning({ bodyOffsetX: next })}
        />

        <SliderField
          label="Move Body Y"
          value={tuning.bodyOffsetY}
          min={-6}
          max={6}
          step={0.05}
          onChange={(next) => setTuning({ bodyOffsetY: next })}
        />

        <SliderField
          label="Rotate Body (deg)"
          value={tuning.bodyRotationDeg}
          min={-180}
          max={180}
          step={1}
          onChange={(next) => setTuning({ bodyRotationDeg: next })}
        />

        <SliderField
          label="Scale Body X"
          value={tuning.bodyScaleX ?? 1}
          min={0.2}
          max={2.5}
          step={0.01}
          onChange={(next) => setTuning({ bodyScaleX: next })}
        />

        <SliderField
          label="Scale Body Y"
          value={tuning.bodyScaleY ?? 1}
          min={0.2}
          max={2.5}
          step={0.01}
          onChange={(next) => setTuning({ bodyScaleY: next })}
        />

        {!isPowerSymbol && (
          <SliderField
            label="Lead Length Delta"
            value={tuning.leadDelta}
            min={-6}
            max={6}
            step={0.05}
            onChange={(next) => setTuning({ leadDelta: next })}
          />
        )}

        <div className="symbol-tuner-section-title">Text Placement</div>
        <p className="symbol-tuner-hint">Click a label and press <code>R</code> to rotate (+90 deg). <code>Shift+R</code> rotates the other way.</p>

        <SliderField
          label={isPowerSymbol ? 'Label X' : 'Designator X'}
          value={visualTuning.designator.offsetX}
          min={-12}
          max={12}
          step={0.05}
          onChange={(next) => setLabelTuning('designator', { offsetX: next })}
        />

        <SliderField
          label={isPowerSymbol ? 'Label Y' : 'Designator Y'}
          value={visualTuning.designator.offsetY}
          min={-12}
          max={12}
          step={0.05}
          onChange={(next) => setLabelTuning('designator', { offsetY: next })}
        />

        <SliderField
          label={isPowerSymbol ? 'Label Size' : 'Designator Size'}
          value={visualTuning.designator.fontSize}
          min={0.3}
          max={2.5}
          step={0.01}
          onChange={(next) => setLabelTuning('designator', { fontSize: next })}
        />

        <SliderField
          label={isPowerSymbol ? 'Label Rotation' : 'Designator Rotation'}
          value={visualTuning.designator.rotationDeg}
          min={-180}
          max={180}
          step={1}
          onChange={(next) => setLabelTuning('designator', { rotationDeg: next })}
        />

        {!isPowerSymbol && (
          <>
            <SliderField
              label="Value X"
              value={visualTuning.value.offsetX}
              min={-12}
              max={12}
              step={0.05}
              onChange={(next) => setLabelTuning('value', { offsetX: next })}
            />

            <SliderField
              label="Value Y"
              value={visualTuning.value.offsetY}
              min={-12}
              max={12}
              step={0.05}
              onChange={(next) => setLabelTuning('value', { offsetY: next })}
            />

            <SliderField
              label="Value Size"
              value={visualTuning.value.fontSize}
              min={0.3}
              max={2.5}
              step={0.01}
              onChange={(next) => setLabelTuning('value', { fontSize: next })}
            />

            <SliderField
              label="Value Rotation"
              value={visualTuning.value.rotationDeg}
              min={-180}
              max={180}
              step={1}
              onChange={(next) => setLabelTuning('value', { rotationDeg: next })}
            />

            <SliderField
              label="Package X"
              value={visualTuning.package.offsetX}
              min={-12}
              max={12}
              step={0.05}
              onChange={(next) => setLabelTuning('package', { offsetX: next })}
            />

            <SliderField
              label="Package Y"
              value={visualTuning.package.offsetY}
              min={-12}
              max={12}
              step={0.05}
              onChange={(next) => setLabelTuning('package', { offsetY: next })}
            />

            <SliderField
              label="Package Size"
              value={visualTuning.package.fontSize}
              min={0.3}
              max={2.5}
              step={0.01}
              onChange={(next) => setLabelTuning('package', { fontSize: next })}
            />

            <SliderField
              label="Package Rotation"
              value={visualTuning.package.rotationDeg}
              min={-180}
              max={180}
              step={1}
              onChange={(next) => setLabelTuning('package', { rotationDeg: next })}
            />

            <label className="symbol-tuner-check symbol-tuner-check-block">
              <input
                type="checkbox"
                checked={visualTuning.package.followInstanceRotation}
                onChange={(event) => setVisualTuning({
                  package: {
                    ...visualTuning.package,
                    followInstanceRotation: event.target.checked,
                  },
                })}
              />
              <span>Package follows component rotation</span>
            </label>
          </>
        )}

        <div className="symbol-tuner-section-title">Stroke Thickness</div>

        <SliderField
          label="Body Stroke"
          value={visualTuning.symbolStrokeWidth}
          min={0.08}
          max={1.2}
          step={0.01}
          onChange={(next) => setVisualTuning({ symbolStrokeWidth: next })}
          onSetAll={() => applyVisualFieldToAll('symbolStrokeWidth', visualTuning.symbolStrokeWidth)}
        />

        <SliderField
          label="Lead Stroke"
          value={visualTuning.leadStrokeWidth}
          min={0.08}
          max={1.2}
          step={0.01}
          onChange={(next) => setVisualTuning({ leadStrokeWidth: next })}
          onSetAll={() => applyVisualFieldToAll('leadStrokeWidth', visualTuning.leadStrokeWidth)}
        />

        <SliderField
          label="Connection Dot Radius"
          value={visualTuning.connectionDotRadius}
          min={0.05}
          max={0.8}
          step={0.01}
          onChange={(next) => setVisualTuning({ connectionDotRadius: next })}
          onSetAll={() => applyVisualFieldToAll('connectionDotRadius', visualTuning.connectionDotRadius)}
        />

        <div className="symbol-tuner-actions">
          <button type="button" onClick={resetFamily}>
            Reset Family
          </button>
          <button type="button" onClick={resetAll}>
            Reset All
          </button>
          <button type="button" onClick={() => void copyJson(tuningJson)}>
            Copy Geometry JSON
          </button>
          <button type="button" onClick={() => void copyJson(visualTuningJson)}>
            Copy Visual JSON
          </button>
        </div>

        <div className="symbol-tuner-copy-state">
          {copyState === 'done' && 'Copied JSON'}
          {copyState === 'error' && 'Clipboard copy failed'}
        </div>

        <details className="symbol-tuner-json">
          <summary>Geometry JSON</summary>
          <pre>{tuningJson}</pre>
        </details>
        <details className="symbol-tuner-json">
          <summary>Visual JSON</summary>
          <pre>{visualTuningJson}</pre>
        </details>
      </aside>

      <main className="symbol-tuner-preview">
        <div className="symbol-tuner-preview-header">
          <strong>{family}</strong>
          <span>
            offset({fmt(tuning.bodyOffsetX)}, {fmt(tuning.bodyOffsetY)}) | rot {fmt(tuning.bodyRotationDeg)}
            deg | scale({fmt(tuning.bodyScaleX ?? 1)}, {fmt(tuning.bodyScaleY ?? 1)})
            {!isPowerSymbol ? ` | lead ${fmt(tuning.leadDelta)}` : ''}
            | body {fmt(visualTuning.symbolStrokeWidth)} | lead {fmt(visualTuning.leadStrokeWidth)}
            | dot {fmt(visualTuning.connectionDotRadius)}
            | inst {instanceRotation} deg
            {mirrorX ? ' | MX' : ''}
            {mirrorY ? ' | MY' : ''}
            {selectedLabel ? ` | sel ${selectedLabel}` : ''}
          </span>
        </div>

        {!preview && (
          <div className="symbol-tuner-empty">No canonical symbol found.</div>
        )}

        {preview && (
          <svg
            ref={svgRef}
            className="symbol-tuner-svg"
            viewBox={`${previewViewBox?.x ?? preview.viewBox.x} ${previewViewBox?.y ?? preview.viewBox.y} ${previewViewBox?.width ?? preview.viewBox.width} ${previewViewBox?.height ?? preview.viewBox.height}`}
            xmlns="http://www.w3.org/2000/svg"
          >
            <defs>
              <pattern id="symbol-tuner-grid" width="2.54" height="2.54" patternUnits="userSpaceOnUse">
                <path d="M 2.54 0 L 0 0 0 2.54" fill="none" stroke="#e4e7ed" strokeWidth="0.03" />
              </pattern>
            </defs>
            <rect
              x={previewViewBox?.x ?? preview.viewBox.x}
              y={previewViewBox?.y ?? preview.viewBox.y}
              width={previewViewBox?.width ?? preview.viewBox.width}
              height={previewViewBox?.height ?? preview.viewBox.height}
              fill="url(#symbol-tuner-grid)"
            />

            {preview.leads.map((lead) => (
              <line
                key={`lead-${lead.number}`}
                x1={lead.attach.x}
                y1={-lead.attach.y}
                x2={lead.pin.x}
                y2={-lead.pin.y}
                stroke="#6b7280"
                strokeWidth={visualTuning.leadStrokeWidth}
                strokeLinecap="round"
              />
            ))}

            {preview.bodyFillPolygons.map((poly, idx) => (
              <polygon
                key={`fill-${idx}`}
                points={poly.map((p) => pt(p)).join(' ')}
                fill={family === 'led' ? inferLedFillColor(fixture) : '#374151'}
                fillOpacity={
                  family === 'led'
                    ? 0.42
                    : family === 'capacitor_polarized'
                      ? 0.72
                      : 0.28
                }
              />
            ))}

            {preview.bodyPolylines.map((poly, idx) => (
              <polyline
                key={`poly-${idx}`}
                points={poly.map((p) => pt(p)).join(' ')}
                fill="none"
                stroke="#374151"
                strokeWidth={visualTuning.symbolStrokeWidth}
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            ))}

            {preview.bodyCircles.map((circle, idx) => (
              <circle
                key={`circle-${idx}`}
                cx={circle.center.x}
                cy={-circle.center.y}
                r={circle.radius}
                fill="none"
                stroke="#374151"
                strokeWidth={visualTuning.symbolStrokeWidth}
              />
            ))}

            {!isPowerSymbol && showDebugOverlays && preview.leads.map((lead) => (
              <circle
                key={`raw-${lead.number}`}
                cx={lead.rawPin.x}
                cy={-lead.rawPin.y}
                r={0.12}
                fill="#f97316"
              />
            ))}

            {preview.leads.map((lead) => (
              <circle
                key={`pin-${lead.number}`}
                cx={lead.pin.x}
                cy={-lead.pin.y}
                r={visualTuning.connectionDotRadius}
                fill="#4b5563"
              />
            ))}

            {designatorWorld && (
              <g transform={`translate(${designatorWorld.x} ${-designatorWorld.y})`}>
                <g transform={`rotate(${textTfRotationDeg})`}>
                  <g transform={`scale(${textTf.scaleX} ${textTf.scaleY})`}>
                    <g transform={`rotate(${visualTuning.designator.rotationDeg})`}>
                      <text
                        className={`symbol-tuner-label-text ${selectedLabel === 'designator' ? 'is-selected' : ''} ${dragState?.target === 'designator' ? 'is-dragging' : ''}`}
                        x={0}
                        y={0}
                        fontSize={visualTuning.designator.fontSize}
                        fill="#334155"
                        textAnchor="middle"
                        dominantBaseline="middle"
                        onPointerDown={(event) => startLabelDrag(event, 'designator')}
                      >
                        {fixture.designator}
                      </text>
                    </g>
                  </g>
                </g>
              </g>
            )}

            {!isPowerSymbol && valueWorld && (
              <g transform={`translate(${valueWorld.x} ${-valueWorld.y})`}>
                <g transform={`rotate(${textTfRotationDeg})`}>
                  <g transform={`scale(${textTf.scaleX} ${textTf.scaleY})`}>
                    <g transform={`rotate(${visualTuning.value.rotationDeg})`}>
                      <text
                        className={`symbol-tuner-label-text ${selectedLabel === 'value' ? 'is-selected' : ''} ${dragState?.target === 'value' ? 'is-dragging' : ''}`}
                        x={0}
                        y={0}
                        fontSize={visualTuning.value.fontSize}
                        fill="#475569"
                        textAnchor="middle"
                        dominantBaseline="middle"
                        onPointerDown={(event) => startLabelDrag(event, 'value')}
                      >
                        {valuePreviewText}
                      </text>
                    </g>
                  </g>
                </g>
              </g>
            )}

            {!isPowerSymbol && packageWorld && fixture.packageCode && (
              <g transform={`translate(${packageWorld.x} ${-packageWorld.y})`}>
                <g transform={`rotate(${textTfRotationDeg})`}>
                  <g transform={`scale(${textTf.scaleX} ${textTf.scaleY})`}>
                    <g transform={`rotate(${packageLabelRotationDeg})`}>
                      <text
                        className={`symbol-tuner-label-text ${selectedLabel === 'package' ? 'is-selected' : ''} ${dragState?.target === 'package' ? 'is-dragging' : ''}`}
                        x={0}
                        y={0}
                        fontSize={visualTuning.package.fontSize}
                        fill="#64748b"
                        textAnchor="middle"
                        dominantBaseline="middle"
                        onPointerDown={(event) => startLabelDrag(event, 'package')}
                      >
                        {fixture.packageCode}
                      </text>
                    </g>
                  </g>
                </g>
              </g>
            )}


            {!isPowerSymbol && showDebugOverlays && preview.leads.map((lead) => (
              <text
                key={`pin-label-${lead.number}`}
                x={lead.pin.x + 0.18}
                y={-lead.pin.y - 0.18}
                fontSize="0.58"
                fill="#64748b"
              >
                {lead.name}
              </text>
            ))}

            {showDebugOverlays && (
              <>
                <line
                  x1={preview.centerCross.h0.x}
                  y1={-preview.centerCross.h0.y}
                  x2={preview.centerCross.h1.x}
                  y2={-preview.centerCross.h1.y}
                  stroke="#9ca3af"
                  strokeWidth="0.1"
                  strokeDasharray="0.35 0.25"
                />
                <line
                  x1={preview.centerCross.v0.x}
                  y1={-preview.centerCross.v0.y}
                  x2={preview.centerCross.v1.x}
                  y2={-preview.centerCross.v1.y}
                  stroke="#9ca3af"
                  strokeWidth="0.1"
                  strokeDasharray="0.35 0.25"
                />
                <text
                  x={preview.centerCross.h1.x + 0.2}
                  y={-preview.centerCross.h1.y - 0.2}
                  fontSize="0.58"
                  fill="#64748b"
                >
                  gridOffset ({fmt(preview.gridOffset.x)}, {fmt(preview.gridOffset.y)})
                </text>
              </>
            )}
          </svg>
        )}
      </main>
    </div>
  );
}
