import { describe, expect, it } from 'vitest';
import { derivePortsFromModule, type SchematicModule } from '../schematic-viewer/types/schematic';

function makeModule(signals: string[]): SchematicModule {
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
        id: 'i2c_port',
        name: 'i2c',
        side: 'left',
        category: 'i2c',
        interfaceType: 'I2C',
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

describe('derivePortsFromModule signal ordering', () => {
  it('applies per-port signal order overrides', () => {
    const mod = makeModule(['scl', 'sda']);
    const [port] = derivePortsFromModule(mod, {
      i2c_port: ['sda', 'scl'],
    });

    expect(port.signals).toEqual(['sda', 'scl']);
    expect(port.signalPins?.sda.y).toBeGreaterThan(port.signalPins?.scl.y);
  });

  it('ignores invalid overrides and keeps default order', () => {
    const mod = makeModule(['scl', 'sda']);
    const [port] = derivePortsFromModule(mod, {
      i2c_port: ['scl', 'bogus'],
    });

    expect(port.signals).toEqual(['scl', 'sda']);
  });
});
