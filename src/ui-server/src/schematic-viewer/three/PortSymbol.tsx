/**
 * PortSymbol — renders an Altium-style sheet port (pentagon arrow).
 *
 * Ports represent external interface connections when viewing a module's
 * internal sheet. They show where signals enter/exit the current hierarchy level.
 *
 * Visual design:
 * - Pentagon/arrow shape pointing into the sheet
 * - Color-coded by pin category (power=red, ground=grey, i2c=blue, etc.)
 * - Signal name label inside
 * - Connection dot at the arrow tip
 * - Directional indicator line from body to connection dot
 */

import { useMemo, memo } from 'react';
import { Text, Line } from '@react-three/drei';
import * as THREE from 'three';
import type { SchematicPort } from '../types/schematic';
import { PORT_W, PORT_H } from '../types/schematic';
import type { ThemeColors } from '../lib/theme';
import { getPinColor } from '../lib/theme';

const ARROW_DEPTH = 1.6;
const DOT_RADIUS = 0.4;
const NO_RAYCAST = () => {};

/**
 * Build a pentagon shape for the port arrow.
 *
 * For a left-side port (arrow points right →):
 *   (-W/2, H/2) ─── (W/2 - A, H/2)
 *        |                     ╲
 *        |                      (W/2, 0) ← tip
 *        |                     ╱
 *   (-W/2, -H/2) ── (W/2 - A, -H/2)
 */
function buildPortShape(side: string): THREE.Shape {
  const hw = PORT_W / 2;
  const hh = PORT_H / 2;
  const a = ARROW_DEPTH;
  const shape = new THREE.Shape();

  switch (side) {
    case 'left': // arrow points right
      shape.moveTo(-hw, hh);
      shape.lineTo(hw - a, hh);
      shape.lineTo(hw, 0);
      shape.lineTo(hw - a, -hh);
      shape.lineTo(-hw, -hh);
      shape.closePath();
      break;

    case 'right': // arrow points left
      shape.moveTo(hw, hh);
      shape.lineTo(-(hw - a), hh);
      shape.lineTo(-hw, 0);
      shape.lineTo(-(hw - a), -hh);
      shape.lineTo(hw, -hh);
      shape.closePath();
      break;

    case 'top': // arrow points down
      shape.moveTo(-hh, hw);
      shape.lineTo(hh, hw);
      shape.lineTo(hh, -(hw - a));
      shape.lineTo(0, -hw);
      shape.lineTo(-hh, -(hw - a));
      shape.closePath();
      break;

    case 'bottom': // arrow points up
      shape.moveTo(-hh, -hw);
      shape.lineTo(hh, -hw);
      shape.lineTo(hh, hw - a);
      shape.lineTo(0, hw);
      shape.lineTo(-hh, hw - a);
      shape.closePath();
      break;

    default: // fallback: right-pointing
      shape.moveTo(-hw, hh);
      shape.lineTo(hw - a, hh);
      shape.lineTo(hw, 0);
      shape.lineTo(hw - a, -hh);
      shape.lineTo(-hw, -hh);
      shape.closePath();
  }

  return shape;
}

// ── Public component ───────────────────────────────────────────

interface Props {
  port: SchematicPort;
  theme: ThemeColors;
  isSelected: boolean;
  isHovered: boolean;
  isDragging: boolean;
  selectedNetId: string | null;
  netId: string | null;
}

export const PortSymbol = memo(function PortSymbol(props: Props) {
  const { port } = props;
  const isBreakout = port.signals && port.signals.length >= 2;

  if (isBreakout) {
    return <BreakoutPortSymbol {...props} />;
  }
  return <PentagonPortSymbol {...props} />;
});

// ── Pentagon port (original single-signal rendering) ────────────

