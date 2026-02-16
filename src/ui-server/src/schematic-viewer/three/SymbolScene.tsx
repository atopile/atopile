/**
 * SymbolScene - Main Three.js canvas for rendering KiCad symbols.
 *
 * Uses an orthographic-like setup (OrbitControls with no rotation)
 * for a clean 2D schematic view. Auto-fits the symbol on load.
 */

import { useMemo } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import { useSymbolStore, useActiveSymbol } from '../stores/symbolStore';
import { useTheme } from '../utils/theme';
import { SymbolBody } from './SymbolBody';
import { PinElement } from './PinElement';

export function SymbolScene() {
  const symbol = useActiveSymbol();
  const theme = useTheme();

  // Camera framing from total bounds
  const cameraSetup = useMemo(() => {
    if (!symbol) return null;
    const { totalBounds } = symbol;
    const cx = (totalBounds.minX + totalBounds.maxX) / 2;
    const cy = (totalBounds.minY + totalBounds.maxY) / 2;
    const rangeX = totalBounds.maxX - totalBounds.minX;
    const rangeY = totalBounds.maxY - totalBounds.minY;
    // Add generous padding for pin names
    const padding = Math.max(rangeX, rangeY) * 0.6;
    const distance = Math.max(rangeX + padding, rangeY + padding) * 0.7 + 10;
    return { cx, cy, distance };
  }, [symbol]);

  if (!symbol || !cameraSetup) return null;

  return (
    <Canvas
      camera={{
        position: [cameraSetup.cx, cameraSetup.cy, cameraSetup.distance],
        fov: 50,
        near: 0.1,
        far: 500,
      }}
      style={{ background: theme.bgPrimary }}
      onPointerMissed={() => {
        useSymbolStore.getState().setSelectedPin(null);
        useSymbolStore.getState().setHighlightCategory(null);
      }}
    >
      <ambientLight intensity={1} />

      <OrbitControls
        target={[cameraSetup.cx, cameraSetup.cy, 0]}
        enableRotate={false}
        enablePan={true}
        enableZoom={true}
        minDistance={3}
        maxDistance={200}
        mouseButtons={{
          LEFT: 2,   // pan
          MIDDLE: 1, // zoom
          RIGHT: 2,  // pan
        }}
      />

      {/* Component body */}
      <SymbolBody symbol={symbol} theme={theme} />

      {/* Pins */}
      {symbol.pins.map((pin) => (
        <PinElement key={`${pin.number}-${pin.name}`} pin={pin} theme={theme} />
      ))}
    </Canvas>
  );
}
