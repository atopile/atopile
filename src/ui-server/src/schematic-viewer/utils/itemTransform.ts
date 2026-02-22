import type { PinSide } from '../types/symbol';

export type AnchorX = 'left' | 'center' | 'right';

function normalizeRotation(rotationDeg: number): number {
  const rounded = Math.round((rotationDeg || 0) / 90) * 90;
  return ((rounded % 360) + 360) % 360;
}

export function getVisualSide(
  side: PinSide,
  rotationDeg = 0,
  mirrorX = false,
  mirrorY = false,
): PinSide {
  let mapped: PinSide = side;

  if (mirrorX) {
    if (mapped === 'left') mapped = 'right';
    else if (mapped === 'right') mapped = 'left';
  }
  if (mirrorY) {
    if (mapped === 'top') mapped = 'bottom';
    else if (mapped === 'bottom') mapped = 'top';
  }

  const rot = normalizeRotation(rotationDeg);
  const rotate90: Record<PinSide, PinSide> = {
    right: 'top',
    top: 'left',
    left: 'bottom',
    bottom: 'right',
  };

  if (rot === 90) return rotate90[mapped];
  if (rot === 180) return rotate90[rotate90[mapped]];
  if (rot === 270) return rotate90[rotate90[rotate90[mapped]]];
  return mapped;
}

export function anchorFromVisualSide(
  baseSide: PinSide,
  opts: {
    rotationDeg?: number;
    mirrorX?: boolean;
    mirrorY?: boolean;
    left: AnchorX;
    right: AnchorX;
    vertical?: AnchorX;
  },
): AnchorX {
  const visual = getVisualSide(
    baseSide,
    opts.rotationDeg ?? 0,
    opts.mirrorX ?? false,
    opts.mirrorY ?? false,
  );

  if (visual === 'left') return opts.left;
  if (visual === 'right') return opts.right;
  return opts.vertical ?? 'center';
}

export function getUprightTextTransform(
  rotationDeg = 0,
  mirrorX = false,
  mirrorY = false,
): { rotationZ: number; scaleX: number; scaleY: number } {
  const rot = normalizeRotation(rotationDeg);
  let rotationZ = (rot * Math.PI) / 180;
  let scaleX = mirrorX ? -1 : 1;
  let scaleY = mirrorY ? -1 : 1;

  // Keep text upright for upside-down orientations.
  if (rot === 180) {
    rotationZ = 0;
    scaleX *= -1;
    scaleY *= -1;
  }

  return { rotationZ, scaleX, scaleY };
}
