import { describe, expect, it } from 'vitest';
import { routeHitsObstacle, type RouteObstacle } from '../schematic-viewer/three/routeObstacles';

const BOX: RouteObstacle = {
  id: 'u1',
  minX: 4,
  minY: -2,
  maxX: 8,
  maxY: 2,
};

describe('routeHitsObstacle', () => {
  it('detects horizontal route overlap through an obstacle box', () => {
    const route: [number, number, number][] = [
      [0, 0, 0],
      [10, 0, 0],
    ];

    expect(routeHitsObstacle(route, [BOX])).toBe(true);
  });

  it('detects vertical route overlap through an obstacle box', () => {
    const route: [number, number, number][] = [
      [6, -6, 0],
      [6, 6, 0],
    ];

    expect(routeHitsObstacle(route, [BOX])).toBe(true);
  });

  it('ignores obstacles not intersected by the route', () => {
    const route: [number, number, number][] = [
      [0, 3, 0],
      [10, 3, 0],
    ];

    expect(routeHitsObstacle(route, [BOX])).toBe(false);
  });

  it('supports ignoring endpoint owner obstacles', () => {
    const route: [number, number, number][] = [
      [0, 0, 0],
      [10, 0, 0],
    ];

    expect(routeHitsObstacle(route, [BOX], new Set(['u1']))).toBe(false);
  });
});
