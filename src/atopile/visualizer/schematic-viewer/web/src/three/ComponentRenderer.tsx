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
import type { ThemeColors } from '../lib/theme';
import { getPinColor } from '../lib/theme';

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

  // Counter-transform for text readability when component is rotated/mirrored
  const counterRot = -(rotation * Math.PI) / 180;
  const counterScaleX = mirrorX ? -1 : 1;
  const counterScaleY = mirrorY ? -1 : 1;

  const RADIUS = Math.min(W, H) * 0.08;
  const maxDim = Math.min(W, H);
  const nameFontSize = Math.min(2.0, Math.max(0.7, maxDim * 0.14));
  const refFontSize = nameFontSize * 0.5;
  const maxTextWidth = W * 0.55;

  // Slight visual lift when dragging
  const zOffset = isDragging ? 0.5 : 0;

  return (
    <group position={[0, 0, zOffset]} raycast={NO_RAYCAST}>
      {/* ── Selection highlight ─────────────────────── */}
      {isSelected && (
        <RoundedBox
          args={[W + 1.2, H + 1.2, 0.001]}
          radius={RADIUS + 0.2}
          smoothness={4}
          position={[0, 0, -0.004]}
          raycast={NO_RAYCAST}
        >
          <meshBasicMaterial color={accent} transparent opacity={0.18} />
        </RoundedBox>
      )}

      {/* ── Hover highlight ─────────────────────────── */}
      {isHovered && !isSelected && (
        <RoundedBox
          args={[W + 0.6, H + 0.6, 0.001]}
          radius={RADIUS + 0.08}
          smoothness={4}
          position={[0, 0, -0.004]}
          raycast={NO_RAYCAST}
        >
          <meshBasicMaterial color={accent} transparent opacity={0.08} />
        </RoundedBox>
      )}

      {/* ── Outer glow / accent ring ────────────────── */}
      <RoundedBox
        args={[W + 0.3, H + 0.3, 0.001]}
        radius={RADIUS + 0.05}
        smoothness={4}
        position={[0, 0, -0.003]}
        raycast={NO_RAYCAST}
      >
        <meshBasicMaterial color={accent} transparent opacity={0.1} />
      </RoundedBox>

      {/* ── Border ──────────────────────────────────── */}
      <RoundedBox
        args={[W + 0.12, H + 0.12, 0.001]}
        radius={RADIUS + 0.02}
        smoothness={4}
        position={[0, 0, -0.002]}
        raycast={NO_RAYCAST}
      >
        <meshBasicMaterial
          color={isSelected ? accent : theme.bodyBorder}
        />
      </RoundedBox>

      {/* ── Body fill ───────────────────────────────── */}
      <RoundedBox args={[W, H, 0.001]} radius={RADIUS} smoothness={4} position={[0, 0, -0.001]}>
        <meshBasicMaterial color={theme.bodyFill} />
      </RoundedBox>

      {/* ── Center label (counter-rotated for readability) ── */}
      {isSmall ? (
        <group position={[0, 0, 0.001]} rotation={[0, 0, counterRot]} scale={[counterScaleX, counterScaleY, 1]}>
          <Text
            fontSize={Math.min(1.4, Math.max(0.6, maxDim * 0.35))}
            color={accent}
            anchorX="center"
            anchorY="middle"
            letterSpacing={0.04}
            font={undefined}
            raycast={NO_RAYCAST}
          >
            {component.reference}
          </Text>
        </group>
      ) : (
        <group position={[0, 0, 0.001]} rotation={[0, 0, counterRot]} scale={[counterScaleX, counterScaleY, 1]}>
          <Text
            position={[0, nameFontSize * 0.7, 0]}
            fontSize={refFontSize}
            color={accent}
            anchorX="center"
            anchorY="middle"
            letterSpacing={0.08}
            maxWidth={maxTextWidth}
            font={undefined}
            raycast={NO_RAYCAST}
          >
            {component.designator}
          </Text>
          <Text
            position={[0, -nameFontSize * 0.2, 0]}
            fontSize={nameFontSize}
            color={theme.textPrimary}
            anchorX="center"
            anchorY="middle"
            maxWidth={maxTextWidth}
            font={undefined}
            raycast={NO_RAYCAST}
          >
            {component.name}
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
          pin={pin}
          theme={theme}
          isSmall={isSmall}
          netId={netsForComponent.get(pin.number) ?? null}
          selectedNetId={selectedNetId}
          counterRot={counterRot}
          counterScaleX={counterScaleX}
          counterScaleY={counterScaleY}
        />
      ))}
    </group>
  );
});

// ── Individual pin (also memoized) ─────────────────────────────

const SchematicPinElement = memo(function SchematicPinElement({
  pin,
  theme,
  isSmall,
  netId,
  selectedNetId,
  counterRot = 0,
  counterScaleX = 1,
  counterScaleY = 1,
}: {
  pin: SchematicPin;
  theme: ThemeColors;
  isSmall: boolean;
  netId: string | null;
  selectedNetId: string | null;
  counterRot?: number;
  counterScaleX?: number;
  counterScaleY?: number;
}) {
  const color = getPinColor(pin.category, theme);
  const isNetHighlighted = netId !== null && netId === selectedNetId;
  const showName = pin.name !== pin.number;
  const DOT_RADIUS = 0.3;

  // Text placement
  let nameX: number, nameY: number;
  let numX: number, numY: number;
  let nameAnchorX: 'left' | 'right' | 'center' = 'left';
  const NAME_INSET = 0.8;
  const NUM_OFFSET = 0.6;

  if (pin.side === 'left') {
    nameX = pin.bodyX + NAME_INSET;
    nameY = pin.y;
    nameAnchorX = 'left';
    numX = pin.x;
    numY = pin.y + NUM_OFFSET;
  } else if (pin.side === 'right') {
    nameX = pin.bodyX - NAME_INSET;
    nameY = pin.y;
    nameAnchorX = 'right';
    numX = pin.x;
    numY = pin.y + NUM_OFFSET;
  } else if (pin.side === 'top') {
    nameX = pin.x;
    nameY = pin.bodyY - NAME_INSET;
    nameAnchorX = 'center';
    numX = pin.x + NUM_OFFSET;
    numY = pin.y;
  } else {
    nameX = pin.x;
    nameY = pin.bodyY + NAME_INSET;
    nameAnchorX = 'center';
    numX = pin.x + NUM_OFFSET;
    numY = pin.y;
  }

  const lineColor = isNetHighlighted ? theme.accent : color;

  return (
    <group raycast={NO_RAYCAST}>
      {/* Stub line */}
      <Line
        points={[
          [pin.x, pin.y, 0],
          [pin.bodyX, pin.bodyY, 0],
        ]}
        color={lineColor}
        lineWidth={isNetHighlighted ? 2.5 : 1.8}
        raycast={NO_RAYCAST}
      />

      {/* Connection dot */}
      <mesh position={[pin.x, pin.y, 0.001]} raycast={NO_RAYCAST}>
        <circleGeometry args={[DOT_RADIUS, 16]} />
        <meshBasicMaterial color={lineColor} />
      </mesh>

      {/* Pin name (inside body edge) — counter-rotated for readability */}
      {showName && !isSmall && (
        <group position={[nameX, nameY, 0.002]} rotation={[0, 0, counterRot]} scale={[counterScaleX, counterScaleY, 1]}>
          <Text
            fontSize={1.05}
            color={theme.textSecondary}
            anchorX={nameAnchorX}
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
        <group position={[numX, numY, 0.002]} rotation={[0, 0, counterRot]} scale={[counterScaleX, counterScaleY, 1]}>
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
