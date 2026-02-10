/**
 * ComponentRenderer - draws a SchematicComponent body + pins.
 *
 * Wrapped in React.memo for render skipping - only re-renders when
 * selection/hover/drag state actually changes for this component.
 */

import { memo, useMemo } from 'react';
import { Line, RoundedBox, Text } from '@react-three/drei';
import { Shape } from 'three';
import type {
  SchematicComponent,
  SchematicPin,
  SchematicSymbolFamily,
} from '../types/schematic';
import type { KicadArc } from '../types/symbol';
import {
  getComponentGridAlignmentOffset,
} from '../types/schematic';
import type { ThemeColors } from '../lib/theme';
import { getCanonicalKicadSymbol } from '../symbol-catalog/canonicalSymbolCatalog';
import { getSymbolRenderTuning } from '../symbol-catalog/symbolTuning';
import { getKicadTemplateSymbol } from '../parsers/kicadSymbolTemplates';
import { anchorFromVisualSide, getUprightTextTransform } from '../lib/itemTransform';
import { getConnectionColor } from './connectionColor';
import {
  CUSTOM_SYMBOL_BODY_BASE_Y,
  chipScale,
  getCanonicalGlyphTransform,
  getCanonicalPinAttachmentMap,
  getTunedPinGeometry,
  transformCanonicalBodyPoint,
} from './symbolRenderGeometry';

const SMALL_AREA = 40;
const NO_RAYCAST = () => {};
const SYMBOL_STROKE_WIDTH = 0.26;
const SYMBOL_STROKE_WIDTH_FINE = 0.22;
const PIN_LEAD_WIDTH = 0.28;
const PIN_LEAD_WIDTH_ACTIVE = 0.34;
const DIODE_FILL_OPACITY = 0.28;
const LED_FILL_OPACITY = 0.42;
const POLARIZED_CAP_NEGATIVE_PLATE_FILL_OPACITY = 0.72;

function getDesignatorPrefix(designator: string): string {
  return designator.replace(/[^A-Za-z]/g, '').toUpperCase();
}

function inferSymbolFamily(component: SchematicComponent): SchematicSymbolFamily | null {
  // Connectors stay on the generic box renderer for now.
  if (component.symbolFamily === 'connector') return null;
  if (component.symbolFamily) return component.symbolFamily;

  const designatorPrefix = getDesignatorPrefix(component.designator);
  const haystack = [
    component.name,
    designatorPrefix,
    component.reference,
    component.symbolVariant,
    component.packageCode,
  ].join(' ').toLowerCase();

  if (haystack.includes('led')) return 'led';
  if (haystack.includes('testpoint') || designatorPrefix.startsWith('TP')) return 'testpoint';

  if (
    haystack.includes('pmos')
    || haystack.includes('p-mos')
    || haystack.includes('pfet')
    || haystack.includes('p-fet')
    || haystack.includes('pchannel')
    || haystack.includes('p-channel')
  ) {
    return 'mosfet_p';
  }
  if (
    haystack.includes('nmos')
    || haystack.includes('n-mos')
    || haystack.includes('nfet')
    || haystack.includes('n-fet')
    || haystack.includes('nchannel')
    || haystack.includes('n-channel')
  ) {
    return 'mosfet_n';
  }
  if (
    haystack.includes('mosfet')
    || /(^|[^a-z0-9])fet([^a-z0-9]|$)/.test(haystack)
  ) {
    return 'mosfet_n';
  }

  if (haystack.includes('pnp')) return 'transistor_pnp';
  if (haystack.includes('npn')) return 'transistor_npn';
  if (
    designatorPrefix.startsWith('Q')
    || haystack.includes('bjt')
    || haystack.includes('transistor')
  ) {
    return 'transistor_npn';
  }

  if (
    haystack.includes('capacitorpolarized')
    || haystack.includes('capacitor_polarized')
    || haystack.includes('polarized')
    || haystack.includes('electrolytic')
  ) {
    return 'capacitor_polarized';
  }
  if (haystack.includes('capacitor') || designatorPrefix.startsWith('C')) return 'capacitor';
  if (haystack.includes('resistor') || designatorPrefix.startsWith('R')) return 'resistor';
  if (haystack.includes('inductor') || designatorPrefix.startsWith('L')) return 'inductor';
  if (haystack.includes('diode') || designatorPrefix.startsWith('D')) return 'diode';

  return null;
}

