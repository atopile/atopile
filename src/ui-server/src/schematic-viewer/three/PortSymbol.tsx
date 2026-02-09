/**
 * PortSymbol — renders schematic sheet ports for module interfaces.
 *
 * Ports represent external interface connections when viewing a module's
 * internal sheet. Single-signal and breakout ports share the same visual
 * language (rounded body, accent rail, stub line, and connection dot).
 */

import { useMemo, memo } from 'react';
import { Text, Line, RoundedBox } from '@react-three/drei';
import type { SchematicPort } from '../types/schematic';
import {
  getPortGridAlignmentOffset,
  PORT_STUB_LEN,
  type GridAlignmentOffset,
} from '../types/schematic';
import type { ThemeColors } from '../lib/theme';
import { getPinColor } from '../lib/theme';
import {
  getUprightTextTransform,
  anchorFromVisualSide,
  getVisualSide,
} from '../lib/itemTransform';

const BREAKOUT_RADIUS = 0.32;
const NO_RAYCAST = () => {};

// ── Public component ───────────────────────────────────────────

interface Props {
  port: SchematicPort;
  theme: ThemeColors;
  isSelected: boolean;
  isHovered: boolean;
  isDragging: boolean;
  selectedNetId: string | null;
  netId: string | null;
  rotation?: number;
  mirrorX?: boolean;
  mirrorY?: boolean;
}

interface SymbolProps extends Props {
  gridOffset: GridAlignmentOffset;
}

export const PortSymbol = memo(function PortSymbol(props: Props) {
  const { port } = props;
  const isBreakout = port.signals && port.signals.length >= 2;
  const gridOffset = useMemo(() => getPortGridAlignmentOffset(port), [port]);

  if (isBreakout) {
    return <BreakoutPortSymbol {...props} gridOffset={gridOffset} />;
  }
  return <SinglePortSymbol {...props} gridOffset={gridOffset} />;
});

// ── Single port (styled to match breakout ports) ────────────────

