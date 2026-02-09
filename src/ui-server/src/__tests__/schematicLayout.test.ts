import { describe, expect, it } from 'vitest';
import { autoLayoutSheet } from '../schematic-viewer/lib/schematicLayout';
import type {
  NetType,
  SchematicComponent,
  SchematicModule,
  SchematicPin,
  SchematicPort,
  SchematicSheet,
} from '../schematic-viewer/types/schematic';
import {
  BREAKOUT_PIN_SPACING,
  getComponentGridAlignmentOffset,
  getPortGridAlignmentOffset,
  PIN_GRID_MM,
  PORT_H,
  PORT_STUB_LEN,
  PORT_W,
  transformPinOffset,
} from '../schematic-viewer/types/schematic';

function makePin(
  number: string,
  name: string,
  side: 'left' | 'right' | 'top' | 'bottom',
  category: 'power' | 'ground' | 'signal' = 'signal',
  {
    x = 0,
    y = 0,
    bodyX = 0,
    bodyY = 0,
  }: { x?: number; y?: number; bodyX?: number; bodyY?: number } = {},
): SchematicPin {
  return {
    number,
    name,
    side,
    electricalType: 'passive',
    category,
    x,
    y,
    bodyX,
    bodyY,
  };
}

function makeComponent(
  id: string,
  reference: string,
  width: number,
  height: number,
  pins: SchematicPin[],
): SchematicComponent {
  return {
    kind: 'component',
    id,
    name: id,
    designator: id.toUpperCase(),
    reference,
    pins,
    bodyWidth: width,
    bodyHeight: height,
  };
}

function makeModule(
  id: string,
  width: number,
  height: number,
): SchematicModule {
  return {
    kind: 'module',
    id,
    name: id,
    typeName: id,
    componentCount: 0,
    interfacePins: [],
    bodyWidth: width,
    bodyHeight: height,
    sheet: {
      modules: [],
      components: [],
      nets: [],
    },
  };
}

function net(
  id: string,
  type: NetType,
  pins: Array<{ componentId: string; pinNumber: string }>,
) {
  return { id, name: id, type, pins };
}

function makeSinglePort(
  id: string,
  side: 'left' | 'right' | 'top' | 'bottom',
): SchematicPort {
  let pinX = 0;
  let pinY = 0;
  let pinSide: 'left' | 'right' | 'top' | 'bottom' = 'right';

  switch (side) {
    case 'left':
      pinX = PORT_W / 2 + PORT_STUB_LEN;
      pinSide = 'right';
      break;
    case 'right':
      pinX = -(PORT_W / 2 + PORT_STUB_LEN);
      pinSide = 'left';
      break;
    case 'top':
      pinY = -(PORT_H / 2 + PORT_STUB_LEN);
      pinSide = 'bottom';
      break;
    case 'bottom':
      pinY = PORT_H / 2 + PORT_STUB_LEN;
      pinSide = 'top';
      break;
  }

  return {
    kind: 'port',
    id,
    name: id,
    side,
    category: 'signal',
    interfaceType: 'Signal',
    bodyWidth: PORT_W,
    bodyHeight: PORT_H,
    pinX,
    pinY,
    pinSide,
  };
}

function makeBreakoutPort(
  id: string,
  signals: string[],
): SchematicPort {
  const signalPins: Record<string, { x: number; y: number }> = {};
  for (let i = 0; i < signals.length; i++) {
    signalPins[signals[i]] = {
      x: 8,
      y: (signals.length - 1) * BREAKOUT_PIN_SPACING / 2 - i * BREAKOUT_PIN_SPACING,
    };
  }

  return {
    kind: 'port',
    id,
    name: id,
    side: 'left',
    category: 'i2c',
    interfaceType: 'I2C',
    bodyWidth: 12,
    bodyHeight: Math.max(PORT_H, (signals.length - 1) * BREAKOUT_PIN_SPACING + 1.2),
    pinX: -8,
    pinY: 0,
    pinSide: 'right',
    signals: [...signals],
    signalPins,
  };
}

