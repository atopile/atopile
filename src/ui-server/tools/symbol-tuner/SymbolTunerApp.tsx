import { useEffect, useMemo, useState } from 'react';
import { getCanonicalKicadSymbol } from '../../src/schematic-viewer/symbol-catalog/canonicalSymbolCatalog';
import {
  SYMBOL_RENDER_TUNING,
  type SymbolRenderTuning,
} from '../../src/schematic-viewer/symbol-catalog/symbolTuning';
import type { KicadArc, KicadSymbol } from '../../src/schematic-viewer/types/symbol';
import {
  getComponentGridAlignmentOffset,
  type SchematicComponent,
  type SchematicPin,
  type SchematicSymbolFamily,
  transformPinOffset,
} from '../../src/schematic-viewer/types/schematic';
import {
  CUSTOM_SYMBOL_BODY_BASE_Y,
  getCanonicalGlyphTransform,
  getCanonicalPinAttachmentMap,
  getTunedPinGeometry,
  transformCanonicalBodyPoint,
} from '../../src/schematic-viewer/three/symbolRenderGeometry';

type Family = Exclude<SchematicSymbolFamily, 'connector'>;

type Point = { x: number; y: number };

type SymbolTuning = SymbolRenderTuning;

interface PreviewModel {
  bodyPolylines: Point[][];
  bodyCircles: Array<{ center: Point; radius: number }>;
  leads: Array<{ attach: Point; pin: Point; rawPin: Point; number: string; name: string }>;
  centerCross: { h0: Point; h1: Point; v0: Point; v1: Point };
  viewBox: { x: number; y: number; width: number; height: number };
  gridOffset: Point;
}

const FAMILIES: Family[] = [
  'resistor',
  'capacitor',
  'capacitor_polarized',
  'inductor',
  'diode',
  'led',
  'testpoint',
];

const PIN_COUNT_BY_FAMILY: Record<Family, number> = {
  resistor: 2,
  capacitor: 2,
  capacitor_polarized: 2,
  inductor: 2,
  diode: 2,
  led: 2,
  testpoint: 1,
};

const BASE_TWO_PINS: SchematicPin[] = [
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
    x: 5.08,
    y: 0,
    bodyX: 2.54,
    bodyY: 0,
  },
];

function fixtureComponent(
  family: Family,
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
    bodyWidth: 5.08,
    bodyHeight: 2.04,
  };
}

const FIXTURE_BY_FAMILY: Record<Family, SchematicComponent> = {
  resistor: fixtureComponent('resistor', '0402', 'R1', ['A', 'B']),
  capacitor: fixtureComponent('capacitor', '0603', 'C1', ['VCC', 'GND']),
  capacitor_polarized: fixtureComponent('capacitor_polarized', '1206', 'C2', ['positive', 'negative']),
  inductor: fixtureComponent('inductor', '0805', 'L1', ['A', 'B']),
  diode: fixtureComponent('diode', 'SOD-123', 'D1', ['anode', 'cathode']),
  led: fixtureComponent('led', '0603', 'D2', ['anode', 'cathode']),
  testpoint: {
    kind: 'component',
    id: 'fixture_testpoint',
    name: 'fixture_testpoint',
    designator: 'TP1',
    reference: 'TP',
    symbolFamily: 'testpoint',
    packageCode: 'TESTPOINT',
    pins: [{
      ...BASE_TWO_PINS[0],
      name: 'contact',
    }],
    bodyWidth: 5.08,
    bodyHeight: 2.04,
  },
};

const STORAGE_KEY = 'atopile.symbol_tuner.v1';
const TUNER_SYMBOL_STROKE_WIDTH = 0.26;
const TUNER_LEAD_STROKE_WIDTH = 0.28;

const DEFAULT_TUNINGS: Record<Family, SymbolTuning> = {
  resistor: { ...SYMBOL_RENDER_TUNING.resistor },
  capacitor: { ...SYMBOL_RENDER_TUNING.capacitor },
  capacitor_polarized: { ...SYMBOL_RENDER_TUNING.capacitor_polarized },
  inductor: { ...SYMBOL_RENDER_TUNING.inductor },
  diode: { ...SYMBOL_RENDER_TUNING.diode },
  led: { ...SYMBOL_RENDER_TUNING.led },
  testpoint: { ...SYMBOL_RENDER_TUNING.testpoint },
};

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
        leadDelta: Number.isFinite(item.leadDelta) ? item.leadDelta : 0,
      };
    }
    return out;
  } catch {
    return null;
  }
}

function initialTunings(): Record<Family, SymbolTuning> {
  if (typeof window === 'undefined') return { ...DEFAULT_TUNINGS };
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) return { ...DEFAULT_TUNINGS };
  return parseStoredTunings(raw) ?? { ...DEFAULT_TUNINGS };
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

