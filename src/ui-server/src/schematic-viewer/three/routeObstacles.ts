/**
 * Obstacle intersection helpers for schematic routes.
 *
 * A route is considered obstructed when any orthogonal segment overlaps the
 * interior projection of an obstacle AABB.
 */

export interface RouteObstacle {
  id: string;
  minX: number;
  minY: number;
  maxX: number;
  maxY: number;
}

function overlaps1D(a0: number, a1: number, b0: number, b1: number): boolean {
  const minA = Math.min(a0, a1);
  const maxA = Math.max(a0, a1);
  return maxA >= b0 && minA <= b1;
}

function segmentHitsObstacle(
  x1: number,
  y1: number,
  x2: number,
  y2: number,
  obstacle: RouteObstacle,
): boolean {
  // Ignore degenerate segments.
  if (Math.abs(x1 - x2) < 1e-6 && Math.abs(y1 - y2) < 1e-6) return false;

  // Horizontal segment.
  if (Math.abs(y1 - y2) < 1e-6) {
    return y1 >= obstacle.minY &&
      y1 <= obstacle.maxY &&
      overlaps1D(x1, x2, obstacle.minX, obstacle.maxX);
  }

  // Vertical segment.
  if (Math.abs(x1 - x2) < 1e-6) {
    return x1 >= obstacle.minX &&
      x1 <= obstacle.maxX &&
      overlaps1D(y1, y2, obstacle.minY, obstacle.maxY);
  }

  // Fallback for non-orthogonal segments (should not happen for ortho routing):
  // test against obstacle bounding box.
  const segMinX = Math.min(x1, x2);
  const segMaxX = Math.max(x1, x2);
  const segMinY = Math.min(y1, y2);
  const segMaxY = Math.max(y1, y2);
  return segMaxX >= obstacle.minX &&
    segMinX <= obstacle.maxX &&
    segMaxY >= obstacle.minY &&
    segMinY <= obstacle.maxY;
}

/**
 * True if any route segment intersects any non-ignored obstacle.
 */
export function routeHitsObstacle(
  route: [number, number, number][],
  obstacles: RouteObstacle[],
  ignoredIds: Set<string> = new Set(),
): boolean {
  if (route.length < 2 || obstacles.length === 0) return false;

  for (let i = 1; i < route.length; i++) {
    const [x1, y1] = route[i - 1];
    const [x2, y2] = route[i];
    for (const obstacle of obstacles) {
      if (ignoredIds.has(obstacle.id)) continue;
      if (segmentHitsObstacle(x1, y1, x2, y2, obstacle)) return true;
    }
  }
  return false;
}