const SinglePortSymbol = memo(function SinglePortSymbol({
  port,
  theme,
  isSelected,
  isHovered,
  isDragging,
  selectedNetId,
  netId,
  gridOffset,
  rotation = 0,
  mirrorX = false,
  mirrorY = false,
}: SymbolProps) {
  const color = getPinColor(port.category, theme);
  const isNetHighlighted = netId !== null && netId === selectedNetId;
  const isActive = isSelected || isHovered || isNetHighlighted;
  const fillOpacity = 0.96;
  const tintOpacity = isSelected ? 0.28 : isActive ? 0.2 : 0.12;
  const borderOpacity = isSelected || isNetHighlighted ? 0.95 : isHovered ? 0.82 : 0.68;
  const borderColor = isSelected || isNetHighlighted ? color : theme.bodyBorder;
  const zOffset = isDragging ? 0.5 : 0;
  const pinX = port.pinX;
  const pinY = port.pinY;
  const hw = port.bodyWidth / 2;
  const hh = port.bodyHeight / 2;
  const hitW = port.bodyWidth + Math.max(2.2, Math.max(0, Math.abs(pinX) - hw) * 2 + 1);
  const hitH = port.bodyHeight + Math.max(1.8, Math.max(0, Math.abs(pinY) - hh) * 2 + 1);
  const textTf = useMemo(
    () => getUprightTextTransform(rotation, mirrorX, mirrorY),
    [rotation, mirrorX, mirrorY],
  );
  const visualSide = useMemo(
    () => getVisualSide(port.side, rotation, mirrorX, mirrorY),
    [port.side, rotation, mirrorX, mirrorY],
  );
  const visualHorizontal = visualSide === 'left' || visualSide === 'right';
  const isHorizontal = port.side === 'left' || port.side === 'right';
  const stubDir = port.side === 'left' ? 1 : port.side === 'right' ? -1 : 0;
  const stubDirY = port.side === 'top' ? -1 : port.side === 'bottom' ? 1 : 0;

  // Body edge point where the external line meets the symbol.
  let edgeX: number;
  let edgeY: number;
  if (isHorizontal) {
    edgeX = stubDir > 0 ? hw : -hw;
    edgeY = pinY;
  } else {
    edgeX = pinX;
    edgeY = stubDirY > 0 ? -hh : hh;
  }

  let labelX: number;
  let labelY: number;
  if (isHorizontal) {
    labelX = stubDir > 0 ? hw - 0.7 : -hw + 0.7;
    labelY = pinY;
  } else {
    labelX = pinX;
    labelY = stubDirY > 0 ? -hh + 0.66 : hh - 0.66;
  }
  const effectiveAnchor = anchorFromVisualSide(port.side, {
    rotationDeg: rotation,
    mirrorX,
    mirrorY,
    left: 'right',
    right: 'left',
    vertical: 'center',
  });
  const labelFontSize = Math.min(0.86, Math.max(0.7, port.bodyHeight * 0.7));

  return (
    <group position={[gridOffset.x, gridOffset.y, zOffset]}>
      {/* ── Invisible hit target ── */}
      <mesh position={[0, 0, -0.005]}>
        <planeGeometry args={[hitW, hitH]} />
        <meshBasicMaterial transparent opacity={0} depthWrite={false} />
      </mesh>

      {/* ── Active halo ─────────────────────────────── */}
      {isActive && (
        <RoundedBox
          args={[port.bodyWidth + 0.9, port.bodyHeight + 0.9, 0.001]}
          radius={BREAKOUT_RADIUS + 0.18}
          smoothness={4}
          position={[0, 0, -0.003]}
          raycast={NO_RAYCAST}
        >
          <meshBasicMaterial
            color={color}
            transparent
            opacity={isSelected ? 0.16 : 0.09}
            depthWrite={false}
          />
        </RoundedBox>
      )}

      {/* ── Border ──────────────────────────────────── */}
      <RoundedBox
        args={[port.bodyWidth + 0.12, port.bodyHeight + 0.12, 0.001]}
        radius={BREAKOUT_RADIUS + 0.04}
        smoothness={4}
        position={[0, 0, -0.002]}
        raycast={NO_RAYCAST}
      >
        <meshBasicMaterial color={borderColor} transparent opacity={borderOpacity} depthWrite={false} />
      </RoundedBox>

      {/* ── Body fill ── */}
      <RoundedBox
        args={[port.bodyWidth, port.bodyHeight, 0.001]}
        radius={BREAKOUT_RADIUS}
        smoothness={4}
        position={[0, 0, -0.001]}
        raycast={NO_RAYCAST}
      >
        <meshBasicMaterial color={theme.bodyFill} transparent opacity={fillOpacity} depthWrite={false} />
      </RoundedBox>

      {/* ── Accent tint overlay ─────────────────────── */}
      <RoundedBox
        args={[port.bodyWidth, port.bodyHeight, 0.001]}
        radius={BREAKOUT_RADIUS}
        smoothness={4}
        position={[0, 0, 0]}
        raycast={NO_RAYCAST}
      >
        <meshBasicMaterial color={color} transparent opacity={tintOpacity} depthWrite={false} />
      </RoundedBox>

      {/* ── Accent rail near stub side ──────────────── */}
      <mesh
        position={[
          isHorizontal ? (stubDir > 0 ? hw - 0.2 : -hw + 0.2) : 0,
          isHorizontal ? 0 : (stubDirY > 0 ? -hh + 0.2 : hh - 0.2),
          0.001,
        ]}
        raycast={NO_RAYCAST}
      >
        <planeGeometry
          args={isHorizontal ? [0.24, Math.max(0.8, port.bodyHeight - 0.8)] : [Math.max(0.8, port.bodyWidth - 0.8), 0.24]}
        />
        <meshBasicMaterial color={color} transparent opacity={isActive ? 0.5 : 0.36} depthWrite={false} />
      </mesh>

      {/* ── Name label (single signal row style) ───── */}
      <group
        position={[labelX, labelY, 0.002]}
        rotation={[0, 0, textTf.rotationZ]}
        scale={[textTf.scaleX, textTf.scaleY, 1]}
      >
        <Text
          fontSize={labelFontSize}
          color={isNetHighlighted ? theme.textPrimary : theme.textSecondary}
          anchorX={effectiveAnchor}
          anchorY="middle"
          maxWidth={visualHorizontal ? port.bodyWidth * 0.72 : port.bodyWidth * 0.82}
          letterSpacing={0.02}
          font={undefined}
          raycast={NO_RAYCAST}
        >
          {port.name}
        </Text>
      </group>

      {/* ── Stub line from body edge to connection dot ── */}
      <Line
        points={[
          [edgeX, edgeY, 0.002],
          [pinX, pinY, 0.002],
        ]}
        color={color}
        lineWidth={isActive ? 1.9 : 1.5}
        transparent
        opacity={isActive ? 0.78 : 0.58}
        raycast={NO_RAYCAST}
      />

      {/* ── Connection dot + glow ───────────────────── */}
      <mesh position={[pinX, pinY, 0.001]} raycast={NO_RAYCAST}>
        <circleGeometry args={[BREAKOUT_DOT_RADIUS * 1.85, 16]} />
        <meshBasicMaterial
          color={color}
          transparent
          opacity={isActive ? 0.22 : 0.12}
          depthWrite={false}
        />
      </mesh>
      <mesh position={[pinX, pinY, 0.002]} raycast={NO_RAYCAST}>
        <circleGeometry args={[BREAKOUT_DOT_RADIUS, 16]} />
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

const BREAKOUT_STUB_LEN = PORT_STUB_LEN;
const BREAKOUT_DOT_RADIUS = 0.4;

const BreakoutPortSymbol = memo(function BreakoutPortSymbol({
  port,
  theme,
  isSelected,
  isHovered,
  isDragging,
  selectedNetId,
  netId,
  gridOffset,
  rotation = 0,
  mirrorX = false,
  mirrorY = false,
}: SymbolProps) {
  const signals = port.signals!;
  const signalPins = port.signalPins!;
  const color = getPinColor(port.category, theme);
  const isNetHighlighted = netId !== null && netId === selectedNetId;
  const isActive = isSelected || isHovered || isNetHighlighted;
  const fillOpacity = 0.96;
  const tintOpacity = isSelected ? 0.24 : isActive ? 0.17 : 0.1;
  const borderOpacity = isSelected || isNetHighlighted ? 0.95 : isHovered ? 0.84 : 0.68;
  const borderColor = isSelected || isNetHighlighted ? color : theme.bodyBorder;
  const zOffset = isDragging ? 0.5 : 0;
  const textTf = useMemo(
    () => getUprightTextTransform(rotation, mirrorX, mirrorY),
    [rotation, mirrorX, mirrorY],
  );
  const visualSide = useMemo(
    () => getVisualSide(port.side, rotation, mirrorX, mirrorY),
    [port.side, rotation, mirrorX, mirrorY],
  );
  const visualHorizontal = visualSide === 'left' || visualSide === 'right';
  const effectiveNameAnchor = anchorFromVisualSide(port.side, {
    rotationDeg: rotation,
    mirrorX,
    mirrorY,
    left: 'left',
    right: 'right',
    vertical: 'center',
  });
  const effectiveSignalAnchor = anchorFromVisualSide(port.side, {
    rotationDeg: rotation,
    mirrorX,
    mirrorY,
    left: 'right',
    right: 'left',
    vertical: 'center',
  });

  const hw = port.bodyWidth / 2;
  const hh = port.bodyHeight / 2;
  const showLinePin =
    Math.abs(port.pinX) > hw + 0.01 || Math.abs(port.pinY) > hh + 0.01;

  // Hit target covers body + stubs
  const hitW = port.bodyWidth + BREAKOUT_STUB_LEN * 2 + 2;
  const hitH = port.bodyHeight + 2;

  // Determine stub direction
  const isHorizontal = port.side === 'left' || port.side === 'right';
  const stubDir = port.side === 'left' ? 1 : port.side === 'right' ? -1 : 0;
  const stubDirY = port.side === 'top' ? -1 : port.side === 'bottom' ? 1 : 0;
  const nameFontSize = Math.min(0.98, Math.max(0.62, port.bodyHeight * 0.17));

  let nameX = 0;
  let nameY = 0;
  if (isHorizontal) {
    nameX = stubDir > 0 ? -hw + 0.9 : hw - 0.9;
  } else {
    nameY = stubDirY > 0 ? hh - 0.8 : -hh + 0.8;
  }

  return (
    <group position={[gridOffset.x, gridOffset.y, zOffset]}>
      {/* ── Invisible hit target ── */}
      <mesh position={[0, 0, -0.005]}>
        <planeGeometry args={[hitW, hitH]} />
        <meshBasicMaterial transparent opacity={0} depthWrite={false} />
      </mesh>

      {/* ── Active halo ─────────────────────────────── */}
      {isActive && (
        <RoundedBox
          args={[port.bodyWidth + 0.9, port.bodyHeight + 0.9, 0.001]}
          radius={BREAKOUT_RADIUS + 0.18}
          smoothness={4}
          position={[0, 0, -0.003]}
          raycast={NO_RAYCAST}
        >
          <meshBasicMaterial
            color={color}
            transparent
            opacity={isSelected ? 0.16 : 0.09}
            depthWrite={false}
          />
        </RoundedBox>
      )}

      {/* ── Border ──────────────────────────────────── */}
      <RoundedBox
        args={[port.bodyWidth + 0.12, port.bodyHeight + 0.12, 0.001]}
        radius={BREAKOUT_RADIUS + 0.04}
        smoothness={4}
        position={[0, 0, -0.002]}
        raycast={NO_RAYCAST}
      >
        <meshBasicMaterial color={borderColor} transparent opacity={borderOpacity} depthWrite={false} />
      </RoundedBox>

      {/* ── Body fill ── */}
      <RoundedBox
        args={[port.bodyWidth, port.bodyHeight, 0.001]}
        radius={BREAKOUT_RADIUS}
        smoothness={4}
        position={[0, 0, -0.001]}
        raycast={NO_RAYCAST}
      >
        <meshBasicMaterial color={theme.bodyFill} transparent opacity={fillOpacity} depthWrite={false} />
      </RoundedBox>

      {/* ── Accent tint ─────────────────────────────── */}
      <RoundedBox
        args={[port.bodyWidth, port.bodyHeight, 0.001]}
        radius={BREAKOUT_RADIUS}
        smoothness={4}
        position={[0, 0, 0]}
        raycast={NO_RAYCAST}
      >
        <meshBasicMaterial color={color} transparent opacity={tintOpacity} depthWrite={false} />
      </RoundedBox>

      {/* ── Accent rail near stub side ──────────────── */}
      <mesh
        position={[
          isHorizontal ? (stubDir > 0 ? hw - 0.2 : -hw + 0.2) : 0,
          isHorizontal ? 0 : (stubDirY > 0 ? -hh + 0.2 : hh - 0.2),
          0.001,
        ]}
        raycast={NO_RAYCAST}
      >
        <planeGeometry
          args={isHorizontal ? [0.24, Math.max(0.8, port.bodyHeight - 0.8)] : [Math.max(0.8, port.bodyWidth - 0.8), 0.24]}
        />
        <meshBasicMaterial color={color} transparent opacity={isActive ? 0.5 : 0.36} depthWrite={false} />
      </mesh>

      {/* ── Interface name label ────────────────────── */}
      <group
        position={[nameX, nameY, 0.002]}
        rotation={[0, 0, textTf.rotationZ]}
        scale={[textTf.scaleX, textTf.scaleY, 1]}
      >
        <Text
          fontSize={nameFontSize}
          color={theme.textPrimary}
          anchorX={effectiveNameAnchor}
          anchorY="middle"
          maxWidth={visualHorizontal ? port.bodyWidth * 0.55 : port.bodyWidth * 0.72}
          letterSpacing={0.02}
          font={undefined}
          raycast={NO_RAYCAST}
        >
          {port.name}
        </Text>
      </group>

      {/* ── Line-level translator pin (opposite edge) ─────────── */}
      {showLinePin && (() => {
        let lineEdgeX: number;
        let lineEdgeY: number;
        if (isHorizontal) {
          lineEdgeX = port.pinX > 0 ? hw : -hw;
          lineEdgeY = port.pinY;
        } else {
          lineEdgeX = port.pinX;
          lineEdgeY = port.pinY > 0 ? hh : -hh;
        }

        return (
          <group>
            <Line
              points={[
                [lineEdgeX, lineEdgeY, 0.002],
                [port.pinX, port.pinY, 0.002],
              ]}
              color={color}
              lineWidth={isActive ? 1.5 : 1.2}
              transparent
              opacity={isActive ? 0.5 : 0.34}
              raycast={NO_RAYCAST}
            />
            <mesh position={[port.pinX, port.pinY, 0.001]} raycast={NO_RAYCAST}>
              <circleGeometry args={[0.48, 14]} />
              <meshBasicMaterial
                color={color}
                transparent
                opacity={isActive ? 0.16 : 0.09}
                depthWrite={false}
              />
            </mesh>
            <mesh position={[port.pinX, port.pinY, 0.002]} raycast={NO_RAYCAST}>
              <circleGeometry args={[0.24, 14]} />
              <meshBasicMaterial
                color={color}
                transparent
                opacity={isActive ? 0.82 : 0.62}
                depthWrite={false}
              />
            </mesh>
          </group>
        );
      })()}

      {/* ── Signal stubs + dots + labels ── */}
      {signals.map((sig) => {
        const rawSp = signalPins[sig];
        const sp = rawSp ? { x: rawSp.x, y: rawSp.y } : null;
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
        if (isHorizontal) {
          labelX = stubDir > 0 ? hw - 0.7 : -hw + 0.7;
          labelY = sp.y;
        } else {
          labelX = sp.x;
          labelY = stubDirY > 0 ? -hh + 0.7 : hh - 0.7;
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
              lineWidth={isActive ? 1.9 : 1.5}
              transparent
              opacity={isActive ? 0.78 : 0.58}
              raycast={NO_RAYCAST}
            />

            {/* Connection dot + glow */}
            <mesh position={[sp.x, sp.y, 0.001]} raycast={NO_RAYCAST}>
              <circleGeometry args={[BREAKOUT_DOT_RADIUS * 1.85, 16]} />
              <meshBasicMaterial
                color={color}
                transparent
                opacity={isActive ? 0.22 : 0.12}
                depthWrite={false}
              />
            </mesh>
            <mesh position={[sp.x, sp.y, 0.002]} raycast={NO_RAYCAST}>
              <circleGeometry args={[BREAKOUT_DOT_RADIUS, 16]} />
              <meshBasicMaterial color={color} />
            </mesh>

            {/* Signal label inside body */}
            <group
              position={[labelX, labelY, 0.001]}
              rotation={[0, 0, textTf.rotationZ]}
              scale={[textTf.scaleX, textTf.scaleY, 1]}
            >
              <Text
                fontSize={0.78}
                color={isNetHighlighted ? theme.textPrimary : theme.textSecondary}
                anchorX={effectiveSignalAnchor}
                anchorY="middle"
                font={undefined}
                raycast={NO_RAYCAST}
              >
                {sig.toUpperCase()}
              </Text>
            </group>
          </group>
        );
      })}
    </group>
  );
});
