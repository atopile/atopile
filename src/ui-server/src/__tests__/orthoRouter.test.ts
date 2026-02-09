import { describe, expect, it } from 'vitest';
import {
  routeOrthogonalWithHeuristics,
  type RouteSegment,
} from '../schematic-viewer/lib/orthoRouter';

const PITCH = 2.54;

describe('routeOrthogonalWithHeuristics', () => {
  it('nudges a horizontal direct route off an occupied colinear lane', () => {
    const existing: RouteSegment[] = [
      { x1: 5, y1: 0, x2: 15, y2: 0, isHorizontal: true, netId: 'occupied' },
    ];

    const result = routeOrthogonalWithHeuristics(
      0, 0, 'right',
      20, 0, 'left',
      { existingSegments: existing, preferredSpacing: PITCH },
    );

    expect(result.quality.overlaps).toBe(0);
    // Route should have taken a dogleg lane rather than the original y=0 trunk.
    const interior = result.route.slice(2, -2);
    expect(interior.some((p) => Math.abs(p[1]) > 0.1)).toBe(true);
  });

  it('nudges a vertical direct route off an occupied colinear lane', () => {
    const existing: RouteSegment[] = [
      { x1: 0, y1: 5, x2: 0, y2: 15, isHorizontal: false, netId: 'occupied' },
    ];

    const result = routeOrthogonalWithHeuristics(
      0, 0, 'top',
      0, 20, 'bottom',
      { existingSegments: existing, preferredSpacing: PITCH },
    );

    expect(result.quality.overlaps).toBe(0);
    const interior = result.route.slice(2, -2);
    expect(interior.some((p) => Math.abs(p[0]) > 0.1)).toBe(true);
  });

  it('keeps the geometric shortest route when there is no lane overlap', () => {
    const existing: RouteSegment[] = [
      // Orthogonal crossing candidate through the direct route.
      { x1: 10, y1: -6, x2: 10, y2: 6, isHorizontal: false, netId: 'crossing_only' },
    ];

    const result = routeOrthogonalWithHeuristics(
      0, 0, 'right',
      20, 0, 'left',
      { existingSegments: existing, preferredSpacing: PITCH },
    );

    expect(result.quality.overlaps).toBe(0);
    // Base direct route is pin A -> stub A -> stub B -> pin B.
    expect(result.route).toHaveLength(4);
    expect(result.route[1][1]).toBeCloseTo(0, 6);
    expect(result.route[2][1]).toBeCloseTo(0, 6);
  });

  it('routes around blocked obstacle boxes when searching the shortest free path', () => {
    const result = routeOrthogonalWithHeuristics(
      0, 0, 'right',
      20, 0, 'left',
      {
        obstacles: [
          { id: 'u1', minX: 8, minY: -2, maxX: 12, maxY: 2 },
        ],
      },
    );

    // Should detour off the direct y=0 corridor.
    const interior = result.route.slice(2, -2);
    expect(interior.some((p) => Math.abs(p[1]) > 0.1)).toBe(true);
  });

  it('respects ignored obstacles so endpoint components do not block exit routing', () => {
    const result = routeOrthogonalWithHeuristics(
      0, 0, 'right',
      20, 0, 'left',
      {
        obstacles: [
          { id: 'u1', minX: 8, minY: -2, maxX: 12, maxY: 2 },
        ],
        ignoredObstacleIds: new Set(['u1']),
      },
    );

    // With the only obstacle ignored, route should remain straight.
    expect(result.route[1][1]).toBeCloseTo(0, 6);
    expect(result.route[result.route.length - 2][1]).toBeCloseTo(0, 6);
  });
});
