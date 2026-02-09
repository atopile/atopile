/**
 * ModuleBlock — renders a SchematicModule as a styled expandable box.
 *
 * Visually distinct from components:
 * - Dashed border + subtle gradient background
 * - Shows module type name, instance name, and component count badge
 * - Interface pins shown as color-coded stubs
 * - Double-click to "enter" the module (navigate into its sheet)
 * - Shares the same drag architecture as DraggableComponent
 */

import { useMemo, memo } from 'react';
import { Text, RoundedBox, Line } from '@react-three/drei';
import type { SchematicModule, SchematicInterfacePin } from '../types/schematic';
import { getModuleGridAlignmentOffset } from '../types/schematic';
import type { ThemeColors } from '../lib/theme';
import { getPinColor } from '../lib/theme';
import {
  getUprightTextTransform,
  anchorFromVisualSide,
} from '../lib/itemTransform';

const NO_RAYCAST = () => { };

function moduleAccentColor(typeName: string): string {
  const t = typeName.toLowerCase();
  if (/power|ldo|buck|boost|regulator/i.test(t)) return '#f38ba8';
  if (/mcu|esp|stm|rp2|cortex|cpu/i.test(t)) return '#89b4fa';
  if (/sensor|bme|bmp|lis|mpu|accel/i.test(t)) return '#a6e3a1';
  if (/led|light|display/i.test(t)) return '#f9e2af';
  if (/usb|conn|jack/i.test(t)) return '#94e2d5';
  if (/i2c|spi|uart|bus/i.test(t)) return '#cba6f7';
  return '#89b4fa';
}

// ── Public component ───────────────────────────────────────────

interface Props {
  module: SchematicModule;
  theme: ThemeColors;
  isSelected: boolean;
  isHovered: boolean;
  isDragging: boolean;
  selectedNetId: string | null;
  netsForModule: Map<string, string>;
  rotation?: number;
  mirrorX?: boolean;
  mirrorY?: boolean;
}

