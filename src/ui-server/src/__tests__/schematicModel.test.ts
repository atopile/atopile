import { describe, expect, it } from 'vitest';
import {
  derivePowerPorts,
  derivePortsFromModule,
  getNormalizedComponentPinGeometry,
  getPortPinNumbers,
  getRootSheet,
  type SchematicSheet,
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
    // Right-side pin keeps its edge on the right body boundary (bodyX fixed)
    // while row shifts track the normalized pin Y.
    expect(right.bodyX).toBeCloseTo(component.pins[1].bodyX, 6);
    expect(right.bodyY).toBeCloseTo(right.y, 6);
  });

  it('derives power symbols for component-only HV/LV nets', () => {
    const sheet: SchematicSheet = {
      modules: [],
      components: [
        {
          kind: 'component',
          id: 'u1',
          name: 'u1',
          designator: 'U1',
          reference: 'U',
          bodyWidth: 10,
          bodyHeight: 6,
          pins: [
            {
              number: '1',
              name: 'HV',
              side: 'left',
              electricalType: 'power_in',
              category: 'power',
              x: -2.54,
              y: 0,
              bodyX: -2,
              bodyY: 0,
            },
            {
              number: '2',
              name: 'LV',
              side: 'left',
              electricalType: 'power_in',
              category: 'ground',
              x: -2.54,
              y: -2.54,
              bodyX: -2,
              bodyY: -2.54,
            },
          ],
        },
      ],
      nets: [
        {
          id: 'hv',
          name: 'hv',
          type: 'power',
          pins: [{ componentId: 'u1', pinNumber: '1' }],
        },
        {
          id: 'lv',
          name: 'lv',
          type: 'ground',
          pins: [{ componentId: 'u1', pinNumber: '2' }],
        },
      ],
    };

    const ports = derivePowerPorts(sheet);
    expect(ports).toHaveLength(2);
    expect(ports.map((p) => p.name).sort()).toEqual(['hv', 'lv']);
    expect(ports.every((p) => p.componentId === 'u1')).toBe(true);
  });

  it('filters deprecated VCC/GND power symbols while keeping HV/LV', () => {
    const sheet: SchematicSheet = {
      modules: [],
      components: [
        {
          kind: 'component',
          id: 'u1',
          name: 'u1',
          designator: 'U1',
          reference: 'U',
          bodyWidth: 10,
          bodyHeight: 6,
          pins: [
            {
              number: '1',
              name: 'VCC',
              side: 'left',
              electricalType: 'power_in',
              category: 'power',
              x: -2.54,
              y: 0,
              bodyX: -2,
              bodyY: 0,
            },
            {
              number: '2',
              name: 'GND',
              side: 'left',
              electricalType: 'power_in',
              category: 'ground',
              x: -2.54,
              y: -2.54,
              bodyX: -2,
              bodyY: -2.54,
            },
            {
              number: '3',
              name: 'HV',
              side: 'left',
              electricalType: 'power_in',
              category: 'power',
              x: -2.54,
              y: -5.08,
              bodyX: -2,
              bodyY: -5.08,
            },
            {
              number: '4',
              name: 'LV',
              side: 'left',
              electricalType: 'power_in',
              category: 'ground',
              x: -2.54,
              y: -7.62,
              bodyX: -2,
              bodyY: -7.62,
            },
          ],
        },
      ],
      nets: [
        {
          id: 'VCC',
          name: 'VCC',
          type: 'power',
          pins: [{ componentId: 'u1', pinNumber: '1' }],
        },
        {
          id: 'gnd',
          name: 'gnd',
          type: 'ground',
          pins: [{ componentId: 'u1', pinNumber: '2' }],
        },
        {
          id: 'hv',
          name: 'hv',
          type: 'power',
          pins: [{ componentId: 'u1', pinNumber: '3' }],
        },
        {
          id: 'lv',
          name: 'lv',
          type: 'ground',
          pins: [{ componentId: 'u1', pinNumber: '4' }],
        },
      ],
    };

    const ports = derivePowerPorts(sheet);
    expect(ports).toHaveLength(2);
    expect(ports.map((p) => p.name).sort()).toEqual(['hv', 'lv']);
  });

  it('skips power symbols for nets that touch module-level endpoints', () => {
    const sheet: SchematicSheet = {
      modules: [
        {
          kind: 'module',
          id: 'm1',
          name: 'm1',
          typeName: 'M1',
          componentCount: 0,
          bodyWidth: 20,
          bodyHeight: 12,
          interfacePins: [],
          sheet: { modules: [], components: [], nets: [] },
        },
      ],
      components: [
        {
          kind: 'component',
          id: 'u1',
          name: 'u1',
          designator: 'U1',
          reference: 'U',
          bodyWidth: 10,
          bodyHeight: 6,
          pins: [
            {
              number: '1',
              name: 'VCC',
              side: 'left',
              electricalType: 'power_in',
              category: 'power',
              x: -2.54,
              y: 0,
              bodyX: -2,
              bodyY: 0,
            },
          ],
        },
      ],
      nets: [
        {
          id: 'vcc',
          name: 'VCC',
          type: 'power',
          pins: [
            { componentId: 'u1', pinNumber: '1' },
            { componentId: 'm1', pinNumber: 'power' },
          ],
        },
      ],
    };

    expect(derivePowerPorts(sheet)).toHaveLength(0);
  });
});
