/**
 * GridBackground — subtle schematic grid rendered with a single
 * BufferGeometry of line segments for efficiency.
 *
 * Minor grid: every 10 mm  (≈ 4 × 2.54 mm)
 * Major grid: every 50 mm  (extra thickness via separate material)
 *
 * Wrapped in memo to prevent re-renders from parent.
 * raycast={null} disabled to prevent r3f raycasting overhead.
 */

import { useMemo, memo } from 'react';
import * as THREE from 'three';
import type { ThemeColors } from '../lib/theme';

const NO_RAYCAST = () => {};

interface GridBackgroundProps {
  theme: ThemeColors;
  size?: number;
}

export const GridBackground = memo(function GridBackground({
  theme,
  size = 800,
}: GridBackgroundProps) {
  const minorGeo = useMemo(() => {
    const step = 10;
    const half = size / 2;
    const verts: number[] = [];
    for (let i = -half; i <= half; i += step) {
      verts.push(i, -half, 0, i, half, 0); // vertical
      verts.push(-half, i, 0, half, i, 0); // horizontal
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(verts, 3));
    return g;
  }, [size]);

  const majorGeo = useMemo(() => {
    const step = 50;
    const half = size / 2;
    const verts: number[] = [];
    for (let i = -half; i <= half; i += step) {
      verts.push(i, -half, 0, i, half, 0);
      verts.push(-half, i, 0, half, i, 0);
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(verts, 3));
    return g;
  }, [size]);

  return (
    <group position={[0, 0, -0.1]} raycast={NO_RAYCAST}>
      <lineSegments geometry={minorGeo} raycast={NO_RAYCAST}>
        <lineBasicMaterial
          color={theme.borderSubtle}
          transparent
          opacity={0.1}
        />
      </lineSegments>
      <lineSegments geometry={majorGeo} raycast={NO_RAYCAST}>
        <lineBasicMaterial
          color={theme.borderSubtle}
          transparent
          opacity={0.22}
        />
      </lineSegments>
    </group>
  );
});
