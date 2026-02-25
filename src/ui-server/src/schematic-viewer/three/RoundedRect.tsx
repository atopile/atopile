/**
 * RoundedRect — flat 2D rounded-rectangle geometry for schematic node bodies.
 *
 * Replaces drei's `RoundedBox` (which creates extruded 3D geometry with edge
 * bevels) with a truly flat `shapeGeometry` built from `THREE.Shape`. This
 * ensures all schematic boxes render as clean 2D planes regardless of camera
 * angle.
 */

import { memo, useMemo } from 'react';
import { Shape } from 'three';

const NO_RAYCAST = () => {};

/** Build a THREE.Shape describing a rounded rectangle centered at the origin. */
export function roundedRectShape(width: number, height: number, radius: number): Shape {
  const r = Math.max(0, Math.min(radius, width / 2, height / 2));
  const hw = width / 2;
  const hh = height / 2;
  const shape = new Shape();
  shape.moveTo(-hw + r, -hh);
  shape.lineTo(hw - r, -hh);
  shape.quadraticCurveTo(hw, -hh, hw, -hh + r);
  shape.lineTo(hw, hh - r);
  shape.quadraticCurveTo(hw, hh, hw - r, hh);
  shape.lineTo(-hw + r, hh);
  shape.quadraticCurveTo(-hw, hh, -hw, hh - r);
  shape.lineTo(-hw, -hh + r);
  shape.quadraticCurveTo(-hw, -hh, -hw + r, -hh);
  return shape;
}

export const RoundedRect = memo(function RoundedRect({
  width,
  height,
  radius,
  color,
  opacity = 1,
  transparent,
  depthWrite = false,
  position,
  toneMapped,
}: {
  width: number;
  height: number;
  radius: number;
  color: string;
  opacity?: number;
  transparent?: boolean;
  depthWrite?: boolean;
  position?: [number, number, number];
  toneMapped?: boolean;
}) {
  const shape = useMemo(
    () => roundedRectShape(width, height, radius),
    [width, height, radius],
  );

  const isTransparent = transparent ?? opacity < 1;

  return (
    <mesh position={position} raycast={NO_RAYCAST}>
      <shapeGeometry args={[shape]} />
      <meshBasicMaterial
        color={color}
        transparent={isTransparent}
        opacity={opacity}
        depthWrite={depthWrite}
        toneMapped={toneMapped}
      />
    </mesh>
  );
});