export const ModuleBlock = memo(function ModuleBlock({
  module,
  theme,
  isSelected,
  isHovered,
  isDragging,
  selectedNetId,
  netsForModule,
  rotation = 0,
  mirrorX = false,
  mirrorY = false,
}: Props) {
  const W = module.bodyWidth;
  const H = module.bodyHeight;
  const accent = useMemo(
    () => moduleAccentColor(module.typeName),
    [module.typeName],
  );

  const RADIUS = Math.min(W, H) * 0.06;
  const maxDim = Math.min(W, H);
  const typeFontSize = Math.min(1.8, Math.max(0.8, maxDim * 0.12));
  const nameFontSize = typeFontSize * 0.65;
  const maxTextWidth = W * 0.65;
  const zOffset = isDragging ? 0.5 : 0;
  const gridOffset = useMemo(
    () => getModuleGridAlignmentOffset(module),
    [module],
  );

  const textTf = useMemo(
    () => getUprightTextTransform(rotation, mirrorX, mirrorY),
    [rotation, mirrorX, mirrorY],
  );

  return (
    <group position={[gridOffset.x, gridOffset.y, zOffset]} raycast={NO_RAYCAST}>
      {/* ── Selection highlight ─────────────────────── */}
      {isSelected && (
        <RoundedBox
          args={[W + 1.2, H + 1.2, 0.001]}
          radius={RADIUS + 0.2}
          smoothness={4}
          position={[0, 0, -0.004]}
          raycast={NO_RAYCAST}
        >
          <meshBasicMaterial color={accent} transparent opacity={0.2} />
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
          <meshBasicMaterial color={accent} transparent opacity={0.1} />
        </RoundedBox>
      )}

      {/* ── Border ──────────────────────────────────── */}
      <RoundedBox
        args={[W + 0.2, H + 0.2, 0.001]}
        radius={RADIUS + 0.03}
        smoothness={4}
        position={[0, 0, -0.003]}
        raycast={NO_RAYCAST}
      >
        <meshBasicMaterial
          color={isSelected ? accent : theme.borderColor}
          transparent
          opacity={0.6}
        />
      </RoundedBox>

      {/* ── Module body — subtle fill distinct from components ─ */}
      <RoundedBox args={[W, H, 0.001]} radius={RADIUS} smoothness={4} position={[0, 0, -0.002]}>
        <meshBasicMaterial color={theme.bgTertiary} />
      </RoundedBox>

      {/* ── Accent stripe at top ────────────────────── */}
      <mesh position={[0, H / 2 - 0.4, -0.001]} raycast={NO_RAYCAST}>
        <planeGeometry args={[W - 1, 0.8]} />
        <meshBasicMaterial color={accent} transparent opacity={0.35} />
      </mesh>

      {/* ── Labels (counter-rotated for readability) ── */}
      <group position={[0, 0, 0.001]} rotation={[0, 0, textTf.rotationZ]} scale={[textTf.scaleX, textTf.scaleY, 1]}>
        {/* Type name (bold, colored) */}
        <Text
          position={[0, typeFontSize * 0.5, 0]}
          fontSize={typeFontSize}
          color={accent}
          anchorX="center"
          anchorY="middle"
          letterSpacing={0.02}
          maxWidth={maxTextWidth}
          font={undefined}
          raycast={NO_RAYCAST}
        >
          {module.typeName}
        </Text>

        {/* Instance name */}
        <Text
          position={[0, -nameFontSize * 0.6, 0]}
          fontSize={nameFontSize}
          color={theme.textSecondary}
          anchorX="center"
          anchorY="middle"
          maxWidth={maxTextWidth}
          font={undefined}
          raycast={NO_RAYCAST}
        >
          {module.name}
        </Text>
      </group>

      {/* ── Component count badge (counter-rotated) ── */}
      <group position={[W / 2 - 2, -H / 2 + 1.2, 0.001]} rotation={[0, 0, textTf.rotationZ]} scale={[textTf.scaleX, textTf.scaleY, 1]}>
        <mesh raycast={NO_RAYCAST}>
          <planeGeometry args={[3.5, 1.4]} />
          <meshBasicMaterial color={accent} transparent opacity={0.15} />
        </mesh>
        <Text
          position={[0, 0, 0.001]}
          fontSize={0.7}
          color={theme.textMuted}
          anchorX="center"
          anchorY="middle"
          font={undefined}
          raycast={NO_RAYCAST}
        >
          {`${module.componentCount} parts`}
        </Text>
      </group>

      {/* ── Expand hint icon (counter-rotated) ───────── */}
      <group position={[-W / 2 + 1.5, -H / 2 + 1.2, 0.001]} rotation={[0, 0, textTf.rotationZ]} scale={[textTf.scaleX, textTf.scaleY, 1]}>
        <Text
          fontSize={0.9}
          color={theme.textMuted}
          anchorX="center"
          anchorY="middle"
          font={undefined}
          raycast={NO_RAYCAST}
        >
          {'>>'}
        </Text>
      </group>

      {/* ── Interface pins ───────────────────────────── */}
      {module.interfacePins.map((pin) => (
        <InterfacePinElement
          key={pin.id}
          pin={pin}
          theme={theme}
          netId={netsForModule.get(pin.id) ?? null}
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

// ── Interface pin element ──────────────────────────────────────

const InterfacePinElement = memo(function InterfacePinElement({
  pin,
  theme,
  netId,
  selectedNetId,
  textRotationZ = 0,
  textScaleX = 1,
  textScaleY = 1,
  rotationDeg = 0,
  mirrorX = false,
  mirrorY = false,
}: {
  pin: SchematicInterfacePin;
  theme: ThemeColors;
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
  const isHighlighted = netId !== null && netId === selectedNetId;
  const DOT_RADIUS = 0.35;
  const pinX = pin.x;
  const pinY = pin.y;
  const bodyX = pin.bodyX;
  const bodyY = pin.bodyY;

  // Text placement
  let nameX: number, nameY: number;
  const NAME_INSET = 0.8;

  if (pin.side === 'left') {
    nameX = bodyX + NAME_INSET;
    nameY = pinY;
  } else if (pin.side === 'right') {
    nameX = bodyX - NAME_INSET;
    nameY = pinY;
  } else if (pin.side === 'top') {
    nameX = pinX;
    nameY = bodyY - NAME_INSET;
  } else {
    nameX = pinX;
    nameY = bodyY + NAME_INSET;
  }
  const effectiveNameAnchorX = anchorFromVisualSide(pin.side, {
    rotationDeg,
    mirrorX,
    mirrorY,
    left: 'left',
    right: 'right',
    vertical: 'center',
  });

  const lineColor = isHighlighted ? theme.accent : color;

  return (
    <group raycast={NO_RAYCAST}>
      {/* Stub line */}
      <Line
        points={[
          [pinX, pinY, 0],
          [bodyX, bodyY, 0],
        ]}
        color={lineColor}
        lineWidth={isHighlighted ? 2.5 : 1.8}
        raycast={NO_RAYCAST}
      />

      {/* Connection dot */}
      <mesh position={[pinX, pinY, 0.001]} raycast={NO_RAYCAST}>
        <circleGeometry args={[DOT_RADIUS, 16]} />
        <meshBasicMaterial color={lineColor} />
      </mesh>

      {/* Pin name (counter-rotated for readability) */}
      <group position={[nameX, nameY, 0.002]} rotation={[0, 0, textRotationZ]} scale={[textScaleX, textScaleY, 1]}>
        <Text
          fontSize={1.0}
          color={theme.textSecondary}
          anchorX={effectiveNameAnchorX}
          anchorY="middle"
          font={undefined}
          raycast={NO_RAYCAST}
        >
          {pin.name}
        </Text>
      </group>
    </group>
  );
});