function circlePoints(
  cx: number,
  cy: number,
  radius: number,
  segments = 24,
): Array<[number, number, number]> {
  const points: Array<[number, number, number]> = [];
  for (let i = 0; i <= segments; i += 1) {
    const t = (i / segments) * Math.PI * 2;
    points.push([cx + Math.cos(t) * radius, cy + Math.sin(t) * radius, 0]);
  }
  return points;
}

function arcPoints(
  cx: number,
  cy: number,
  radius: number,
  start: number,
  end: number,
  segments = 8,
): Array<[number, number, number]> {
  const points: Array<[number, number, number]> = [];
  for (let i = 0; i <= segments; i += 1) {
    const t = start + ((end - start) * i) / segments;
    points.push([cx + Math.cos(t) * radius, cy + Math.sin(t) * radius, 0]);
  }
  return points;
}

function arcCircleFromThreePoints(
  start: [number, number],
  mid: [number, number],
  end: [number, number],
): { cx: number; cy: number; radius: number } | null {
  const [x1, y1] = start;
  const [x2, y2] = mid;
  const [x3, y3] = end;

  const d = 2 * (
    x1 * (y2 - y3)
    + x2 * (y3 - y1)
    + x3 * (y1 - y2)
  );
  if (Math.abs(d) < 1e-9) return null;

  const ux = (
    (x1 * x1 + y1 * y1) * (y2 - y3)
    + (x2 * x2 + y2 * y2) * (y3 - y1)
    + (x3 * x3 + y3 * y3) * (y1 - y2)
  ) / d;
  const uy = (
    (x1 * x1 + y1 * y1) * (x3 - x2)
    + (x2 * x2 + y2 * y2) * (x1 - x3)
    + (x3 * x3 + y3 * y3) * (x2 - x1)
  ) / d;

  return { cx: ux, cy: uy, radius: Math.hypot(x1 - ux, y1 - uy) };
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

function kicadArcPoints(arc: KicadArc, segments = 20): Array<[number, number]> {
  const start: [number, number] = [arc.startX, arc.startY];
  const mid: [number, number] = [arc.midX, arc.midY];
  const end: [number, number] = [arc.endX, arc.endY];
  const circle = arcCircleFromThreePoints(start, mid, end);
  if (!circle) return [start, mid, end];

  const { cx, cy, radius } = circle;
  const a0 = normalizeAngle(Math.atan2(start[1] - cy, start[0] - cx));
  const am = normalizeAngle(Math.atan2(mid[1] - cy, mid[0] - cx));
  const a1 = normalizeAngle(Math.atan2(end[1] - cy, end[0] - cx));
  const ccw = isAngleOnCCWPath(a0, am, a1);
  const twoPi = Math.PI * 2;
  const span = ccw ? (a1 - a0 + twoPi) % twoPi : (a0 - a1 + twoPi) % twoPi;

  const pts: Array<[number, number]> = [];
  for (let i = 0; i <= segments; i += 1) {
    const t = i / segments;
    const angle = ccw ? a0 + span * t : a0 - span * t;
    pts.push([cx + Math.cos(angle) * radius, cy + Math.sin(angle) * radius]);
  }
  return pts;
}

function isDiodeCenterBridgePolyline(
  family: SchematicSymbolFamily,
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
  family: SchematicSymbolFamily,
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

interface SymbolGlyphProps {
  component: SchematicComponent;
  family: SchematicSymbolFamily;
  color: string;
  templateSymbol: ReturnType<typeof getCanonicalKicadSymbol>;
  tuning: {
    bodyOffsetX: number;
    bodyOffsetY: number;
    bodyRotationDeg: number;
    leadDelta: number;
  };
}

function SymbolGlyph({
  component,
  family,
  color,
  templateSymbol,
  tuning,
}: SymbolGlyphProps) {
  const W = component.bodyWidth;
  const H = component.bodyHeight;
  const scale = chipScale(component.packageCode);
  const lineColor = color;
  const lineWidth = SYMBOL_STROKE_WIDTH;
  if (
    templateSymbol
    && templateSymbol.bodyBounds.width > 1e-6
    && templateSymbol.bodyBounds.height > 1e-6
  ) {
    const transform = getCanonicalGlyphTransform(component, family, templateSymbol, tuning);
    if (!transform) return null;
    const bodyFills: Array<{
      key: string;
      points: Array<[number, number]>;
      color: string;
      opacity: number;
    }> = [];

    if (family === 'diode' || family === 'led') {
      const fillColor = family === 'led' ? inferLedFillColor(component) : lineColor;
      const fillOpacity = family === 'led' ? LED_FILL_OPACITY : DIODE_FILL_OPACITY;
      for (let idx = 0; idx < templateSymbol.polylines.length; idx += 1) {
        const poly = templateSymbol.polylines[idx];
        if (!isDiodeBodyTrianglePolyline(family, poly)) continue;
        const points = poly.points
          .slice(0, -1)
          .map((p) => transformCanonicalBodyPoint(p.x, p.y, transform))
          .map((p) => [p.x, p.y] as [number, number]);
        if (points.length !== 3) continue;
        bodyFills.push({
          key: `fill-diode-${idx}`,
          points,
          color: fillColor,
          opacity: fillOpacity,
        });
      }
    }

    if (family === 'capacitor_polarized' && templateSymbol.rectangles.length > 0) {
      let negativeIdx = 0;
      let minCenterY = Number.POSITIVE_INFINITY;
      for (let idx = 0; idx < templateSymbol.rectangles.length; idx += 1) {
        const rect = templateSymbol.rectangles[idx];
        const centerY = (rect.startY + rect.endY) * 0.5;
        if (centerY < minCenterY) {
          minCenterY = centerY;
          negativeIdx = idx;
        }
      }
      const rect = templateSymbol.rectangles[negativeIdx];
      const p0 = transformCanonicalBodyPoint(rect.startX, rect.startY, transform);
      const p1 = transformCanonicalBodyPoint(rect.endX, rect.startY, transform);
      const p2 = transformCanonicalBodyPoint(rect.endX, rect.endY, transform);
      const p3 = transformCanonicalBodyPoint(rect.startX, rect.endY, transform);
      bodyFills.push({
        key: `fill-cap-neg-${negativeIdx}`,
        points: [
          [p0.x, p0.y],
          [p1.x, p1.y],
          [p2.x, p2.y],
          [p3.x, p3.y],
        ],
        color: lineColor,
        opacity: POLARIZED_CAP_NEGATIVE_PLATE_FILL_OPACITY,
      });
    }

    const pt = (x: number, y: number): [number, number, number] => {
      const p = transformCanonicalBodyPoint(x, y, transform);
      return [p.x, p.y, 0];
    };

    return (
      <group raycast={NO_RAYCAST}>
        {bodyFills.map((fill) => {
          const shape = new Shape();
          shape.moveTo(fill.points[0][0], fill.points[0][1]);
          for (let i = 1; i < fill.points.length; i += 1) {
            shape.lineTo(fill.points[i][0], fill.points[i][1]);
          }
          shape.closePath();
          return (
            <mesh key={fill.key} position={[0, 0, -0.0004]} raycast={NO_RAYCAST}>
              <shapeGeometry args={[shape]} />
              <meshBasicMaterial
                color={fill.color}
                transparent
                opacity={fill.opacity}
                depthWrite={false}
              />
            </mesh>
          );
        })}

        {templateSymbol.rectangles.map((rect, idx) => (
          <Line
            key={`rect-${idx}`}
            points={[
              pt(rect.startX, rect.startY),
              pt(rect.endX, rect.startY),
              pt(rect.endX, rect.endY),
              pt(rect.startX, rect.endY),
              pt(rect.startX, rect.startY),
            ]}
            color={lineColor}
            lineWidth={lineWidth}
            worldUnits
            raycast={NO_RAYCAST}
          />
        ))}

        {templateSymbol.polylines.map((poly, idx) => (
          isDiodeCenterBridgePolyline(family, poly)
            ? null
            : (
              <Line
                key={`poly-${idx}`}
                points={poly.points.map((p) => pt(p.x, p.y))}
                color={lineColor}
                lineWidth={lineWidth}
                worldUnits
                raycast={NO_RAYCAST}
              />
            )
        ))}

        {templateSymbol.circles.map((circle, idx) => {
          const center = transformCanonicalBodyPoint(
            circle.centerX,
            circle.centerY,
            transform,
          );
          return (
            <Line
              key={`circle-${idx}`}
              points={circlePoints(
                center.x,
                center.y,
                circle.radius * transform.unit,
                24,
              )}
              color={lineColor}
              lineWidth={lineWidth}
              worldUnits
              raycast={NO_RAYCAST}
            />
          );
        })}

        {templateSymbol.arcs.map((arc, idx) => (
          <Line
            key={`arc-${idx}`}
            points={kicadArcPoints(arc, 20).map(([x, y]) => pt(x, y))}
            color={lineColor}
            lineWidth={lineWidth}
            worldUnits
            raycast={NO_RAYCAST}
          />
        ))}
      </group>
    );
  }

  if (family === 'resistor') {
    const halfW = Math.max(0.9, W * 0.28 * scale);
    const halfH = Math.max(0.26, H * 0.3);
    const points: Array<[number, number, number]> = [
      [-halfW, -halfH, 0],
      [halfW, -halfH, 0],
      [halfW, halfH, 0],
      [-halfW, halfH, 0],
      [-halfW, -halfH, 0],
    ];
    return (
      <Line
        points={points}
        color={lineColor}
        lineWidth={lineWidth}
        worldUnits
        raycast={NO_RAYCAST}
      />
    );
  }

  if (family === 'capacitor' || family === 'capacitor_polarized') {
    const plateGap = Math.max(0.18, W * 0.12 * scale);
    const halfPlate = Math.max(0.34, H * 0.36);
    const plateHalfThickness = 0.22;
    const negativePlateFillShape = new Shape();
    negativePlateFillShape.moveTo(plateGap - plateHalfThickness, -halfPlate);
    negativePlateFillShape.lineTo(plateGap + plateHalfThickness, -halfPlate);
    negativePlateFillShape.lineTo(plateGap + plateHalfThickness, halfPlate);
    negativePlateFillShape.lineTo(plateGap - plateHalfThickness, halfPlate);
    negativePlateFillShape.closePath();
    return (
      <group raycast={NO_RAYCAST}>
        {family === 'capacitor_polarized' && (
          <mesh position={[0, 0, -0.0004]} raycast={NO_RAYCAST}>
            <shapeGeometry args={[negativePlateFillShape]} />
            <meshBasicMaterial
              color={lineColor}
              transparent
              opacity={POLARIZED_CAP_NEGATIVE_PLATE_FILL_OPACITY}
              depthWrite={false}
            />
          </mesh>
        )}
        <Line
          points={[
            [-plateGap, -halfPlate, 0],
            [-plateGap, halfPlate, 0],
          ]}
          color={lineColor}
          lineWidth={lineWidth}
          worldUnits
          raycast={NO_RAYCAST}
        />
        <Line
          points={[
            [plateGap, -halfPlate, 0],
            [plateGap, halfPlate, 0],
          ]}
          color={lineColor}
          lineWidth={lineWidth}
          worldUnits
          raycast={NO_RAYCAST}
        />
        {family === 'capacitor_polarized' && (
          <group raycast={NO_RAYCAST}>
            <Line
              points={[
                [-plateGap - 0.32, 0.18, 0],
                [-plateGap - 0.12, 0.18, 0],
              ]}
              color={lineColor}
              lineWidth={SYMBOL_STROKE_WIDTH_FINE}
              worldUnits
              raycast={NO_RAYCAST}
            />
            <Line
              points={[
                [-plateGap - 0.22, 0.08, 0],
                [-plateGap - 0.22, 0.28, 0],
              ]}
              color={lineColor}
              lineWidth={SYMBOL_STROKE_WIDTH_FINE}
              worldUnits
              raycast={NO_RAYCAST}
            />
          </group>
        )}
      </group>
    );
  }

  if (family === 'inductor') {
    const turns = 4;
    const radius = Math.max(0.2, Math.min(W * 0.09 * scale, H * 0.34));
    const startX = -turns * radius;
    const points: Array<[number, number, number]> = [];

    for (let i = 0; i < turns; i += 1) {
      const cx = startX + radius + i * radius * 2;
      const arc = arcPoints(cx, 0, radius, Math.PI, 0, 10);
      if (i > 0) arc.shift();
      points.push(...arc);
    }

    return (
      <Line
        points={points}
        color={lineColor}
        lineWidth={lineWidth}
        worldUnits
        raycast={NO_RAYCAST}
      />
    );
  }

  if (family === 'diode' || family === 'led') {
    const left = -Math.max(0.9, W * 0.2);
    const barX = Math.max(0.8, W * 0.2);
    const halfY = Math.max(0.32, H * 0.3);
    const fillShape = new Shape();
    fillShape.moveTo(left, -halfY);
    fillShape.lineTo(left, halfY);
    fillShape.lineTo(barX, 0);
    fillShape.closePath();
    const fillColor = family === 'led' ? inferLedFillColor(component) : lineColor;
    const fillOpacity = family === 'led' ? LED_FILL_OPACITY : DIODE_FILL_OPACITY;

    return (
      <group raycast={NO_RAYCAST}>
        <mesh position={[0, 0, -0.0004]} raycast={NO_RAYCAST}>
          <shapeGeometry args={[fillShape]} />
          <meshBasicMaterial
            color={fillColor}
            transparent
            opacity={fillOpacity}
            depthWrite={false}
          />
        </mesh>
        <Line
          points={[
            [left, -halfY, 0],
            [left, halfY, 0],
            [barX, 0, 0],
            [left, -halfY, 0],
          ]}
          color={lineColor}
          lineWidth={lineWidth}
          worldUnits
          raycast={NO_RAYCAST}
        />
        <Line
          points={[
            [barX, -halfY, 0],
            [barX, halfY, 0],
          ]}
          color={lineColor}
          lineWidth={lineWidth}
          worldUnits
          raycast={NO_RAYCAST}
        />

        {family === 'led' && (
          <group raycast={NO_RAYCAST}>
            <Line
              points={[
                [barX - 0.14, halfY * 0.2, 0],
                [barX + 0.62, halfY + 0.62, 0],
              ]}
              color={lineColor}
              lineWidth={SYMBOL_STROKE_WIDTH_FINE}
              worldUnits
              raycast={NO_RAYCAST}
            />
            <Line
              points={[
                [barX + 0.42, halfY + 0.63, 0],
                [barX + 0.62, halfY + 0.62, 0],
                [barX + 0.57, halfY + 0.42, 0],
              ]}
              color={lineColor}
              lineWidth={SYMBOL_STROKE_WIDTH_FINE}
              worldUnits
              raycast={NO_RAYCAST}
            />
            <Line
              points={[
                [barX - 0.3, -halfY * 0.06, 0],
                [barX + 0.45, halfY + 0.34, 0],
              ]}
              color={lineColor}
              lineWidth={SYMBOL_STROKE_WIDTH_FINE}
              worldUnits
              raycast={NO_RAYCAST}
            />
            <Line
              points={[
                [barX + 0.25, halfY + 0.35, 0],
                [barX + 0.45, halfY + 0.34, 0],
                [barX + 0.4, halfY + 0.14, 0],
              ]}
              color={lineColor}
              lineWidth={SYMBOL_STROKE_WIDTH_FINE}
              worldUnits
              raycast={NO_RAYCAST}
            />
          </group>
        )}
      </group>
    );
  }

  if (family === 'testpoint') {
    const radius = Math.max(0.32, Math.min(W, H) * 0.34);
    return (
      <group raycast={NO_RAYCAST}>
        <Line
          points={circlePoints(0, 0.08, radius, 24)}
          color={lineColor}
          lineWidth={lineWidth}
          worldUnits
          raycast={NO_RAYCAST}
        />
        <Line
          points={[
            [0, -radius + 0.08, 0],
            [0, -radius - 0.56, 0],
          ]}
          color={lineColor}
          lineWidth={lineWidth}
          worldUnits
          raycast={NO_RAYCAST}
        />
      </group>
    );
  }

  return null;
}

interface Props {
  component: SchematicComponent;
  theme: ThemeColors;
  isSelected: boolean;
  isHovered: boolean;
  isDragging: boolean;
  selectedNetId: string | null;
  netsForComponent: Map<string, string>;
  rotation?: number;
  mirrorX?: boolean;
  mirrorY?: boolean;
}

export const ComponentRenderer = memo(function ComponentRenderer({
  component,
  theme,
  isSelected,
  isHovered,
  isDragging,
  selectedNetId,
  netsForComponent,
  rotation = 0,
  mirrorX = false,
  mirrorY = false,
}: Props) {
  const W = component.bodyWidth;
  const H = component.bodyHeight;
  const isSmall = W * H < SMALL_AREA;
  const accent = isSelected ? theme.textSecondary : theme.textMuted;

  const symbolFamily = useMemo(() => inferSymbolFamily(component), [component]);
  const symbolTuning = useMemo(
    () => getSymbolRenderTuning(symbolFamily),
    [symbolFamily],
  );
  const templateSymbol = useMemo(() => {
    if (!symbolFamily) return null;
    return getCanonicalKicadSymbol(symbolFamily, component.pins.length)
      ?? getKicadTemplateSymbol(symbolFamily, component.pins.length);
  }, [symbolFamily, component.pins.length]);
  const pinAttachOverrides = useMemo(() => {
    if (!symbolFamily || !templateSymbol) return null;
    return getCanonicalPinAttachmentMap(
      component,
      symbolFamily,
      templateSymbol,
      symbolTuning,
      CUSTOM_SYMBOL_BODY_BASE_Y,
    );
  }, [component, symbolFamily, templateSymbol, symbolTuning]);
  const symbolBodyCenter = useMemo(() => {
    if (!symbolFamily) return null;
    return {
      x: symbolTuning.bodyOffsetX,
      y: symbolTuning.bodyOffsetY + CUSTOM_SYMBOL_BODY_BASE_Y,
    };
  }, [symbolFamily, symbolTuning]);
  const renderedPins = useMemo(() => {
    if (symbolFamily !== 'testpoint') return component.pins;
    const primaryPin = component.pins.find((pin) => pin.number === '1') ?? component.pins[0];
    return primaryPin ? [primaryPin] : [];
  }, [component.pins, symbolFamily]);
  const hasCustomSymbol = symbolFamily !== null;

  const textTf = useMemo(
    () => getUprightTextTransform(rotation, mirrorX, mirrorY),
    [rotation, mirrorX, mirrorY],
  );

  const RADIUS = Math.min(W, H) * 0.08;
  const maxDim = Math.min(W, H);
  const refFontSizeBase = isSmall
    ? Math.min(1.35, Math.max(0.62, maxDim * 0.34))
    : Math.min(1.35, Math.max(0.78, maxDim * 0.18));
  const refFontSize = hasCustomSymbol ? refFontSizeBase * 0.85 : refFontSizeBase;
  const refLabelY = hasCustomSymbol ? -Math.min(H * 0.36, 0.96) : 0;
  const bodyRefMaxWidth = hasCustomSymbol ? W * 0.72 : W * 0.84;

  const showNameBadge = (isHovered || isSelected) && component.name.trim().length > 0;
  const nameBadgeWidth = Math.min(Math.max(W * 0.95, 10), 28);
  const nameBadgeHeight = 1.9;
  const nameBadgeRadius = 0.34;
  const nameBadgeFontSize = 0.72;
  const displayName = useMemo(() => {
    const raw = component.name.trim();
    if (!raw) return '';
    const maxChars = Math.max(10, Math.floor(nameBadgeWidth / (nameBadgeFontSize * 0.55)));
    if (raw.length <= maxChars) return raw;
    return raw.slice(0, Math.max(1, maxChars - 1)) + '\u2026';
  }, [component.name, nameBadgeWidth, nameBadgeFontSize]);

  const zOffset = isDragging ? 0.5 : 0;
  const gridOffset = useMemo(
    () => getComponentGridAlignmentOffset(component),
    [component],
  );

  const showPackageLabel = hasCustomSymbol && !!component.packageCode && !isSmall;

  return (
    <group position={[gridOffset.x, gridOffset.y, zOffset]} raycast={NO_RAYCAST}>
      {/* Dedicated hit target so component selection still works while visual
          primitives keep raycast disabled for performance. */}
      <mesh position={[0, 0, -0.1]}>
        <planeGeometry args={[Math.max(W + 0.6, 1.2), Math.max(H + 0.6, 1.2)]} />
        <meshBasicMaterial transparent opacity={0} depthWrite={false} />
      </mesh>

      {isSelected && (
        <RoundedBox
          args={[W + 1.2, H + 1.2, 0.001]}
          radius={RADIUS + 0.2}
          smoothness={4}
          position={[0, 0, -0.06]}
          raycast={NO_RAYCAST}
        >
          <meshBasicMaterial color={theme.textSecondary} transparent opacity={0.14} depthWrite={false} />
        </RoundedBox>
      )}

      {isHovered && !isSelected && (
        <RoundedBox
          args={[W + 0.6, H + 0.6, 0.001]}
          radius={RADIUS + 0.08}
          smoothness={4}
          position={[0, 0, -0.06]}
          raycast={NO_RAYCAST}
        >
          <meshBasicMaterial color={theme.textMuted} transparent opacity={0.08} depthWrite={false} />
        </RoundedBox>
      )}

      {!hasCustomSymbol && (
        <>
          <RoundedBox
            args={[W + 0.12, H + 0.12, 0.001]}
            radius={RADIUS + 0.02}
            smoothness={4}
            position={[0, 0, -0.04]}
            raycast={NO_RAYCAST}
          >
            <meshBasicMaterial
              color={isSelected ? accent : theme.bodyBorder}
              depthWrite={false}
            />
          </RoundedBox>

          <RoundedBox
            args={[W, H, 0.001]}
            radius={RADIUS}
            smoothness={4}
            position={[0, 0, -0.02]}
            raycast={NO_RAYCAST}
          >
            <meshBasicMaterial color={theme.bodyFill} depthWrite={false} />
          </RoundedBox>
        </>
      )}

      {hasCustomSymbol && (
        <>
          {symbolFamily && (
            <group position={[0, CUSTOM_SYMBOL_BODY_BASE_Y, 0.001]} raycast={NO_RAYCAST}>
              <SymbolGlyph
                component={component}
                family={symbolFamily}
                color={accent}
                templateSymbol={templateSymbol}
                tuning={symbolTuning}
              />
            </group>
          )}
        </>
      )}

      <group
        position={[0, refLabelY, 0.001]}
        rotation={[0, 0, textTf.rotationZ]}
        scale={[textTf.scaleX, textTf.scaleY, 1]}
      >
        <Text
          fontSize={refFontSize}
          color={accent}
          anchorX="center"
          anchorY="middle"
          letterSpacing={0.04}
          maxWidth={bodyRefMaxWidth}
          clipRect={[-W / 2, -H / 2, W / 2, H / 2]}
          font={undefined}
          raycast={NO_RAYCAST}
        >
          {component.designator}
        </Text>
      </group>

      {showPackageLabel && (
        <group
          position={[0, -H / 2 - 0.82, 0.01]}
          rotation={[0, 0, textTf.rotationZ]}
          scale={[textTf.scaleX, textTf.scaleY, 1]}
          raycast={NO_RAYCAST}
        >
          <Text
            fontSize={0.52}
            color={theme.textMuted}
            anchorX="center"
            anchorY="middle"
            letterSpacing={0.02}
            font={undefined}
            raycast={NO_RAYCAST}
          >
            {component.packageCode}
          </Text>
        </group>
      )}

      {showNameBadge && (
        <group
          position={[0, H / 2 + nameBadgeHeight / 2 + 0.7, 0.01]}
          rotation={[0, 0, textTf.rotationZ]}
          scale={[textTf.scaleX, textTf.scaleY, 1]}
          raycast={NO_RAYCAST}
        >
          <RoundedBox
            args={[nameBadgeWidth + 0.12, nameBadgeHeight + 0.12, 0.001]}
            radius={nameBadgeRadius + 0.03}
            smoothness={4}
            position={[0, 0, -0.001]}
            raycast={NO_RAYCAST}
          >
            <meshBasicMaterial
              color={isSelected ? accent : theme.bodyBorder}
              transparent
              opacity={0.82}
              depthWrite={false}
            />
          </RoundedBox>
          <RoundedBox
            args={[nameBadgeWidth, nameBadgeHeight, 0.001]}
            radius={nameBadgeRadius}
            smoothness={4}
            raycast={NO_RAYCAST}
          >
            <meshBasicMaterial
              color={theme.bgSecondary}
              transparent
              opacity={0.94}
              depthWrite={false}
            />
          </RoundedBox>
          <Text
            position={[0, 0, 0.002]}
            fontSize={nameBadgeFontSize}
            color={theme.textPrimary}
            anchorX="center"
            anchorY="middle"
            maxWidth={nameBadgeWidth - 1.2}
            letterSpacing={0.015}
            font={undefined}
            raycast={NO_RAYCAST}
          >
            {displayName}
          </Text>
        </group>
      )}

      <mesh
        position={[
          -W / 2 + Math.max(0.5, W * 0.06),
          H / 2 - Math.max(0.5, H * 0.06),
          0.001,
        ]}
        raycast={NO_RAYCAST}
      >
        <circleGeometry args={[isSmall ? 0.2 : 0.35, 16]} />
        <meshBasicMaterial color={theme.textMuted} transparent opacity={0.3} />
      </mesh>

      {renderedPins.map((pin) => (
        <SchematicPinElement
          key={pin.number}
          component={component}
          pin={pin}
          theme={theme}
          isSmall={isSmall}
          netId={netsForComponent.get(pin.number) ?? null}
          selectedNetId={selectedNetId}
          textRotationZ={textTf.rotationZ}
          textScaleX={textTf.scaleX}
          textScaleY={textTf.scaleY}
          rotationDeg={rotation}
          mirrorX={mirrorX}
          mirrorY={mirrorY}
          symbolFamily={symbolFamily}
          pinAttachOverride={pinAttachOverrides?.get(pin.number) ?? null}
          pinBodyCenterOverride={symbolBodyCenter}
        />
      ))}
    </group>
  );
});

const SchematicPinElement = memo(function SchematicPinElement({
  component,
  pin,
  theme,
  isSmall,
  netId,
  selectedNetId,
  textRotationZ = 0,
  textScaleX = 1,
  textScaleY = 1,
  rotationDeg = 0,
  mirrorX = false,
  mirrorY = false,
  symbolFamily,
  pinAttachOverride,
  pinBodyCenterOverride,
}: {
  component: SchematicComponent;
  pin: SchematicPin;
  theme: ThemeColors;
  isSmall: boolean;
  netId: string | null;
  selectedNetId: string | null;
  textRotationZ?: number;
  textScaleX?: number;
  textScaleY?: number;
  rotationDeg?: number;
  mirrorX?: boolean;
  mirrorY?: boolean;
  symbolFamily: SchematicSymbolFamily | null;
  pinAttachOverride?: { x: number; y: number } | null;
  pinBodyCenterOverride?: { x: number; y: number } | null;
}) {
  const color = getConnectionColor(pin.category, theme);
  const isNetHighlighted = netId !== null && netId === selectedNetId;
  const isDimmed = selectedNetId !== null && !isNetHighlighted;
  const showName = pin.name !== pin.number;
  const DOT_RADIUS = 0.15;
  const pinOpacity = isNetHighlighted ? 1 : isDimmed ? 0.25 : 0.8;
  const pinGeom = useMemo(
    () => getTunedPinGeometry(
      component,
      pin,
      symbolFamily,
      pinAttachOverride,
      undefined,
      pinBodyCenterOverride,
    ),
    [component, pin, symbolFamily, pinAttachOverride, pinBodyCenterOverride],
  );
  const pinX = pinGeom.x;
  const pinY = pinGeom.y;
  const bodyX = pinGeom.bodyX;
  const bodyY = pinGeom.bodyY;

  let nameX: number;
  let nameY: number;
  let numX: number;
  let numY: number;
  const NAME_INSET = 0.8;
  const NUM_OFFSET = 0.6;

  if (pin.side === 'left') {
    nameX = bodyX + NAME_INSET;
    nameY = pinY;
    numX = pinX;
    numY = pinY + NUM_OFFSET;
  } else if (pin.side === 'right') {
    nameX = bodyX - NAME_INSET;
    nameY = pinY;
    numX = pinX;
    numY = pinY + NUM_OFFSET;
  } else if (pin.side === 'top') {
    nameX = pinX;
    nameY = bodyY - NAME_INSET;
    numX = pinX + NUM_OFFSET;
    numY = pinY;
  } else {
    nameX = pinX;
    nameY = bodyY + NAME_INSET;
    numX = pinX + NUM_OFFSET;
    numY = pinY;
  }

  const effectiveNameAnchorX = anchorFromVisualSide(pin.side, {
    rotationDeg,
    mirrorX,
    mirrorY,
    left: 'left',
    right: 'right',
    vertical: 'center',
  });

  return (
    <group raycast={NO_RAYCAST}>
      <Line
        points={[
          [pinX, pinY, 0],
          [bodyX, bodyY, 0],
        ]}
        color={color}
        lineWidth={isNetHighlighted ? PIN_LEAD_WIDTH_ACTIVE : PIN_LEAD_WIDTH}
        worldUnits
        transparent
        opacity={pinOpacity}
        raycast={NO_RAYCAST}
      />

      <mesh position={[pinX, pinY, 0.001]} raycast={NO_RAYCAST}>
        <circleGeometry args={[DOT_RADIUS, 16]} />
        <meshBasicMaterial color={color} transparent opacity={pinOpacity} />
      </mesh>

      {showName && !isSmall && (
        <group
          position={[nameX, nameY, 0.002]}
          rotation={[0, 0, textRotationZ]}
          scale={[textScaleX, textScaleY, 1]}
        >
          <Text
            fontSize={1.05}
            color={theme.textSecondary}
            anchorX={effectiveNameAnchorX}
            anchorY="middle"
            font={undefined}
            raycast={NO_RAYCAST}
          >
            {pin.name}
          </Text>
        </group>
      )}

      {!isSmall && (
        <group
          position={[numX, numY, 0.002]}
          rotation={[0, 0, textRotationZ]}
          scale={[textScaleX, textScaleY, 1]}
        >
          <Text
            fontSize={0.65}
            color={theme.textMuted}
            anchorX="center"
            anchorY="middle"
            font={undefined}
            raycast={NO_RAYCAST}
          >
            {pin.number}
          </Text>
        </group>
      )}
    </group>
  );
});
