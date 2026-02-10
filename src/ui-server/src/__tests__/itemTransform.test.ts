import { describe, expect, it } from 'vitest';
import {
  anchorFromVisualSide,
  getVisualSide,
} from '../schematic-viewer/lib/itemTransform';

describe('itemTransform visual side + anchor policy', () => {
  it('maps sides through mirror/rotation using mirror-first semantics', () => {
    expect(getVisualSide('left', 0, false, false)).toBe('left');
    expect(getVisualSide('left', 180, false, false)).toBe('right');
    expect(getVisualSide('right', 90, false, false)).toBe('top');
    expect(getVisualSide('top', 270, false, false)).toBe('right');
    expect(getVisualSide('right', 0, true, false)).toBe('left');
  });

  it('keeps breakout signal labels on the visual inner edge', () => {
    // Port signal labels use opposite mapping (left side => right anchor, right side => left anchor).
    expect(
      anchorFromVisualSide('left', {
        rotationDeg: 0,
        mirrorX: false,
        mirrorY: false,
        left: 'right',
        right: 'left',
      }),
    ).toBe('right');

    // 180° rotation swaps the visual side, so anchor should swap too.
    expect(
      anchorFromVisualSide('left', {
        rotationDeg: 180,
        mirrorX: false,
        mirrorY: false,
        left: 'right',
        right: 'left',
      }),
    ).toBe('left');

    // Horizontal mirror also swaps visual side.
    expect(
      anchorFromVisualSide('right', {
        rotationDeg: 0,
        mirrorX: true,
        mirrorY: false,
        left: 'right',
        right: 'left',
      }),
    ).toBe('right');
  });

  it('uses center anchor when a side becomes vertical after transform', () => {
    expect(
      anchorFromVisualSide('left', {
        rotationDeg: 90,
        mirrorX: false,
        mirrorY: false,
        left: 'right',
        right: 'left',
      }),
    ).toBe('center');
  });

  it('keeps component/module pin labels inside the visual body edge', () => {
    // Component/module pin names use direct mapping (left => left anchor, right => right anchor).
    expect(
      anchorFromVisualSide('right', {
        rotationDeg: 0,
        mirrorX: false,
        mirrorY: false,
        left: 'left',
        right: 'right',
      }),
    ).toBe('right');

    // After 180° rotate, visual side flips so anchor should flip.
    expect(
      anchorFromVisualSide('right', {
        rotationDeg: 180,
        mirrorX: false,
        mirrorY: false,
        left: 'left',
        right: 'right',
      }),
    ).toBe('left');
  });
});