describe('schematicLayout decoupling placement', () => {
  it('lays out each decoupling group as a horizontal row with top alignment', () => {
    const sheet: SchematicSheet = {
      modules: [],
      components: [
        makeComponent(
          'u1',
          'U',
          20,
          20,
          [
            makePin('1', 'VCCA', 'left', 'power'),
            makePin('2', 'GND', 'left', 'ground'),
            makePin('3', 'VCCB', 'left', 'power'),
          ],
        ),
        // Same power net group
        makeComponent(
          'c1',
          'C',
          5.08,
          5.08,
          [
            makePin('1', 'P', 'left', 'power'),
            makePin('2', 'G', 'right', 'ground'),
          ],
        ),
        makeComponent(
          'c2',
          'C',
          7.62,
          10.16,
          [
            makePin('1', 'P', 'left', 'power'),
            makePin('2', 'G', 'right', 'ground'),
          ],
        ),
        // Different power net group
        makeComponent(
          'c3',
          'C',
          5.08,
          5.08,
          [
            makePin('1', 'P', 'left', 'power'),
            makePin('2', 'G', 'right', 'ground'),
          ],
        ),
      ],
      nets: [
        net('pwr_a', 'power', [
          { componentId: 'u1', pinNumber: '1' },
          { componentId: 'c1', pinNumber: '1' },
          { componentId: 'c2', pinNumber: '1' },
        ]),
        net('pwr_b', 'power', [
          { componentId: 'u1', pinNumber: '3' },
          { componentId: 'c3', pinNumber: '1' },
        ]),
        net('gnd', 'ground', [
          { componentId: 'u1', pinNumber: '2' },
          { componentId: 'c1', pinNumber: '2' },
          { componentId: 'c2', pinNumber: '2' },
          { componentId: 'c3', pinNumber: '2' },
        ]),
      ],
    };

    const positions = autoLayoutSheet(sheet, [], []);

    const c1 = positions.c1;
    const c2 = positions.c2;
    const c3 = positions.c3;
    expect(c1).toBeDefined();
    expect(c2).toBeDefined();
    expect(c3).toBeDefined();

    // Same decoupling group should lay out left-to-right.
    expect(c2.x).toBeGreaterThan(c1.x);

    // Same decoupling group should share the same top edge.
    const c1Top = c1.y + 5.08 / 2;
    const c2Top = c2.y + 10.16 / 2;
    expect(Math.abs(c1Top - c2Top)).toBeLessThan(0.001);

    // Different decoupling groups should stack vertically (upward, away from main body).
    const c3Top = c3.y + 5.08 / 2;
    expect(c3Top).toBeGreaterThan(c1Top);
  });
});

describe('schematicLayout main-item collision handling', () => {
  function rotatedSize(
    width: number,
    height: number,
    rotation?: number,
  ): { w: number; h: number } {
    const r = ((Math.round((rotation ?? 0) / 90) * 90) % 360 + 360) % 360;
    return r === 90 || r === 270 ? { w: height, h: width } : { w: width, h: height };
  }

  function overlaps(
    a: { x: number; y: number; w: number; h: number },
    b: { x: number; y: number; w: number; h: number },
  ): boolean {
    const minAx = a.x - a.w / 2;
    const maxAx = a.x + a.w / 2;
    const minAy = a.y - a.h / 2;
    const maxAy = a.y + a.h / 2;
    const minBx = b.x - b.w / 2;
    const maxBx = b.x + b.w / 2;
    const minBy = b.y - b.h / 2;
    const maxBy = b.y + b.h / 2;
    return Math.min(maxAx, maxBx) > Math.max(minAx, minBx) &&
      Math.min(maxAy, maxBy) > Math.max(minAy, minBy);
  }

  it('keeps unmatched modules/components non-overlapping after post-layout rotations', () => {
    const u1 = makeComponent(
      'u1',
      'U',
      24,
      18,
      [
        makePin('1', 'VCC', 'left', 'power', { x: -7.62, y: 2.54, bodyX: -7, bodyY: 2.54 }),
        makePin('2', 'GND', 'left', 'ground', { x: -7.62, y: -2.54, bodyX: -7, bodyY: -2.54 }),
      ],
    );
    const r1 = makeComponent(
      'r1',
      'R',
      20,
      6,
      [
        makePin('1', 'A', 'left', 'power', { x: -5.08, y: 0, bodyX: -5, bodyY: 0 }),
        makePin('2', 'B', 'right', 'ground', { x: 5.08, y: 0, bodyX: 5, bodyY: 0 }),
      ],
    );
    const r2 = makeComponent(
      'r2',
      'R',
      20,
      6,
      [
        makePin('1', 'A', 'left', 'power', { x: -5.08, y: 0, bodyX: -5, bodyY: 0 }),
        makePin('2', 'B', 'right', 'ground', { x: 5.08, y: 0, bodyX: 5, bodyY: 0 }),
      ],
    );
    const m1 = makeModule('m1', 42, 24);
    const m2 = makeModule('m2', 40, 26);

    const sheet: SchematicSheet = {
      modules: [m1, m2],
      components: [u1, r1, r2],
      nets: [
        net('pwr', 'power', [
          { componentId: 'u1', pinNumber: '1' },
          { componentId: 'r1', pinNumber: '1' },
          { componentId: 'r2', pinNumber: '1' },
        ]),
        net('gnd', 'ground', [
          { componentId: 'u1', pinNumber: '2' },
          { componentId: 'r1', pinNumber: '2' },
          { componentId: 'r2', pinNumber: '2' },
        ]),
      ],
    };

    const positions = autoLayoutSheet(sheet, [], []);

    const items = [
      { id: 'u1', width: u1.bodyWidth, height: u1.bodyHeight },
      { id: 'r1', width: r1.bodyWidth, height: r1.bodyHeight },
      { id: 'r2', width: r2.bodyWidth, height: r2.bodyHeight },
      { id: 'm1', width: m1.bodyWidth, height: m1.bodyHeight },
      { id: 'm2', width: m2.bodyWidth, height: m2.bodyHeight },
    ].map((item) => {
      const pos = positions[item.id];
      const size = rotatedSize(item.width, item.height, pos?.rotation);
      return {
        id: item.id,
        x: pos.x,
        y: pos.y,
        w: size.w,
        h: size.h,
      };
    });

    for (let i = 0; i < items.length; i++) {
      for (let j = i + 1; j < items.length; j++) {
        expect(
          overlaps(items[i], items[j]),
          `${items[i].id} overlaps ${items[j].id}`,
        ).toBe(false);
      }
    }
  });
});

