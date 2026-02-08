/**
 * SymbolBody - Renders the component body as a modern card.
 *
 * - Rounded rectangle with subtle accent-tinted border
 * - Reference designator tag + component name centered
 * - Small parts only show the reference, full name in sidebar
 * - Pin-1 dot indicator
 */

import { useMemo } from 'react';
import { Text, RoundedBox } from '@react-three/drei';
import type { KicadSymbol } from '../types/symbol';
import type { ThemeColors } from '../lib/theme';

interface SymbolBodyProps {
  symbol: KicadSymbol;
  theme: ThemeColors;
}

/** Threshold: bodies smaller than this area (mm^2) are "small parts" */
const SMALL_AREA = 40;

export function SymbolBody({ symbol, theme }: SymbolBodyProps) {
  const { bodyBounds } = symbol;
  const W = bodyBounds.width;
  const H = bodyBounds.height;
  const cx = (bodyBounds.minX + bodyBounds.maxX) / 2;
  const cy = (bodyBounds.minY + bodyBounds.maxY) / 2;

  const isSmall = W * H < SMALL_AREA;

  // Component-type accent color
  const accentColor = useMemo(() => {
    const ref = symbol.reference.toUpperCase();
    if (ref.startsWith('U')) return '#89b4fa';  // IC - blue
    if (ref.startsWith('R')) return '#cba6f7';  // Resistor - mauve
    if (ref.startsWith('C')) return '#f9e2af';  // Capacitor - yellow
    if (ref.startsWith('L')) return '#94e2d5';  // Inductor - teal
    if (ref.startsWith('D')) return '#f38ba8';  // Diode - red
    if (ref.startsWith('Q')) return '#fab387';  // Transistor - peach
    if (ref.startsWith('J') || ref.startsWith('P')) return '#a6e3a1'; // Connector - green
    return '#7f849c';
  }, [symbol.reference]);

  const RADIUS = Math.min(W, H) * 0.08;
  const DEPTH = 0.01;

  const refText = symbol.reference;
  const displayName = symbol.value || symbol.name;

  // Font sizing — scale with body, leave room for pin names on edges
  const maxDim = Math.min(W, H);
  const nameFontSize = Math.min(2.0, Math.max(0.7, maxDim * 0.14));
  const refFontSize = nameFontSize * 0.5;
  const maxTextWidth = W * 0.55;

  // Pin-1 dot position (top-left corner inside body)
  const dotX = bodyBounds.minX + Math.max(0.6, W * 0.06);
  const dotY = bodyBounds.maxY - Math.max(0.6, H * 0.06);

  return (
    <group position={[cx, cy, 0]}>
      {/* ── Outer glow / border ring ── */}
      <RoundedBox
        args={[W + 0.3, H + 0.3, DEPTH]}
        radius={RADIUS + 0.05}
        smoothness={4}
        position={[0, 0, -0.005]}
      >
        <meshBasicMaterial color={accentColor} transparent opacity={0.1} />
      </RoundedBox>

      {/* ── Body background ── */}
      <RoundedBox
        args={[W, H, DEPTH]}
        radius={RADIUS}
        smoothness={4}
      >
        <meshBasicMaterial color={theme.bodyFill} />
      </RoundedBox>

      {/* ── Border line ── */}
      <RoundedBox
        args={[W + 0.12, H + 0.12, DEPTH * 0.5]}
        radius={RADIUS + 0.02}
        smoothness={4}
        position={[0, 0, -0.002]}
      >
        <meshBasicMaterial color={theme.bodyBorder} />
      </RoundedBox>

      {/* ── Center text ── */}
      {isSmall ? (
        /* Small parts: just the reference designator, centered */
        <Text
          position={[0, 0, 0.015]}
          fontSize={Math.min(1.4, Math.max(0.6, maxDim * 0.35))}
          color={accentColor}
          anchorX="center"
          anchorY="middle"
          letterSpacing={0.04}
          font={undefined}
        >
          {refText}
        </Text>
      ) : (
        /* Larger parts: reference tag above, part name below */
        <>
          <Text
            position={[0, nameFontSize * 0.7, 0.015]}
            fontSize={refFontSize}
            color={accentColor}
            anchorX="center"
            anchorY="middle"
            letterSpacing={0.08}
            maxWidth={maxTextWidth}
            font={undefined}
          >
            {refText}
          </Text>
          <Text
            position={[0, -nameFontSize * 0.2, 0.015]}
            fontSize={nameFontSize}
            color={theme.textPrimary}
            anchorX="center"
            anchorY="middle"
            maxWidth={maxTextWidth}
            font={undefined}
          >
            {displayName}
          </Text>
        </>
      )}

      {/* ── Pin-1 indicator dot ── */}
      <mesh position={[dotX - cx, dotY - cy, 0.015]}>
        <circleGeometry args={[isSmall ? 0.25 : 0.4, 16]} />
        <meshBasicMaterial color={theme.textMuted} transparent opacity={0.3} />
      </mesh>
    </group>
  );
}
