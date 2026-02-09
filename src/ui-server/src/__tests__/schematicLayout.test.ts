import { describe, expect, it } from 'vitest';
import { autoLayoutSheet } from '../schematic-viewer/lib/schematicLayout';
import type {
  NetType,
  SchematicComponent,
  SchematicPin,
  SchematicPort,
  SchematicSheet,
} from '../schematic-viewer/types/schematic';
import {
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

    // Different decoupling groups should stack vertically.
    const c3Top = c3.y + 5.08 / 2;
    expect(c3Top).toBeLessThan(c1Top);
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