describe('schematicLayout single-port anchoring', () => {
  const ANCHOR_OFFSET = PIN_GRID_MM * 5;

  function resolvePortPinWorld(
    port: SchematicPort,
    pos: { x: number; y: number; rotation?: number; mirrorX?: boolean; mirrorY?: boolean },
  ): { x: number; y: number } {
    const align = getPortGridAlignmentOffset(port);
    const rotated = transformPinOffset(
      port.pinX + align.x,
      port.pinY + align.y,
      pos.rotation,
      pos.mirrorX,
      pos.mirrorY,
    );
    return {
      x: pos.x + rotated.x,
      y: pos.y + rotated.y,
    };
  }

  it('aligns a one-connection port to its target pin with a short straight link', () => {
    const target = makeComponent(
      'u1',
      'U',
      20,
      10,
      [makePin('1', 'RESET', 'left', 'signal', { x: -5.08, y: 0, bodyX: -5, bodyY: 0 })],
    );
    const port = makeSinglePort('reset', 'left');

    const sheet: SchematicSheet = {
      modules: [],
      components: [target],
      nets: [
        net('n_reset', 'signal', [
          { componentId: 'u1', pinNumber: '1' },
          { componentId: 'reset', pinNumber: '1' },
        ]),
      ],
    };

    const positions = autoLayoutSheet(sheet, [port], []);
    const compPos = positions.u1;
    const portPos = positions.reset;
    expect(compPos).toBeDefined();
    expect(portPos).toBeDefined();

    const compAlign = getComponentGridAlignmentOffset(target);
    const compPinWorldX = compPos.x + target.pins[0].x + compAlign.x;
    const compPinWorldY = compPos.y + target.pins[0].y + compAlign.y;

    const portPinWorld = resolvePortPinWorld(port, portPos);

    // Port should line up exactly for a straight horizontal route.
    expect(Math.abs(compPinWorldY - portPinWorld.y)).toBeLessThan(1e-6);
    // Port pin should sit five pin-pitches away from the target pin.
    expect(Math.abs(compPinWorldX - portPinWorld.x - ANCHOR_OFFSET)).toBeLessThan(1e-6);
  });

  it('anchors to the primary item pin even when the net also includes passives', () => {
    const target = makeComponent(
      'u1',
      'U',
      20,
      10,
      [
        makePin('1', 'RESET', 'left', 'signal', { x: -5.08, y: 0, bodyX: -5, bodyY: 0 }),
        makePin('2', 'AUX1', 'right', 'signal', { x: 5.08, y: 2.54, bodyX: 5, bodyY: 2.54 }),
        makePin('3', 'AUX2', 'right', 'signal', { x: 5.08, y: -2.54, bodyX: 5, bodyY: -2.54 }),
      ],
    );
    const pullup = makeComponent(
      'r1',
      'R',
      7,
      3,
      [
        makePin('1', 'A', 'left', 'signal', { x: -2.54, y: 0, bodyX: -2.5, bodyY: 0 }),
        makePin('2', 'B', 'right', 'signal', { x: 2.54, y: 0, bodyX: 2.5, bodyY: 0 }),
      ],
    );
    const aux1 = makeComponent(
      'x1',
      'J',
      6,
      4,
      [makePin('1', 'P', 'left', 'signal', { x: -2.54, y: 0, bodyX: -2.5, bodyY: 0 })],
    );
    const aux2 = makeComponent(
      'x2',
      'J',
      6,
      4,
      [makePin('1', 'P', 'left', 'signal', { x: -2.54, y: 0, bodyX: -2.5, bodyY: 0 })],
    );
    const port = makeSinglePort('reset', 'right');

    const sheet: SchematicSheet = {
      modules: [],
      components: [target, pullup, aux1, aux2],
      nets: [
        net('n_reset', 'signal', [
          { componentId: 'u1', pinNumber: '1' },
          { componentId: 'r1', pinNumber: '1' },
          { componentId: 'reset', pinNumber: '1' },
        ]),
        net('n_aux1', 'signal', [
          { componentId: 'u1', pinNumber: '2' },
          { componentId: 'x1', pinNumber: '1' },
        ]),
        net('n_aux2', 'signal', [
          { componentId: 'u1', pinNumber: '3' },
          { componentId: 'x2', pinNumber: '1' },
        ]),
      ],
    };

    const positions = autoLayoutSheet(sheet, [port], []);
    const compPos = positions.u1;
    const portPos = positions.reset;
    expect(compPos).toBeDefined();
    expect(portPos).toBeDefined();

    const compAlign = getComponentGridAlignmentOffset(target);
    const compPinWorldX = compPos.x + target.pins[0].x + compAlign.x;
    const compPinWorldY = compPos.y + target.pins[0].y + compAlign.y;

    const portPinWorld = resolvePortPinWorld(port, portPos);

    // Keep the route straight.
    expect(Math.abs(compPinWorldY - portPinWorld.y)).toBeLessThan(1e-6);
    // Port should orient to face the target pin side, independent of its original side metadata.
    expect(portPinWorld.x).toBeLessThan(compPinWorldX);
    expect(Math.abs(compPinWorldX - portPinWorld.x - ANCHOR_OFFSET)).toBeLessThan(1e-6);
    expect((portPos.rotation || 0) % 360).toBe(180);
  });
});

