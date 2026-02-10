import { describe, expect, it } from 'vitest';
import type { SchematicComponent } from '../schematic-viewer/types/schematic';
import { getTunedPinGeometry } from '../schematic-viewer/three/symbolRenderGeometry';

const TEST_COMPONENT: SchematicComponent = {
  kind: 'component',
  id: 'fixture_r',
  name: 'fixture_r',
  designator: 'R1',
  reference: 'R',
  symbolFamily: 'resistor',
  packageCode: '0402',
  bodyWidth: 5.08,
  bodyHeight: 2.04,
  pins: [
    {
      number: '1',
      name: 'A',
      side: 'left',
      electricalType: 'passive',
      category: 'signal',
      x: -5.08,
      y: 0,
      bodyX: -2.54,
      bodyY: 0,
    },
    {
      number: '2',
      name: 'B',
      side: 'right',
      electricalType: 'passive',
      category: 'signal',
      x: 5.08,
      y: 0,
      bodyX: 2.54,
      bodyY: 0,
    },
  ],
};

describe('symbolRenderGeometry.getTunedPinGeometry', () => {
  it('keeps external pin connection fixed while moving body-side attachment', () => {
    const pin = TEST_COMPONENT.pins[0];
    const base = getTunedPinGeometry(
      TEST_COMPONENT,
      pin,
      'resistor',
      { x: -1.2, y: 0 },
      { bodyOffsetX: 0, bodyOffsetY: 0, bodyRotationDeg: 0, leadDelta: 0 },
      { x: 0, y: 0 },
    );
    const tuned = getTunedPinGeometry(
      TEST_COMPONENT,
      pin,
      'resistor',
      { x: -1.2, y: 0 },
      { bodyOffsetX: 0, bodyOffsetY: 0, bodyRotationDeg: 0, leadDelta: 0.5 },
      { x: 0, y: 0 },
    );

    expect(tuned.x).toBeCloseTo(base.x, 6);
    expect(tuned.y).toBeCloseTo(base.y, 6);
    expect(Math.hypot(tuned.bodyX, tuned.bodyY)).toBeCloseTo(
      Math.hypot(base.bodyX, base.bodyY) - 0.5,
      6,
    );
  });

  it('clamps large positive leadDelta so attachment does not cross the body center', () => {
    const pin = TEST_COMPONENT.pins[0];
    const tuned = getTunedPinGeometry(
      TEST_COMPONENT,
      pin,
      'resistor',
      { x: -1.2, y: 0 },
      { bodyOffsetX: 0, bodyOffsetY: 0, bodyRotationDeg: 0, leadDelta: 100 },
      { x: 0, y: 0 },
    );

    expect(tuned.bodyX).toBeLessThan(0);
    expect(Math.hypot(tuned.bodyX, tuned.bodyY)).toBeGreaterThanOrEqual(0.04 - 1e-6);
  });

  it('clamps large negative leadDelta so attachment stays inside the pin endpoint', () => {
    const pin = TEST_COMPONENT.pins[0];
    const tuned = getTunedPinGeometry(
      TEST_COMPONENT,
      pin,
      'resistor',
      { x: -1.2, y: 0 },
      { bodyOffsetX: 0, bodyOffsetY: 0, bodyRotationDeg: 0, leadDelta: -100 },
      { x: 0, y: 0 },
    );

    expect(Math.abs(tuned.bodyX)).toBeLessThan(Math.abs(tuned.x));
    expect(Math.abs(tuned.bodyX)).toBeCloseTo(Math.abs(tuned.x) - 0.08, 6);
  });
});
