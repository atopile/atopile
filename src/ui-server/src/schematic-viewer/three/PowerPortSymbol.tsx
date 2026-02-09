/**
 * PowerPortSymbol — renders a small power rail bar or ground symbol.
 *
 * Power:    ───────
 *              |       + net name above bar
 *
 * Ground:     |
 *           ───────
 *            ─────
 *             ───
 */

import { memo } from 'react';
import { Text, Line } from '@react-three/drei';
import type { SchematicPowerPort } from '../types/schematic';
import { POWER_PORT_W, getPowerPortGridAlignmentOffset } from '../types/schematic';
import type { ThemeColors } from '../lib/theme';
import { getUprightTextTransform } from '../lib/itemTransform';

const NO_RAYCAST = () => {};
const BAR_HALF = POWER_PORT_W / 2;
const POWER_LABEL_MAX_CHARS = 14;

interface Props {
  powerPort: SchematicPowerPort;
  theme: ThemeColors;
  isSelected: boolean;
  isHovered: boolean;
  isDragging: boolean;
  selectedNetId: string | null;
  rotation?: number;
  mirrorX?: boolean;
  mirrorY?: boolean;
}

export const PowerPortSymbol = memo(function PowerPortSymbol({
  powerPort,
  theme,
  isSelected,
  isHovered,
  isDragging,
  selectedNetId,
  rotation = 0,
  mirrorX = false,
  mirrorY = false,
}: Props) {
  const zOffset = isDragging ? 0.5 : 0;
  const isPower = powerPort.type === 'power';
  const isNetSelected = selectedNetId === powerPort.netId;
  const color = isPower ? theme.pinPower : theme.pinGround;
  const fillOpacity = isSelected || isNetSelected ? 0.4 : isHovered ? 0.3 : 0;
  const pinX = powerPort.pinX;
  const pinY = powerPort.pinY;
  const gridOffset = getPowerPortGridAlignmentOffset(powerPort);
  const textTf = getUprightTextTransform(rotation, mirrorX, mirrorY);

  // Hit target for pointer events
  const hitW = POWER_PORT_W + 2;
  const hitH = 3;

  return (
    <group position={[gridOffset.x, gridOffset.y, zOffset]}>
      {/* ── Invisible hit target ── */}
      <mesh position={[0, 0, -0.005]}>
        <planeGeometry args={[hitW, hitH]} />
        <meshBasicMaterial transparent opacity={0} depthWrite={false} />
      </mesh>

      {/* ── Selection highlight ── */}
      {(isSelected || isHovered || isNetSelected) && (
        <mesh position={[0, 0, -0.003]} raycast={NO_RAYCAST}>
          <planeGeometry args={[hitW, hitH]} />
          <meshBasicMaterial color={color} transparent opacity={fillOpacity} />
        </mesh>
      )}

      <group raycast={NO_RAYCAST}>
        {isPower ? (
          <PowerBarGlyph
            color={color}
            name={powerPort.name}
            showFullName={isSelected || isNetSelected}
            textTf={textTf}
          />
        ) : (
          <GroundGlyph color={color} />
        )}
      </group>

      {/* ── Connection dot at pin point ── */}
      <mesh position={[pinX, pinY, 0.01]} raycast={NO_RAYCAST}>
        <circleGeometry args={[0.25, 10]} />
        <meshBasicMaterial color={color} />
      </mesh>
    </group>
  );
});

// ── Power bar glyph ─────────────────────────────────────────────
//
//     VCC
//   ───────
//      |

function PowerBarGlyph({
  color,
  name,
  showFullName,
  textTf,
}: {
  color: string;
  name: string;
  showFullName: boolean;
  textTf: { rotationZ: number; scaleX: number; scaleY: number };
}) {
  const compactName = truncateLabel(name, POWER_LABEL_MAX_CHARS);
  const displayName = showFullName ? name : compactName;
  return (
    <group raycast={NO_RAYCAST}>
      {/* Horizontal bar at top */}
      <Line
        points={[[-BAR_HALF, 0.4, 0], [BAR_HALF, 0.4, 0]]}
        color={color}
        lineWidth={2.2}
        raycast={NO_RAYCAST}
      />
      {/* Vertical stem from bar down to pin */}
      <Line
        points={[[0, 0.4, 0], [0, -0.6, 0]]}
        color={color}
        lineWidth={1.5}
        raycast={NO_RAYCAST}
      />
      {/* Net name above bar */}
      <group
        position={[0, 0.5, 0.01]}
        rotation={[0, 0, textTf.rotationZ]}
        scale={[textTf.scaleX, textTf.scaleY, 1]}
      >
        <Text
          fontSize={showFullName ? 0.54 : 0.5}
          color={color}
          anchorX="center"
          anchorY="bottom"
          maxWidth={showFullName ? 12 : 8}
          overflowWrap="normal"
          textAlign="center"
          font={undefined}
          raycast={NO_RAYCAST}
        >
          {displayName}
        </Text>
      </group>
    </group>
  );
}

function truncateLabel(label: string, maxChars: number): string {
  if (label.length <= maxChars) return label;
  return `${label.slice(0, Math.max(1, maxChars - 1))}…`;
}

// ── Ground glyph ────────────────────────────────────────────────
//
//      |
//   ───────
//    ─────
//     ───

function GroundGlyph({ color }: { color: string }) {
  const WIDTHS = [BAR_HALF, BAR_HALF * 0.6, BAR_HALF * 0.25];
  const GAP = 0.4;

  return (
    <group raycast={NO_RAYCAST}>
      {/* Vertical stem from pin down to bars */}
      <Line
        points={[[0, 0.6, 0], [0, -0.1, 0]]}
        color={color}
        lineWidth={1.5}
        raycast={NO_RAYCAST}
      />
      {/* Three horizontal bars getting smaller */}
      {WIDTHS.map((hw, i) => (
        <Line
          key={i}
          points={[[-hw, -0.1 - i * GAP, 0], [hw, -0.1 - i * GAP, 0]]}
          color={color}
          lineWidth={i === 0 ? 2.2 : 1.5}
          raycast={NO_RAYCAST}
        />
      ))}
    </group>
  );
}
