import {
  isBusInterface,
  getInterfaceDotRadius,
  getInterfaceNameInset,
  getInterfaceParallelOffset,
  getInterfaceStrokeStyle,
} from '../schematic-viewer/three/interfaceVisuals';

describe('interfaceVisuals', () => {
  it('classifies single vs bus interfaces consistently', () => {
    expect(isBusInterface(undefined)).toBe(false);
    expect(isBusInterface(['sda'])).toBe(false);
    expect(isBusInterface(['scl', 'sda'])).toBe(true);
  });

  it('uses larger endpoint + inset for bus interfaces', () => {
    expect(getInterfaceDotRadius(['a'])).toBeLessThan(getInterfaceDotRadius(['a', 'b']));
    expect(getInterfaceNameInset(['a'])).toBeLessThan(getInterfaceNameInset(['a', 'b']));
  });

  it('computes perpendicular offset for parallel bus strokes', () => {
    const off = getInterfaceParallelOffset(0, 0, 10, 0, 0.2);
    expect(off.x).toBeCloseTo(0);
    expect(off.y).toBeCloseTo(0.2);
  });

  it('returns two-stroke style only for buses', () => {
    const single = getInterfaceStrokeStyle(undefined, false);
    expect(single.secondaryWidth).toBeUndefined();

    const bus = getInterfaceStrokeStyle(['clk', 'data'], false);
    expect(bus.secondaryWidth).toBeDefined();
    expect(bus.primaryWidth).toBeGreaterThan(single.primaryWidth);
  });
});