function buildPreviewModel(
  component: SchematicComponent,
  family: Family,
  symbol: KicadSymbol,
  tuning: SymbolTuning,
  rotationDeg: number,
  mirrorX: boolean,
  mirrorY: boolean,
): PreviewModel | null {
  const bodyPolylines: Point[][] = [];
  const bodyCircles: Array<{ center: Point; radius: number }> = [];
  const leads: Array<{ attach: Point; pin: Point; rawPin: Point; number: string; name: string }> = [];

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

  for (const rect of symbol.rectangles) {
    bodyPolylines.push([
      toWorldBody(transformCanonicalBodyPoint(rect.startX, rect.startY, glyphTransform)),
      toWorldBody(transformCanonicalBodyPoint(rect.endX, rect.startY, glyphTransform)),
      toWorldBody(transformCanonicalBodyPoint(rect.endX, rect.endY, glyphTransform)),
      toWorldBody(transformCanonicalBodyPoint(rect.startX, rect.endY, glyphTransform)),
      toWorldBody(transformCanonicalBodyPoint(rect.startX, rect.startY, glyphTransform)),
    ]);
  }

  for (const poly of symbol.polylines) {
    bodyPolylines.push(
      poly.points.map((p) => toWorldBody(transformCanonicalBodyPoint(p.x, p.y, glyphTransform))),
    );
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

  for (const pin of component.pins) {
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
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (next: number) => void;
}) {
  return (
    <label className="symbol-tuner-field">
      <div className="symbol-tuner-field-row">
        <span className="symbol-tuner-label">{label}</span>
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
  const [copyState, setCopyState] = useState<'idle' | 'done' | 'error'>('idle');
  const [instanceRotation, setInstanceRotation] = useState<number>(0);
  const [mirrorX, setMirrorX] = useState(false);
  const [mirrorY, setMirrorY] = useState(false);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(tunings));
  }, [tunings]);

  const tuning = tunings[family];
  const fixture = useMemo(() => FIXTURE_BY_FAMILY[family], [family]);
  const symbol = useMemo(
    () => getCanonicalKicadSymbol(family, PIN_COUNT_BY_FAMILY[family]),
    [family],
  );
  const preview = useMemo(
    () => (
      symbol
        ? buildPreviewModel(
          fixture,
          family,
          symbol,
          tuning,
          instanceRotation,
          mirrorX,
          mirrorY,
        )
        : null
    ),
    [symbol, fixture, family, tuning, instanceRotation, mirrorX, mirrorY],
  );

  const tuningJson = useMemo(
    () => JSON.stringify(tunings, null, 2),
    [tunings],
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

  const resetFamily = () => {
    setTunings((prev) => ({
      ...prev,
      [family]: { ...DEFAULT_TUNINGS[family] },
    }));
  };

  const resetAll = () => {
    setTunings({ ...DEFAULT_TUNINGS });
  };

  const copyAllTunings = async () => {
    try {
      await navigator.clipboard.writeText(tuningJson);
      setCopyState('done');
      window.setTimeout(() => setCopyState('idle'), 1400);
    } catch {
      setCopyState('error');
      window.setTimeout(() => setCopyState('idle'), 1800);
    }
  };

  return (
    <div className="symbol-tuner-root">
      <aside className="symbol-tuner-controls">
        <h1>Symbol Tuner</h1>
        <p className="symbol-tuner-subtitle">
          Uses the exact canvas pipeline: canonical glyph transform, pin-grid normalization, lead tuning, and
          instance rotation/mirroring.
        </p>

        <label className="symbol-tuner-field">
          <span className="symbol-tuner-label">Component Type</span>
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
          label="Lead Length Delta"
          value={tuning.leadDelta}
          min={-6}
          max={6}
          step={0.05}
          onChange={(next) => setTuning({ leadDelta: next })}
        />

        <div className="symbol-tuner-actions">
          <button type="button" onClick={resetFamily}>
            Reset Family
          </button>
          <button type="button" onClick={resetAll}>
            Reset All
          </button>
          <button type="button" onClick={copyAllTunings}>
            Copy JSON
          </button>
        </div>

        <div className="symbol-tuner-copy-state">
          {copyState === 'done' && 'Copied tuning JSON'}
          {copyState === 'error' && 'Clipboard copy failed'}
        </div>

        <details className="symbol-tuner-json">
          <summary>Tuning JSON</summary>
          <pre>{tuningJson}</pre>
        </details>
      </aside>

      <main className="symbol-tuner-preview">
        <div className="symbol-tuner-preview-header">
          <strong>{family}</strong>
          <span>
            offset({fmt(tuning.bodyOffsetX)}, {fmt(tuning.bodyOffsetY)}) | rot {fmt(tuning.bodyRotationDeg)}
            deg | lead {fmt(tuning.leadDelta)} | inst {instanceRotation} deg
            {mirrorX ? ' | MX' : ''}
            {mirrorY ? ' | MY' : ''}
          </span>
        </div>

        {!preview && (
          <div className="symbol-tuner-empty">No canonical symbol found.</div>
        )}

        {preview && (
          <svg
            className="symbol-tuner-svg"
            viewBox={`${preview.viewBox.x} ${preview.viewBox.y} ${preview.viewBox.width} ${preview.viewBox.height}`}
            xmlns="http://www.w3.org/2000/svg"
          >
            <defs>
              <pattern id="symbol-tuner-grid" width="2.54" height="2.54" patternUnits="userSpaceOnUse">
                <path d="M 2.54 0 L 0 0 0 2.54" fill="none" stroke="#e4e7ed" strokeWidth="0.03" />
              </pattern>
            </defs>
            <rect
              x={preview.viewBox.x}
              y={preview.viewBox.y}
              width={preview.viewBox.width}
              height={preview.viewBox.height}
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
                strokeWidth={TUNER_LEAD_STROKE_WIDTH}
                strokeLinecap="round"
              />
            ))}

            {preview.bodyPolylines.map((poly, idx) => (
              <polyline
                key={`poly-${idx}`}
                points={poly.map((p) => pt(p)).join(' ')}
                fill="none"
                stroke="#374151"
                strokeWidth={TUNER_SYMBOL_STROKE_WIDTH}
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
                strokeWidth={TUNER_SYMBOL_STROKE_WIDTH}
              />
            ))}

            {preview.leads.map((lead) => (
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
                r={0.17}
                fill="#4b5563"
              />
            ))}

            {preview.leads.map((lead) => (
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
          </svg>
        )}
      </main>
    </div>
  );
}
