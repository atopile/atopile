/**
 * PinElement - Renders a single pin with modern styling.
 *
 * Each pin is a colored stub line extending from the body, with:
 * - A filled circle endpoint (connection point)
 * - Pin name text alongside (inside the body area)
 * - Pin number text near the endpoint
 * - Hover glow and selection highlight
 *
 * Draws from the pinout viewer's color-accent tag style
 * and the tree viewer's clean card aesthetic.
 */

import { useState, useMemo, useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { Text, Line } from '@react-three/drei';
import * as THREE from 'three';
import type { KicadPin } from '../types/symbol';
import type { ThemeColors } from '../lib/theme';
import { useSymbolStore } from '../stores/symbolStore';
import { getConnectionColor } from './connectionColor';

interface PinElementProps {
  pin: KicadPin;
  theme: ThemeColors;
}

/** Subtle pulse on the connection dot when hovered. */
function PinDot({ color, radius, isActive }: { color: string; radius: number; isActive: boolean }) {
  const glowRef = useRef<THREE.MeshBasicMaterial>(null);

  useFrame(({ clock }) => {
    if (!glowRef.current) return;
    if (isActive) {
      const t = Math.sin(clock.getElapsedTime() * 3) * 0.5 + 0.5;
      glowRef.current.opacity = 0.15 + t * 0.2;
    } else {
      glowRef.current.opacity = 0;
    }
  });

  return (
    <group>
      {/* Glow ring */}
      <mesh>
        <circleGeometry args={[radius * 2.5, 20]} />
        <meshBasicMaterial ref={glowRef} color={color} transparent opacity={0} />
      </mesh>
      {/* Main dot */}
      <mesh>
        <circleGeometry args={[radius, 16]} />
        <meshBasicMaterial color={color} />
      </mesh>
    </group>
  );
}

export function PinElement({ pin, theme }: PinElementProps) {
  const [localHover, setLocalHover] = useState(false);
  const { hoveredPin, selectedPin, setHoveredPin, setSelectedPin, highlightCategory } = useSymbolStore();

  const isHovered = hoveredPin === pin.number || localHover;
  const isSelected = selectedPin?.number === pin.number;
  const isFaded = highlightCategory !== null && pin.category !== highlightCategory;

  const color = useMemo(() => getConnectionColor(pin.category, theme), [pin.category, theme]);

  // Pin geometry
  const { x, y, bodyX, bodyY, side, length } = pin;
  const DOT_RADIUS = 0.15;

  // Should we show the pin name? Hide if it equals the pin number (common for passives)
  const showName = !pin.nameHidden && pin.name && pin.name !== pin.number;

  // Text positioning based on pin side
  // Pin name goes INSIDE the body, near the body edge
  // Pin number goes OUTSIDE, near the connection endpoint, offset perpendicular
  let nameX: number, nameY: number;
  let numX: number, numY: number;
  let nameAnchorX: 'left' | 'right' | 'center' = 'left';

  const NAME_INSET = 0.8;  // how far inside the body the name sits
  const NUM_OFFSET = 0.6;  // perpendicular offset for pin number

  if (side === 'left') {
    // Connection on left, body on right
    nameX = bodyX + NAME_INSET;
    nameY = y;
    nameAnchorX = 'left';
    numX = x;
    numY = y + NUM_OFFSET;
  } else if (side === 'right') {
    // Connection on right, body on left
    nameX = bodyX - NAME_INSET;
    nameY = y;
    nameAnchorX = 'right';
    numX = x;
    numY = y + NUM_OFFSET;
  } else if (side === 'top') {
    // Connection on top, body below
    nameX = x;
    nameY = bodyY - NAME_INSET;
    nameAnchorX = 'center';
    numX = x + NUM_OFFSET;
    numY = y;
  } else {
    // bottom: Connection on bottom, body above
    nameX = x;
    nameY = bodyY + NAME_INSET;
    nameAnchorX = 'center';
    numX = x + NUM_OFFSET;
    numY = y;
  }

  const opacity = isFaded ? 0.12 : 1;
  const lineWidth = isHovered || isSelected ? 2.5 : 1.8;
  const lineColor = isSelected ? theme.accent : color;

  return (
    <group
      onPointerEnter={(e) => { e.stopPropagation(); setLocalHover(true); setHoveredPin(pin.number); document.body.style.cursor = 'pointer'; }}
      onPointerLeave={() => { setLocalHover(false); setHoveredPin(null); document.body.style.cursor = 'auto'; }}
      onClick={(e) => { e.stopPropagation(); setSelectedPin(pin); }}
    >
      {/* Selection/hover background strip along the pin line */}
      {(isHovered || isSelected) && !isFaded && (
        <mesh position={[(x + bodyX) / 2, (y + bodyY) / 2, -0.02]}>
          <planeGeometry args={[
            side === 'left' || side === 'right' ? length + 1 : 2,
            side === 'left' || side === 'right' ? 2 : length + 1,
          ]} />
          <meshBasicMaterial color={lineColor} transparent opacity={isSelected ? 0.08 : 0.05} />
        </mesh>
      )}

      {/* Pin stub line */}
      <group position={[0, 0, 0.01]}>
        <Line
          points={[[x, y, 0], [bodyX, bodyY, 0]]}
          color={lineColor}
          lineWidth={lineWidth}
          transparent
          opacity={opacity}
        />
      </group>

      {/* Connection dot */}
      <group position={[x, y, 0.02]}>
        <PinDot
          color={lineColor}
          radius={DOT_RADIUS * (isFaded ? 0.6 : 1)}
          isActive={(isHovered || isSelected) && !isFaded}
        />
      </group>

      {/* Pin name (inside body, near edge) */}
      {showName && (
        <Text
          position={[nameX, nameY, 0.03]}
          fontSize={1.05}
          color={isFaded ? theme.pinNC : (isSelected ? theme.textPrimary : theme.textSecondary)}
          anchorX={nameAnchorX}
          anchorY="middle"
          font={undefined}
        >
          {pin.name}
        </Text>
      )}

      {/* Pin number (outside, near connection endpoint) */}
      {!pin.numberHidden && pin.number && (
        <Text
          position={[numX, numY, 0.03]}
          fontSize={0.65}
          color={isFaded ? theme.pinNC : theme.textMuted}
          anchorX="center"
          anchorY="middle"
          font={undefined}
        >
          {pin.number}
        </Text>
      )}
    </group>
  );
}