const PentagonPortSymbol = memo(function PentagonPortSymbol({
  port,
  theme,
  isSelected,
  isHovered,
  isDragging,
  selectedNetId,
  netId,
}: Props) {
  const color = getPinColor(port.category, theme);
  const isNetHighlighted = netId !== null && netId === selectedNetId;
  const fillColor = isNetHighlighted ? color : color;
  const fillOpacity = isSelected ? 0.5 : isHovered ? 0.42 : 0.35;
  const borderOpacity = isSelected ? 0.9 : 0.6;
  const zOffset = isDragging ? 0.5 : 0;

  const shape = useMemo(() => buildPortShape(port.side), [port.side]);
  const geometry = useMemo(() => new THREE.ShapeGeometry(shape), [shape]);
  const edgesGeometry = useMemo(() => new THREE.EdgesGeometry(geometry), [geometry]);

  // Directional indicator: line from body edge toward connection dot
  const indicatorPoints = useMemo(() => {
    const hw = PORT_W / 2;
    const gap = 0.6; // gap before dot
    switch (port.side) {
      case 'left':
        return [new THREE.Vector3(hw - ARROW_DEPTH, 0, 0.002), new THREE.Vector3(port.pinX - DOT_RADIUS - gap, port.pinY, 0.002)];
      case 'right':
        return [new THREE.Vector3(-(hw - ARROW_DEPTH), 0, 0.002), new THREE.Vector3(port.pinX + DOT_RADIUS + gap, port.pinY, 0.002)];
      case 'top':
        return [new THREE.Vector3(0, -(hw - ARROW_DEPTH), 0.002), new THREE.Vector3(port.pinX, port.pinY + DOT_RADIUS + gap, 0.002)];
      case 'bottom':
        return [new THREE.Vector3(0, hw - ARROW_DEPTH, 0.002), new THREE.Vector3(port.pinX, port.pinY - DOT_RADIUS - gap, 0.002)];
      default:
        return [new THREE.Vector3(0, 0, 0.002), new THREE.Vector3(port.pinX, port.pinY, 0.002)];
    }
  }, [port.side, port.pinX, port.pinY]);

  // Text positioning: center of the non-arrow part
  const textX = port.side === 'left' ? -ARROW_DEPTH / 2 :
                port.side === 'right' ? ARROW_DEPTH / 2 : 0;
  const textY = port.side === 'top' ? ARROW_DEPTH / 2 :
                port.side === 'bottom' ? -ARROW_DEPTH / 2 : 0;
  const fontSize = Math.min(1.1, Math.max(0.7, PORT_H * 0.5));

  // Interface type label (small, below the name)
  const showType = port.interfaceType !== 'Electrical';

  return (
    <group position={[0, 0, zOffset]}>
      {/* ── Invisible hit target (enables pointer events on parent) ── */}
      <mesh geometry={geometry} position={[0, 0, -0.005]}>
        <meshBasicMaterial transparent opacity={0} depthWrite={false} />
      </mesh>

      {/* ── Selection highlight ─────────────────────── */}
      {isSelected && (
        <mesh position={[0, 0, -0.003]} raycast={NO_RAYCAST}>
          <shapeGeometry args={[buildPortShape(port.side)]} />
          <meshBasicMaterial color={color} transparent opacity={0.2} />
        </mesh>
      )}

      {/* ── Border (solid outline via EdgesGeometry) ── */}
      <lineSegments geometry={edgesGeometry} position={[0, 0, -0.002]} raycast={NO_RAYCAST}>
        <lineBasicMaterial
          color={isSelected ? color : theme.bodyBorder}
          transparent
          opacity={borderOpacity}
          linewidth={1}
        />
      </lineSegments>

      {/* ── Body fill ───────────────────────────────── */}
      <mesh geometry={geometry} position={[0, 0, -0.001]} raycast={NO_RAYCAST}>
        <meshBasicMaterial color={fillColor} transparent opacity={fillOpacity} />
      </mesh>

      {/* ── Name label ──────────────────────────────── */}
      <Text
        position={[textX, textY + (showType ? 0.15 : 0), 0.001]}
        fontSize={fontSize}
        color={theme.textPrimary}
        anchorX="center"
        anchorY="middle"
        letterSpacing={0.03}
        font={undefined}
        raycast={NO_RAYCAST}
      >
        {port.name}
      </Text>

      {/* ── Interface type (small, muted) ───────────── */}
      {showType && (
        <Text
          position={[textX, textY - 0.4, 0.001]}
          fontSize={fontSize * 0.55}
          color={theme.textMuted}
          anchorX="center"
          anchorY="middle"
          font={undefined}
          raycast={NO_RAYCAST}
        >
          {port.interfaceType}
        </Text>
      )}

      {/* ── Directional indicator line ────────────────── */}
      <Line
        points={indicatorPoints}
        color={color}
        lineWidth={1.5}
        transparent
        opacity={0.5}
        raycast={NO_RAYCAST}
      />

      {/* ── Connection dot at arrow tip ─────────────── */}
      <mesh position={[port.pinX, port.pinY, 0.001]} raycast={NO_RAYCAST}>
        <circleGeometry args={[DOT_RADIUS, 16]} />
        <meshBasicMaterial color={color} />
      </mesh>
    </group>
  );
});

// ── Breakout port (multi-signal component-like box) ─────────────
//
// Visual design (left-side port, stubs extend right into sheet):
//     ┌──────────┐
//     │          ├── SCL  ●
//     │   I2C    │
//     │          ├── SDA  ●
//     └──────────┘

const BREAKOUT_STUB_LEN = 2.54;
const BREAKOUT_DOT_RADIUS = 0.4;

