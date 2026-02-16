import { describe, expect, it } from 'vitest';
import type { SchematicInterfacePin } from '../schematic-viewer/types/schematic';
import { getModuleRenderSize } from '../schematic-viewer/utils/moduleInterfaces';

function makePin(id: string, side: SchematicInterfacePin['side']): SchematicInterfacePin {
  return {
    id,
    name: id,
    side,
    category: 'signal',
    interfaceType: 'Signal',
    x: 0,
    y: 0,
    bodyX: 0,
    bodyY: 0,
  };
}

describe('getModuleRenderSize', () => {
  it('uses a smaller minimum height for sparse modules', () => {
    const size = getModuleRenderSize({
      interfacePins: [makePin('out', 'right')],
    });

    expect(size.height).toBe(7.62);
  });

  it('scales height based on the most populated vertical side', () => {
    const size = getModuleRenderSize({
      interfacePins: [
        makePin('r1', 'right'),
        makePin('r2', 'right'),
        makePin('r3', 'right'),
        makePin('r4', 'right'),
        makePin('l1', 'left'),
      ],
    });

    // (4 - 1) * 2.54 + 2 * 2.54
    expect(size.height).toBe(12.7);
  });

  it('keeps height driven by left/right density', () => {
    const size = getModuleRenderSize({
      interfacePins: [
        makePin('t1', 'top'),
        makePin('t2', 'top'),
        makePin('t3', 'top'),
        makePin('l1', 'left'),
      ],
    });

    expect(size.height).toBe(7.62);
  });
});