describe('schematicLayout multi-port anchoring', () => {
  it('matches contiguous target pin runs, suggests signal order, and orients breakout ports', () => {
    const target = makeComponent(
      'u1',
      'U',
      16,
      10,
      [
        makePin('11', 'SCL', 'right', 'signal', { x: 5.08, y: 2.54, bodyX: 5, bodyY: 2.54 }),
        makePin('12', 'SDA', 'right', 'signal', { x: 5.08, y: 0, bodyX: 5, bodyY: 0 }),
        makePin('13', 'INT', 'right', 'signal', { x: 5.08, y: -2.54, bodyX: 5, bodyY: -2.54 }),
      ],
    );
    const port = makeBreakoutPort('i2c', ['sda', 'scl', 'int']);

    const sheet: SchematicSheet = {
      modules: [],
      components: [target],
      nets: [
        net('n_scl', 'signal', [
          { componentId: 'u1', pinNumber: '11' },
          { componentId: 'i2c', pinNumber: 'scl' },
        ]),
        net('n_sda', 'signal', [
          { componentId: 'u1', pinNumber: '12' },
          { componentId: 'i2c', pinNumber: 'sda' },
        ]),
        net('n_int', 'signal', [
          { componentId: 'u1', pinNumber: '13' },
          { componentId: 'i2c', pinNumber: 'int' },
        ]),
      ],
    };

    const suggestedOrders: Record<string, string[]> = {};
    const positions = autoLayoutSheet(sheet, [port], [], suggestedOrders);
    const compPos = positions.u1;
    const portPos = positions.i2c;
    expect(compPos).toBeDefined();
    expect(portPos).toBeDefined();

    expect(suggestedOrders.i2c).toBeDefined();
    expect([...(suggestedOrders.i2c || [])].sort()).toEqual(['int', 'scl', 'sda']);
    expect([...(port.signals || [])].sort()).toEqual(['int', 'scl', 'sda']);
    expect((portPos.rotation || 0) % 360).toBe(180);

    const compAlign = getComponentGridAlignmentOffset(target);
    const compTopPinX = compPos.x + target.pins[0].x + compAlign.x;
    const compTopPinY = compPos.y + target.pins[0].y + compAlign.y;

    const portAlign = getPortGridAlignmentOffset(port);
    const signalLocal = port.signalPins?.scl;
    expect(signalLocal).toBeDefined();
    const signalRot = transformPinOffset(
      (signalLocal?.x ?? 0) + portAlign.x,
      (signalLocal?.y ?? 0) + portAlign.y,
      portPos.rotation,
      portPos.mirrorX,
      portPos.mirrorY,
    );
    const portTopPinX = portPos.x + signalRot.x;
    const portTopPinY = portPos.y + signalRot.y;

    // Same straight-line policy as single ports: pin stays 5 pitches away.
    expect(Math.abs(portTopPinX - compTopPinX - PIN_GRID_MM * 5)).toBeLessThan(1e-6);
    expect(Math.abs(portTopPinY - compTopPinY)).toBeLessThan(1e-6);
  });
});
