/**
 * ComponentRenderer - draws a SchematicComponent body + pins.
 *
 * Wrapped in React.memo for render skipping - only re-renders when
 * selection/hover/drag state actually changes for this component.
 */

import { memo, useCallback, useMemo, useRef } from 'react';
import { Html, Line, RoundedBox, Text } from '@react-three/drei';
import { Shape, type Camera, type Object3D, Vector3 } from 'three';
import type {
  SchematicComponent,
  SchematicPin,
  SchematicSymbolFamily,
} from '../types/schematic';
import type { KicadArc } from '../types/symbol';
import {
  getComponentGridAlignmentOffset,
} from '../types/schematic';
import type { ThemeColors } from '../utils/theme';
import { getCanonicalKicadSymbol } from '../symbol-catalog/canonicalSymbolCatalog';
import { getSymbolRenderTuning } from '../symbol-catalog/symbolTuning';
import { getSymbolVisualTuning } from '../symbol-catalog/symbolVisualTuning';
import { inferSymbolFamily } from '../symbol-catalog/symbolFamilyInference';
import { anchorFromVisualSide, getUprightTextTransform } from '../utils/itemTransform';
import { getConnectionColor } from './connectionColor';
import {
  CUSTOM_SYMBOL_BODY_BASE_Y,
  getCanonicalGlyphTransform,
  getCanonicalPinAttachmentMap,
  getTunedPinGeometry,
  transformCanonicalBodyPoint,
} from './symbolRenderGeometry';

const SMALL_AREA = 40;
const NO_RAYCAST = () => {};
const PIN_LEAD_WIDTH_ACTIVE_RATIO = 1.22;
const DIODE_FILL_OPACITY = 0.28;
const LED_FILL_OPACITY = 0.42;
const POLARIZED_CAP_NEGATIVE_PLATE_FILL_OPACITY = 0.72;
const HOVER_CARD_MAX_WIDTH_PX = 260;
const HOVER_CARD_MIN_WIDTH_PX = 140;
const HOVER_CARD_MARGIN_PX = 14;
const HOVER_CARD_MAX_HEIGHT_PX = 62;

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

function normalizeTextRotationUpright(rotationDeg: number): number {
  let rot = ((rotationDeg % 360) + 360) % 360;
  if (rot > 180) rot -= 360;
  if (rot > 90) rot -= 180;
  if (rot <= -90) rot += 180;
  return rot;
}

function stripToleranceSuffix(value: string): string {
  return value
    .replace(/\s*(?:\+\/-|±)\s*\d+(?:\.\d+)?\s*%.*$/i, '')
    .trim();
}

function deriveValueLabel(component: SchematicComponent): string {
  const raw = component.name.trim();
  if (!raw) return '';
  const stripped = stripToleranceSuffix(raw);
  if (!stripped) return '';
  if (stripped.toUpperCase() === component.designator.toUpperCase()) return '';
  // Avoid showing package-only names like "0603" and template IDs like "Demo_LED_0603".
  if (!/[a-z]/i.test(stripped) || stripped.includes('_')) return '';
  // Only render likely value-like tokens (e.g. 100nF, 10k, 4.7uH).
  if (!/\d/.test(stripped)) return '';
  if (!/(ohm|[munpfk]?f|[munpfk]?h|[mk]?r)\b/i.test(stripped)) return '';
  return stripped;
}

