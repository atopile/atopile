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
import { POWER_PORT_W } from '../types/schematic';
import type { ThemeColors } from '../lib/theme';

const NO_RAYCAST = () => {};
const BAR_HALF = POWER_PORT_W / 2;

interface Props {
  powerPort: SchematicPowerPort;
  theme: ThemeColors;
  isSelected: boolean;
  isHovered: boolean;
  isDragging: boolean;
  selectedNetId: string | null;
}

export const PowerPortSymbol = memo(function PowerPortSymbol({
  powerPort,
  theme,
  isSelected,
  isHovered,
  isDragging,
  selectedNetId,
}: Props) {
  const zOffset = isDragging ? 0.5 : 0;
  const isPower = powerPort.type === 'power';
  const isNetSelected = selectedNetId === powerPort.netId;
  const color = isPower ? theme.pinPower : theme.pinGround;
  const fillOpacity = isSelected || isNetSelected ? 0.4 : isHovered ? 0.3 : 0;

  // Hit target for pointer events
  const hitW = POWER_PORT_W + 2;
  const hitH = 3;

  return (
    <group position={[0, 0, zOffset]}>
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

      {isPower ? (
        <PowerBarGlyph color={color} name={powerPort.name} theme={theme} />
      ) : (
        <GroundGlyph color={color} />
      )}

      {/* ── Connection dot at pin point ── */}
      <mesh position={[powerPort.pinX, powerPort.pinY, 0.01]} raycast={NO_RAYCAST}>
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
  theme,
}: {
  color: string;
  name: string;
  theme: ThemeColors;
}) {
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
      <Text
        position={[0, 1.1, 0.01]}
        fontSize={0.7}
        color={theme.textPrimary}
        anchorX="center"
        anchorY="bottom"
        font={undefined}
        raycast={NO_RAYCAST}
      >
        {name}
      </Text>
    </group>
  );
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
