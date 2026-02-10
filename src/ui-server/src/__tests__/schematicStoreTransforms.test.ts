import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { ComponentPosition } from '../schematic-viewer/types/schematic';
import { useSchematicStore } from '../schematic-viewer/stores/schematicStore';

function setBaseState(
  positions: Record<string, ComponentPosition>,
  selectedComponentIds: string[],
) {
  useSchematicStore.setState({
    currentPath: [],
    positions,
    selectedComponentIds,
    selectedComponentId: selectedComponentIds[0] ?? null,
    selectedNetId: null,
    portSignalOrders: {},
    routeOverrides: {},
  });
}

describe('schematicStore rotateSelected', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    setBaseState({}, []);
  });

  afterEach(() => {
    vi.clearAllTimers();
    vi.useRealTimers();
  });

  it('rotates a single selected item in place', () => {
    setBaseState(
      {
        '__root__:u1': { x: 12.7, y: -7.62, rotation: 180 },
      },
      ['u1'],
    );

    useSchematicStore.getState().rotateSelected();

    const next = useSchematicStore.getState().positions['__root__:u1'];
    expect(next).toBeDefined();
    expect(next.x).toBeCloseTo(12.7, 6);
    expect(next.y).toBeCloseTo(-7.62, 6);
    expect(next.rotation).toBe(270);
  });

  it('rotates multi-selection around centroid while preserving spacing', () => {
    setBaseState(
      {
        '__root__:u1': { x: 0, y: 0, rotation: 0 },
        '__root__:u2': { x: 10.16, y: 0, rotation: 90 },
        '__root__:m1': { x: 0, y: 10.16, rotation: 180 },
      },
      ['u1', 'u2', 'm1'],
    );

    useSchematicStore.getState().rotateSelected();
    const next = useSchematicStore.getState().positions;
    const u1 = next['__root__:u1'];
    const u2 = next['__root__:u2'];
    const m1 = next['__root__:m1'];
    expect(u1).toBeDefined();
    expect(u2).toBeDefined();
    expect(m1).toBeDefined();

    // Relative vectors rotate +90deg: (dx, dy) -> (-dy, dx).
    expect(u2.x - u1.x).toBeCloseTo(0, 6);
    expect(u2.y - u1.y).toBeCloseTo(10.16, 6);
    expect(m1.x - u1.x).toBeCloseTo(-10.16, 6);
    expect(m1.y - u1.y).toBeCloseTo(0, 6);

    expect(u1.rotation).toBe(90);
    expect(u2.rotation).toBe(180);
    expect(m1.rotation).toBe(270);
  });
});

describe('schematicStore mirrorSelectedX', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    setBaseState({}, []);
  });

  afterEach(() => {
    vi.clearAllTimers();
    vi.useRealTimers();
  });

  it('mirrors a single selected item in place', () => {
    setBaseState(
      {
        '__root__:u1': { x: 12.7, y: -7.62, mirrorX: false },
      },
      ['u1'],
    );

    useSchematicStore.getState().mirrorSelectedX();

    const next = useSchematicStore.getState().positions['__root__:u1'];
    expect(next).toBeDefined();
    expect(next.x).toBeCloseTo(12.7, 6);
    expect(next.y).toBeCloseTo(-7.62, 6);
    expect(next.mirrorX).toBe(true);
  });

  it('mirrors multi-selection around centroid while preserving spacing', () => {
    setBaseState(
      {
        '__root__:u1': { x: 0, y: 0, mirrorX: false },
        '__root__:u2': { x: 10.16, y: 0, mirrorX: true },
        '__root__:m1': { x: 0, y: 10.16, mirrorX: false },
      },
      ['u1', 'u2', 'm1'],
    );

    useSchematicStore.getState().mirrorSelectedX();
    const next = useSchematicStore.getState().positions;
    const u1 = next['__root__:u1'];
    const u2 = next['__root__:u2'];
    const m1 = next['__root__:m1'];
    expect(u1).toBeDefined();
    expect(u2).toBeDefined();
    expect(m1).toBeDefined();

    // Relative vectors mirror on X: (dx, dy) -> (-dx, dy).
    expect(u2.x - u1.x).toBeCloseTo(-10.16, 6);
    expect(u2.y - u1.y).toBeCloseTo(0, 6);
    expect(m1.x - u1.x).toBeCloseTo(0, 6);
    expect(m1.y - u1.y).toBeCloseTo(10.16, 6);

    expect(u1.mirrorX).toBe(true);
    expect(u2.mirrorX).toBe(false);
    expect(m1.mirrorX).toBe(true);
  });
});
