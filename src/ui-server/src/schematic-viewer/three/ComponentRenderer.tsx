/**
 * ComponentRenderer - draws a SchematicComponent body + pins.
 *
 * Wrapped in React.memo for render skipping - only re-renders when
 * selection/hover/drag state actually changes for this component.
 */

import { memo, useMemo } from 'react';
import { Line, RoundedBox, Text } from '@react-three/drei';
import type {
  SchematicComponent,
  SchematicPin,
  SchematicSymbolFamily,
} from '../types/schematic';
import type { KicadArc } from '../types/symbol';
import {
  getComponentGridAlignmentOffset,
  getNormalizedComponentPinGeometry,
} from '../types/schematic';
import type { ThemeColors } from '../lib/theme';
import { getCanonicalKicadSymbol } from '../symbol-catalog/canonicalSymbolCatalog';
import { getKicadTemplateSymbol } from '../parsers/kicadSymbolTemplates';
import { anchorFromVisualSide, getUprightTextTransform } from '../lib/itemTransform';
import { getConnectionColor } from './connectionColor';

const SMALL_AREA = 40;
const NO_RAYCAST = () => {};

function getDesignatorPrefix(designator: string): string {
  return designator.replace(/[^A-Za-z]/g, '').toUpperCase();
}

function inferSymbolFamily(component: SchematicComponent): SchematicSymbolFamily | null {
  // Connectors stay on the generic box renderer for now.
  if (component.symbolFamily === 'connector') return null;
  if (component.symbolFamily) return component.symbolFamily;

  const designatorPrefix = getDesignatorPrefix(component.designator);
  const haystack = `${component.name} ${designatorPrefix} ${component.reference}`.toLowerCase();

  if (haystack.includes('led')) return 'led';
  if (haystack.includes('testpoint') || designatorPrefix.startsWith('TP')) return 'testpoint';

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

function chipScale(packageCode?: string): number {
  const code = (packageCode ?? '').toUpperCase();
  if (!code) return 1;
  if (['01005', '0201', '0402'].includes(code)) return 0.82;
  if (['1206', '1210', '2010', '2512'].includes(code)) return 1.16;
  if (code.startsWith('SOD-') || code.startsWith('SOT-')) return 0.92;
  return 1;
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

interface SymbolGlyphProps {
  component: SchematicComponent;
  family: SchematicSymbolFamily;
  color: string;
}

function symbolScaleFactors(family: SchematicSymbolFamily): { width: number; height: number } {
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
    case 'testpoint':
      return { width: 0.74, height: 1.02 };
    case 'connector':
      return { width: 0.9, height: 0.9 };
    default:
      return { width: 0.88, height: 0.9 };
  }
}

function SymbolGlyph({ component, family, color }: SymbolGlyphProps) {
  const W = component.bodyWidth;
  const H = component.bodyHeight;
  const scale = chipScale(component.packageCode);
  const lineColor = color;
  const lineWidth = 2.2;
  const templateSymbol = getCanonicalKicadSymbol(family, component.pins.length)
    ?? getKicadTemplateSymbol(family, component.pins.length);

  if (
    templateSymbol
    && templateSymbol.bodyBounds.width > 1e-6
    && templateSymbol.bodyBounds.height > 1e-6
  ) {
    const bounds = templateSymbol.bodyBounds;
    const cx = (bounds.minX + bounds.maxX) * 0.5;
    const cy = (bounds.minY + bounds.maxY) * 0.5;
    const rotateToHorizontal =
      family !== 'connector'
      && family !== 'testpoint'
      && bounds.height > bounds.width;
    const effectiveW = rotateToHorizontal ? bounds.height : bounds.width;
    const effectiveH = rotateToHorizontal ? bounds.width : bounds.height;
    const factors = symbolScaleFactors(family);
    const targetW = Math.max(0.7, W * factors.width * scale);
    const targetH = Math.max(0.55, H * factors.height);
    const sx = targetW / Math.max(effectiveW, 1e-6);
    const sy = targetH / Math.max(effectiveH, 1e-6);
    const unit = Math.min(sx, sy);
    const rotatePoint = (x: number, y: number): [number, number] => {
      const dx = x - cx;
      const dy = y - cy;
      return rotateToHorizontal ? [dy, -dx] : [dx, dy];
    };
    const pt = (x: number, y: number): [number, number, number] => {
      const [rx, ry] = rotatePoint(x, y);
      return [rx * unit, ry * unit, 0];
    };

    return (
      <group raycast={NO_RAYCAST}>
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
            raycast={NO_RAYCAST}
          />
        ))}

        {templateSymbol.polylines.map((poly, idx) => (
          <Line
            key={`poly-${idx}`}
            points={poly.points.map((p) => pt(p.x, p.y))}
            color={lineColor}
            lineWidth={lineWidth}
            raycast={NO_RAYCAST}
          />
        ))}

        {templateSymbol.circles.map((circle, idx) => {
          const [rx, ry] = rotatePoint(circle.centerX, circle.centerY);
          return (
            <Line
              key={`circle-${idx}`}
              points={circlePoints(
                rx * unit,
                ry * unit,
                circle.radius * unit,
                24,
              )}
              color={lineColor}
              lineWidth={lineWidth}
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
        raycast={NO_RAYCAST}
      />
    );
  }

  if (family === 'capacitor' || family === 'capacitor_polarized') {
    const plateGap = Math.max(0.18, W * 0.12 * scale);
    const halfPlate = Math.max(0.34, H * 0.36);
    return (
      <group raycast={NO_RAYCAST}>
        <Line
          points={[
            [-plateGap, -halfPlate, 0],
            [-plateGap, halfPlate, 0],
          ]}
          color={lineColor}
          lineWidth={lineWidth}
          raycast={NO_RAYCAST}
        />
        <Line
          points={[
            [plateGap, -halfPlate, 0],
            [plateGap, halfPlate, 0],
          ]}
          color={lineColor}
          lineWidth={lineWidth}
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
              lineWidth={1.9}
              raycast={NO_RAYCAST}
            />
            <Line
              points={[
                [-plateGap - 0.22, 0.08, 0],
                [-plateGap - 0.22, 0.28, 0],
              ]}
              color={lineColor}
              lineWidth={1.9}
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
        raycast={NO_RAYCAST}
      />
    );
  }

  if (family === 'diode' || family === 'led') {
    const left = -Math.max(0.9, W * 0.2);
    const barX = Math.max(0.8, W * 0.2);
    const halfY = Math.max(0.32, H * 0.3);

    return (
      <group raycast={NO_RAYCAST}>
        <Line
          points={[
            [left, -halfY, 0],
            [left, halfY, 0],
            [barX, 0, 0],
            [left, -halfY, 0],
          ]}
          color={lineColor}
          lineWidth={lineWidth}
          raycast={NO_RAYCAST}
        />
        <Line
          points={[
            [barX, -halfY, 0],
            [barX, halfY, 0],
          ]}
          color={lineColor}
          lineWidth={lineWidth}
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
              lineWidth={1.8}
              raycast={NO_RAYCAST}
            />
            <Line
              points={[
                [barX + 0.42, halfY + 0.63, 0],
                [barX + 0.62, halfY + 0.62, 0],
                [barX + 0.57, halfY + 0.42, 0],
              ]}
              color={lineColor}
              lineWidth={1.7}
              raycast={NO_RAYCAST}
            />
            <Line
              points={[
                [barX - 0.3, -halfY * 0.06, 0],
                [barX + 0.45, halfY + 0.34, 0],
              ]}
              color={lineColor}
              lineWidth={1.8}
              raycast={NO_RAYCAST}
            />
            <Line
              points={[
                [barX + 0.25, halfY + 0.35, 0],
                [barX + 0.45, halfY + 0.34, 0],
                [barX + 0.4, halfY + 0.14, 0],
              ]}
              color={lineColor}
              lineWidth={1.7}
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
          raycast={NO_RAYCAST}
        />
        <Line
          points={[
            [0, -radius + 0.08, 0],
            [0, -radius - 0.56, 0],
          ]}
          color={lineColor}
          lineWidth={lineWidth}
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
            <group position={[0, 0.05, 0.001]} raycast={NO_RAYCAST}>
              <SymbolGlyph
                component={component}
                family={symbolFamily}
                color={accent}
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

      {component.pins.map((pin) => (
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
}) {
  const color = getConnectionColor(pin.category, theme);
  const isNetHighlighted = netId !== null && netId === selectedNetId;
  const isDimmed = selectedNetId !== null && !isNetHighlighted;
  const showName = pin.name !== pin.number;
  const DOT_RADIUS = 0.15;
  const pinOpacity = isNetHighlighted ? 1 : isDimmed ? 0.25 : 0.8;
  const pinGeom = useMemo(
    () => getNormalizedComponentPinGeometry(component, pin),
    [component, pin],
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
        lineWidth={isNetHighlighted ? 2.5 : 1.8}
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
