import { describe, expect, it } from 'vitest';
import {
  derivePortsFromModule,
  getNormalizedComponentPinGeometry,
  getPortPinNumbers,
  getRootSheet,
  type SchematicModule,
} from '../schematic-viewer/types/schematic';

function makeModuleWithInterface(
  id: string,
  signals?: string[],
): SchematicModule {
  return {
    kind: 'module',
    id: 'child_mod',
    name: 'child_mod',
    typeName: 'ChildMod',
    componentCount: 0,
    bodyWidth: 20,
    bodyHeight: 10,
    interfacePins: [
      {
        id,
        name: id,
        side: 'left',
        category: 'signal',
        interfaceType: 'Signal',
        x: 0,
        y: 0,
        bodyX: 0,
        bodyY: 0,
        signals,
      },
    ],
    sheet: {
      modules: [],
      components: [],
      nets: [],
    },
  };
}

describe('schematic model contracts', () => {
  it('exposes canonical port pin numbers for single-signal ports', () => {
    const mod = makeModuleWithInterface('reset');
    const [port] = derivePortsFromModule(mod);

    expect(getPortPinNumbers(port)).toEqual(['1']);
  });

  it('exposes canonical port pin numbers for breakout ports', () => {
    const mod = makeModuleWithInterface('i2c', ['scl', 'sda']);
    const [port] = derivePortsFromModule(mod);

    expect(getPortPinNumbers(port)).toEqual(['scl', 'sda', '1']);
    expect(port.signalPins?.scl?.x ?? 0).toBeGreaterThan(0);
    expect(port.signalPins?.sda?.x ?? 0).toBeGreaterThan(0);
    expect(port.pinX).toBeLessThan(0);
    // Line-level pin should sit on a signal row so both handles land on-grid.
    expect(port.pinY).toBe(port.signalPins?.scl?.y);
  });

  it('rejects malformed schematic payloads without a root sheet', () => {
    expect(() => getRootSheet({ version: '2.0' } as any)).toThrow(
      'missing root sheet',
    );
  });

  it('normalizes mixed-phase component pins onto a unified pin grid', () => {
    const component = {
      kind: 'component' as const,
      id: 'u1',
      name: 'u1',
      designator: 'U1',
      reference: 'U',
      bodyWidth: 20,
      bodyHeight: 10,
      pins: [
        {
          number: '1',
          name: 'L',
          side: 'left' as const,
          electricalType: 'passive' as const,
          category: 'signal' as const,
          x: -9.54,
          y: 34.29,
          bodyX: -8.54,
          bodyY: 34.29,
        },
        {
          number: '2',
          name: 'R',
          side: 'right' as const,
          electricalType: 'passive' as const,
          category: 'signal' as const,
          x: 9.54,
          y: 35.56,
          bodyX: 8.54,
          bodyY: 35.56,
        },
      ],
    };

    const left = getNormalizedComponentPinGeometry(component, component.pins[0]);
    const right = getNormalizedComponentPinGeometry(component, component.pins[1]);
    const phase = (v: number) => ((v % 2.54) + 2.54) % 2.54;

    expect(phase(left.y)).toBeCloseTo(phase(right.y), 6);
  });
});