interface SymbolGlyphProps {
  component: SchematicComponent;
  family: SchematicSymbolFamily;
  color: string;
  templateSymbol: ReturnType<typeof getCanonicalKicadSymbol>;
  symbolStrokeWidth: number;
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
  symbolStrokeWidth,
  tuning,
}: SymbolGlyphProps) {
  const lineColor = color;
  const lineWidth = symbolStrokeWidth;
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
  tuningRevision?: number;
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
  tuningRevision = 0,
}: Props) {
  const W = component.bodyWidth;
  const H = component.bodyHeight;
  const isSmall = W * H < SMALL_AREA;
  const accent = isSelected ? theme.textSecondary : theme.textMuted;

  const symbolFamily = useMemo(() => inferSymbolFamily(component), [component]);
  const symbolTuning = useMemo(
    () => getSymbolRenderTuning(symbolFamily),
    [symbolFamily, tuningRevision],
  );
  const symbolVisualTuning = useMemo(
    () => getSymbolVisualTuning(symbolFamily, component),
    [symbolFamily, component, tuningRevision],
  );
  const templateSymbol = useMemo(() => {
    if (!symbolFamily) return null;
    return getCanonicalKicadSymbol(symbolFamily, component.pins.length);
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
  const refFontSize = hasCustomSymbol
    ? symbolVisualTuning.designator.fontSize
    : refFontSizeBase;
  const refLabelX = hasCustomSymbol ? symbolVisualTuning.designator.offsetX : 0;
  const refLabelY = hasCustomSymbol ? symbolVisualTuning.designator.offsetY : 0;
  const refLabelRotationZ = hasCustomSymbol
    ? (-symbolVisualTuning.designator.rotationDeg * Math.PI) / 180
    : 0;
  const packageLabelX = hasCustomSymbol ? symbolVisualTuning.package.offsetX : 0;
  const packageLabelY = hasCustomSymbol ? symbolVisualTuning.package.offsetY : -H / 2 - 0.82;
  const packageFontSize = hasCustomSymbol ? symbolVisualTuning.package.fontSize : 0.52;
  const valueLabel = hasCustomSymbol ? deriveValueLabel(component) : '';
  const showValueLabel = hasCustomSymbol && valueLabel.length > 0;
  const valueLabelX = hasCustomSymbol ? symbolVisualTuning.value.offsetX : 0;
  const valueLabelY = hasCustomSymbol ? symbolVisualTuning.value.offsetY : H / 2 + 0.86;
  const valueFontSize = hasCustomSymbol ? symbolVisualTuning.value.fontSize : 0.52;
  const valueRotationZ = hasCustomSymbol
    ? (-symbolVisualTuning.value.rotationDeg * Math.PI) / 180
    : 0;
  const packageLabelRotationDeg = hasCustomSymbol
    ? (() => {
      const raw = symbolVisualTuning.package.rotationDeg
        + (symbolVisualTuning.package.followInstanceRotation ? rotation : 0);
      if (!symbolVisualTuning.package.followInstanceRotation) return raw;
      return normalizeTextRotationUpright(raw);
    })()
    : 0;
  const packageRotationZ = (-packageLabelRotationDeg * Math.PI) / 180;
  const pinLeadWidth = hasCustomSymbol ? symbolVisualTuning.leadStrokeWidth : 0.28;
  const pinLeadWidthActive = pinLeadWidth * PIN_LEAD_WIDTH_ACTIVE_RATIO;
  const pinDotRadius = hasCustomSymbol ? symbolVisualTuning.connectionDotRadius : 0.15;
  const bodyRefMaxWidth = hasCustomSymbol ? W * 0.72 : W * 0.84;

  const showHoverCard = (isHovered || isSelected) && component.name.trim().length > 0;
  const hoverCardTitle = useMemo(() => {
    const name = component.name.trim();
    if (!name) return component.designator;
    const maxChars = 34;
    return name.length <= maxChars ? name : `${name.slice(0, maxChars - 1)}\u2026`;
  }, [component.designator, component.name]);
  const hoverCardMeta = useMemo(() => {
    const meta = [component.designator, component.packageCode]
      .filter((v): v is string => !!v && v.trim().length > 0);
    return meta.join(' \u00b7 ');
  }, [component.designator, component.packageCode]);
  const hoverCardWidthPx = useMemo(() => {
    const charWidthPx = 7.1;
    const paddingPx = 28;
    const desired = hoverCardTitle.length * charWidthPx + paddingPx;
    return Math.max(HOVER_CARD_MIN_WIDTH_PX, Math.min(HOVER_CARD_MAX_WIDTH_PX, desired));
  }, [hoverCardTitle]);
  const hoverCardAnchorY = H / 2 + (hasCustomSymbol ? 1.9 : 1.35);
  const hoverProjectRef = useRef(new Vector3());
  const calculateHoverCardPosition = useCallback(
    (
      object: Object3D,
      camera: Camera,
      size: { width: number; height: number },
    ): [number, number] => {
      object.getWorldPosition(hoverProjectRef.current);
      hoverProjectRef.current.project(camera);
      const rawX = (hoverProjectRef.current.x * 0.5 + 0.5) * size.width;
      const rawY = (-hoverProjectRef.current.y * 0.5 + 0.5) * size.height;
      const halfW = hoverCardWidthPx * 0.5;
      const halfH = HOVER_CARD_MAX_HEIGHT_PX * 0.5;
      const x = Math.min(
        size.width - HOVER_CARD_MARGIN_PX - halfW,
        Math.max(HOVER_CARD_MARGIN_PX + halfW, rawX),
      );
      const y = Math.min(
        size.height - HOVER_CARD_MARGIN_PX - halfH,
        Math.max(HOVER_CARD_MARGIN_PX + halfH, rawY),
      );
      return [x, y];
    },
    [hoverCardWidthPx],
  );

  const zOffset = isDragging ? 0.5 : 0;
  const gridOffset = useMemo(
    () => getComponentGridAlignmentOffset(component),
    [component],
  );

  const showPackageLabel = hasCustomSymbol && !!component.packageCode;

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
                symbolStrokeWidth={symbolVisualTuning.symbolStrokeWidth}
                tuning={symbolTuning}
              />
            </group>
          )}
        </>
      )}

      <group
        position={[refLabelX, refLabelY, 0.001]}
        rotation={[0, 0, textTf.rotationZ]}
        scale={[textTf.scaleX, textTf.scaleY, 1]}
      >
        <group rotation={[0, 0, refLabelRotationZ]} raycast={NO_RAYCAST}>
          <Text
            fontSize={refFontSize}
            color={accent}
            anchorX="center"
            anchorY="middle"
            letterSpacing={0.04}
            maxWidth={bodyRefMaxWidth}
            clipRect={hasCustomSymbol ? undefined : [-W / 2, -H / 2, W / 2, H / 2]}
            font={undefined}
            raycast={NO_RAYCAST}
          >
            {component.designator}
          </Text>
        </group>
      </group>

      {showValueLabel && (
        <group
          position={[valueLabelX, valueLabelY, 0.01]}
          rotation={[0, 0, textTf.rotationZ]}
          scale={[textTf.scaleX, textTf.scaleY, 1]}
          raycast={NO_RAYCAST}
        >
          <group rotation={[0, 0, valueRotationZ]} raycast={NO_RAYCAST}>
            <Text
              fontSize={valueFontSize}
              color={theme.textMuted}
              anchorX="center"
              anchorY="middle"
              letterSpacing={0.02}
              font={undefined}
              raycast={NO_RAYCAST}
            >
              {valueLabel}
            </Text>
          </group>
        </group>
      )}

      {showPackageLabel && (
        <group
          position={[packageLabelX, packageLabelY, 0.01]}
          rotation={[0, 0, textTf.rotationZ]}
          scale={[textTf.scaleX, textTf.scaleY, 1]}
          raycast={NO_RAYCAST}
        >
          <group rotation={[0, 0, packageRotationZ]} raycast={NO_RAYCAST}>
            <Text
              fontSize={packageFontSize}
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
        </group>
      )}

      {showHoverCard && (
        <group position={[0, hoverCardAnchorY, 0.03]} raycast={NO_RAYCAST}>
          <Html
            center
            style={{ pointerEvents: 'none' }}
            calculatePosition={calculateHoverCardPosition}
          >
            <div
              style={{
                minWidth: `${HOVER_CARD_MIN_WIDTH_PX}px`,
                maxWidth: `${hoverCardWidthPx}px`,
                padding: '8px 10px',
                borderRadius: '10px',
                border: `1px solid ${isSelected ? `${accent}99` : `${theme.borderColor}cc`}`,
                background: `linear-gradient(180deg, ${theme.bgSecondary}f2 0%, ${theme.bgPrimary}f0 100%)`,
                boxShadow: '0 10px 24px rgba(0,0,0,0.34)',
                backdropFilter: 'blur(5px)',
                WebkitBackdropFilter: 'blur(5px)',
                color: theme.textPrimary,
                lineHeight: 1.2,
              }}
            >
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  minWidth: 0,
                }}
              >
                <span
                  style={{
                    width: 7,
                    height: 7,
                    borderRadius: 999,
                    background: accent,
                    opacity: 0.92,
                    flex: '0 0 auto',
                    boxShadow: `0 0 0 1px ${theme.bgPrimary}99`,
                  }}
                />
                <span
                  style={{
                    display: 'block',
                    fontSize: 12,
                    fontWeight: 600,
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    minWidth: 0,
                  }}
                >
                  {hoverCardTitle}
                </span>
              </div>
              {hoverCardMeta && (
                <div
                  style={{
                    marginTop: 4,
                    fontSize: 11,
                    color: theme.textMuted,
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                  }}
                >
                  {hoverCardMeta}
                </div>
              )}
            </div>
          </Html>
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
          leadStrokeWidth={pinLeadWidth}
          leadStrokeWidthActive={pinLeadWidthActive}
          connectionDotRadius={pinDotRadius}
          pinVisualColor={hasCustomSymbol ? accent : undefined}
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
  leadStrokeWidth = 0.28,
  leadStrokeWidthActive = 0.34,
  connectionDotRadius = 0.15,
  pinVisualColor,
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
  leadStrokeWidth?: number;
  leadStrokeWidthActive?: number;
  connectionDotRadius?: number;
  pinVisualColor?: string;
}) {
  const color = pinVisualColor ?? getConnectionColor(pin.category, theme);
  const isNetHighlighted = netId !== null && netId === selectedNetId;
  const isDimmed = selectedNetId !== null && !isNetHighlighted;
  const showName = pin.name !== pin.number;
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
        lineWidth={isNetHighlighted ? leadStrokeWidthActive : leadStrokeWidth}
        worldUnits
        transparent
        opacity={pinOpacity}
        raycast={NO_RAYCAST}
      />

      <mesh position={[pinX, pinY, 0.001]} raycast={NO_RAYCAST}>
        <circleGeometry args={[connectionDotRadius, 16]} />
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