const BreakoutPortSymbol = memo(function BreakoutPortSymbol({
  port,
  theme,
  isSelected,
  isHovered,
  isDragging,
}: Props) {
  const signals = port.signals!;
  const signalPins = port.signalPins!;
  const color = getPinColor(port.category, theme);
  const fillOpacity = isSelected ? 0.5 : isHovered ? 0.42 : 0.35;
  const borderOpacity = isSelected ? 0.9 : 0.6;
  const zOffset = isDragging ? 0.5 : 0;

  const hw = port.bodyWidth / 2;
  const hh = port.bodyHeight / 2;

  // Rectangular body shape
  const bodyShape = useMemo(() => {
    const s = new THREE.Shape();
    s.moveTo(-hw, hh);
    s.lineTo(hw, hh);
    s.lineTo(hw, -hh);
    s.lineTo(-hw, -hh);
    s.closePath();
    return s;
  }, [hw, hh]);

  const bodyGeo = useMemo(() => new THREE.ShapeGeometry(bodyShape), [bodyShape]);
  const edgesGeo = useMemo(() => new THREE.EdgesGeometry(bodyGeo), [bodyGeo]);

  // Hit target covers body + stubs
  const hitW = port.bodyWidth + BREAKOUT_STUB_LEN * 2 + 2;
  const hitH = port.bodyHeight + 2;

  // Determine stub direction
  const isHorizontal = port.side === 'left' || port.side === 'right';
  const stubDir = port.side === 'left' ? 1 : port.side === 'right' ? -1 : 0;
  const stubDirY = port.side === 'top' ? -1 : port.side === 'bottom' ? 1 : 0;

  return (
    <group position={[0, 0, zOffset]}>
      {/* ── Invisible hit target ── */}
      <mesh position={[0, 0, -0.005]}>
        <planeGeometry args={[hitW, hitH]} />
        <meshBasicMaterial transparent opacity={0} depthWrite={false} />
      </mesh>

      {/* ── Selection highlight ── */}
      {isSelected && (
        <mesh position={[0, 0, -0.003]} raycast={NO_RAYCAST}>
          <planeGeometry args={[port.bodyWidth + 1, port.bodyHeight + 1]} />
          <meshBasicMaterial color={color} transparent opacity={0.2} />
        </mesh>
      )}

      {/* ── Border ── */}
      <lineSegments geometry={edgesGeo} position={[0, 0, -0.002]} raycast={NO_RAYCAST}>
        <lineBasicMaterial
          color={isSelected ? color : theme.bodyBorder}
          transparent
          opacity={borderOpacity}
          linewidth={1}
        />
      </lineSegments>

      {/* ── Body fill ── */}
      <mesh geometry={bodyGeo} position={[0, 0, -0.001]} raycast={NO_RAYCAST}>
        <meshBasicMaterial color={color} transparent opacity={fillOpacity} />
      </mesh>

      {/* ── Interface name label (centered in body) ── */}
      <Text
        position={[0, 0, 0.001]}
        fontSize={1.2}
        color={theme.textPrimary}
        anchorX="center"
        anchorY="middle"
        letterSpacing={0.03}
        font={undefined}
        raycast={NO_RAYCAST}
      >
        {port.name}
      </Text>

      {/* ── Signal stubs + dots + labels ── */}
      {signals.map((sig) => {
        const sp = signalPins[sig];
        if (!sp) return null;

        // Body edge point (where stub exits)
        let edgeX: number, edgeY: number;
        if (isHorizontal) {
          edgeX = stubDir > 0 ? hw : -hw;
          edgeY = sp.y;
        } else {
          edgeX = sp.x;
          edgeY = stubDirY > 0 ? -hh : hh;
        }

        // Signal label position (inside the body, near the edge)
        let labelX: number, labelY: number;
        let anchor: 'left' | 'right' | 'center' = 'center';
        if (isHorizontal) {
          labelX = stubDir > 0 ? hw - 0.6 : -hw + 0.6;
          labelY = sp.y;
          anchor = stubDir > 0 ? 'right' : 'left';
        } else {
          labelX = sp.x;
          labelY = stubDirY > 0 ? -hh + 0.6 : hh - 0.6;
        }

        return (
          <group key={sig}>
            {/* Stub line from body edge to connection dot */}
            <Line
              points={[
                [edgeX, edgeY, 0.002],
                [sp.x, sp.y, 0.002],
              ]}
              color={color}
              lineWidth={1.5}
              transparent
              opacity={0.6}
              raycast={NO_RAYCAST}
            />

            {/* Connection dot */}
            <mesh position={[sp.x, sp.y, 0.001]} raycast={NO_RAYCAST}>
              <circleGeometry args={[BREAKOUT_DOT_RADIUS, 16]} />
              <meshBasicMaterial color={color} />
            </mesh>

            {/* Signal label inside body */}
            <Text
              position={[labelX, labelY, 0.001]}
              fontSize={0.8}
              color={theme.textMuted}
              anchorX={anchor}
              anchorY="middle"
              font={undefined}
              raycast={NO_RAYCAST}
            >
              {sig.toUpperCase()}
            </Text>
          </group>
        );
      })}
    </group>
  );
});
