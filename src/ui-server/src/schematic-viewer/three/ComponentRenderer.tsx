/**
 * ComponentRenderer — draws a SchematicComponent body + pins.
 *
 * Wrapped in React.memo for render skipping — only re-renders when
 * selection/hover/drag state actually changes for THIS component.
 *
 * All child meshes use raycast={NO_RAYCAST} because interaction is
 * handled by the parent DraggableComponent group. This avoids r3f's
 * per-frame raycasting overhead on dozens of sub-meshes per component.
 */

import { useMemo, memo } from 'react';
import { Text, RoundedBox, Line } from '@react-three/drei';
import type { SchematicComponent, SchematicPin } from '../types/schematic';
import {
  getComponentGridAlignmentOffset,
  getNormalizedComponentPinGeometry,
} from '../types/schematic';
import type { ThemeColors } from '../lib/theme';
import { getPinColor } from '../lib/theme';
import {
  getUprightTextTransform,
  anchorFromVisualSide,
} from '../lib/itemTransform';

const SMALL_AREA = 40;
const NO_RAYCAST = () => {};

function accentColorFor(reference: string): string {
  const r = reference.toUpperCase();
  if (r.startsWith('U')) return '#89b4fa';
  if (r.startsWith('R')) return '#cba6f7';
  if (r.startsWith('C')) return '#f9e2af';
  if (r.startsWith('L')) return '#94e2d5';
  if (r.startsWith('D')) return '#f38ba8';
  if (r.startsWith('Q')) return '#fab387';
  if (r.startsWith('J') || r.startsWith('P')) return '#a6e3a1';
  return '#7f849c';
}

// ── Public component ───────────────────────────────────────────

interface Props {
  component: SchematicComponent;
  theme: ThemeColors;
  isSelected: boolean;
  isHovered: boolean;
  isDragging: boolean;
  selectedNetId: string | null;
  netsForComponent: Map<string, string>; // pinNumber → netId
  /** Degrees CCW — used to counter-rotate text so it stays readable */
  rotation?: number;
  /** Mirror state — used to counter-scale text */
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
  const accent = useMemo(
    () => accentColorFor(component.reference),
    [component.reference],
  );

  // Shared label policy: keep text upright for any rotate/mirror combination.
  const textTf = useMemo(
    () => getUprightTextTransform(rotation, mirrorX, mirrorY),
    [rotation, mirrorX, mirrorY],
  );

  const RADIUS = Math.min(W, H) * 0.08;
  const maxDim = Math.min(W, H);
  const refFontSize = isSmall
    ? Math.min(1.35, Math.max(0.62, maxDim * 0.34))
    : Math.min(1.35, Math.max(0.78, maxDim * 0.18));
  const bodyRefMaxWidth = W * 0.84;

  const showNameBadge = (isHovered || isSelected) && component.name.trim().length > 0;
  const nameBadgeWidth = Math.min(Math.max(W * 0.95, 10), 28);
  const nameBadgeHeight = 1.9;
  const nameBadgeRadius = 0.34;
  const nameBadgeFontSize = 0.72;
  const displayName = useMemo(() => {
    const raw = component.name.trim();
    if (!raw) return '';
    const maxChars = Math.max(
      10,
      Math.floor(nameBadgeWidth / (nameBadgeFontSize * 0.55)),
    );
    if (raw.length <= maxChars) return raw;
    return raw.slice(0, Math.max(1, maxChars - 1)) + '\u2026';
  }, [component.name, nameBadgeWidth, nameBadgeFontSize]);

  // Slight visual lift when dragging
  const zOffset = isDragging ? 0.5 : 0;
  const gridOffset = useMemo(
    () => getComponentGridAlignmentOffset(component),
    [component],
  );

  return (
    <group position={[gridOffset.x, gridOffset.y, zOffset]} raycast={NO_RAYCAST}>
      {/* ── Selection highlight ─────────────────────── */}
      {isSelected && (
        <RoundedBox
          args={[W + 1.2, H + 1.2, 0.001]}
          radius={RADIUS + 0.2}
          smoothness={4}
          position={[0, 0, -0.06]}
          raycast={NO_RAYCAST}
        >
          <meshBasicMaterial color={accent} transparent opacity={0.18} depthWrite={false} />
        </RoundedBox>
      )}

      {/* ── Hover highlight ─────────────────────────── */}
      {isHovered && !isSelected && (
        <RoundedBox
          args={[W + 0.6, H + 0.6, 0.001]}
          radius={RADIUS + 0.08}
          smoothness={4}
          position={[0, 0, -0.06]}
          raycast={NO_RAYCAST}
        >
          <meshBasicMaterial color={accent} transparent opacity={0.08} depthWrite={false} />
        </RoundedBox>
      )}

      {/* ── Border ──────────────────────────────────── */}
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

      {/* ── Body fill ───────────────────────────────── */}
      <RoundedBox args={[W, H, 0.001]} radius={RADIUS} smoothness={4} position={[0, 0, -0.02]}>
        <meshBasicMaterial color={theme.bodyFill} depthWrite={false} />
      </RoundedBox>

      {/* ── Center label (counter-rotated for readability) ── */}
      <group position={[0, 0, 0.001]} rotation={[0, 0, textTf.rotationZ]} scale={[textTf.scaleX, textTf.scaleY, 1]}>
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

      {/* ── Part name badge (hover/selected) ────────── */}
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

      {/* ── Pin-1 dot ───────────────────────────────── */}
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

      {/* ── Pins ────────────────────────────────────── */}
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

// ── Individual pin (also memoized) ─────────────────────────────

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
  const color = getPinColor(pin.category, theme);
  const isNetHighlighted = netId !== null && netId === selectedNetId;
  const isDimmed = selectedNetId !== null && !isNetHighlighted;
  const showName = pin.name !== pin.number;
  const DOT_RADIUS = 0.3;
  const pinOpacity = isNetHighlighted ? 1 : isDimmed ? 0.25 : 0.8;
  const pinGeom = useMemo(
    () => getNormalizedComponentPinGeometry(component, pin),
    [component, pin],
  );
  const pinX = pinGeom.x;
  const pinY = pinGeom.y;
  const bodyX = pinGeom.bodyX;
  const bodyY = pinGeom.bodyY;

  // Text placement
  let nameX: number, nameY: number;
  let numX: number, numY: number;
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
      {/* Stub line */}
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

      {/* Connection dot */}
      <mesh position={[pinX, pinY, 0.001]} raycast={NO_RAYCAST}>
        <circleGeometry args={[DOT_RADIUS, 16]} />
        <meshBasicMaterial color={color} transparent opacity={pinOpacity} />
      </mesh>

      {/* Pin name (inside body edge) — counter-rotated for readability */}
      {showName && !isSmall && (
        <group position={[nameX, nameY, 0.002]} rotation={[0, 0, textRotationZ]} scale={[textScaleX, textScaleY, 1]}>
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

      {/* Pin number (near endpoint) — counter-rotated for readability */}
      {!isSmall && (
        <group position={[numX, numY, 0.002]} rotation={[0, 0, textRotationZ]} scale={[textScaleX, textScaleY, 1]}>
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
