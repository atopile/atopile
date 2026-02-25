export const JUMP_RADIUS = 0.34;

export interface RouteSegment {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  isHorizontal: boolean;
  netId: string;
}

export interface Crossing {
  x: number;
  y: number;
  hNetId: string;
  vNetId: string;
}

export interface RouteObstacle {
  id: string;
  minX: number;
  minY: number;
  maxX: number;
  maxY: number;
}

interface RouteOptions {
  existingSegments?: RouteSegment[];
  preferredSpacing?: number;
  obstacles?: RouteObstacle[];
  ignoredObstacleIds?: Set<string>;
}

interface RouteQuality {
  overlaps: number;
  crossings: number;
  closeParallel: number;
  score: number;
}

function stubPoint(
  x: number,
  y: number,
  side: string,
  stub = 2.54,
): [number, number, number] {
  const normalized = side === 'left' || side === 'right' || side === 'top' || side === 'bottom'
    ? side
    : 'right';
  switch (normalized) {
    case 'left':
      return [x - stub, y, 0];
    case 'right':
      return [x + stub, y, 0];
    case 'top':
      return [x, y + stub, 0];
    case 'bottom':
      return [x, y - stub, 0];
  }
}

function orthRoute(
  a: [number, number, number],
  b: [number, number, number],
): [number, number, number][] {
  if (Math.abs(a[0] - b[0]) < 1e-6 || Math.abs(a[1] - b[1]) < 1e-6) {
    return [a, b];
  }
  return [a, [b[0], a[1], 0], b];
}

function lineIntersectsObstacle(
  a: [number, number, number],
  b: [number, number, number],
  obs: RouteObstacle,
): boolean {
  const minX = Math.min(a[0], b[0]);
  const maxX = Math.max(a[0], b[0]);
  const minY = Math.min(a[1], b[1]);
  const maxY = Math.max(a[1], b[1]);
  const overlapsX = maxX > obs.minX && minX < obs.maxX;
  const overlapsY = maxY > obs.minY && minY < obs.maxY;
  return overlapsX && overlapsY;
}

function routeIntersectsObstacles(
  route: [number, number, number][],
  obstacles: RouteObstacle[],
  ignored: Set<string>,
): boolean {
  for (let i = 0; i < route.length - 1; i++) {
    const a = route[i];
    const b = route[i + 1];
    for (const obs of obstacles) {
      if (ignored.has(obs.id)) continue;
      if (lineIntersectsObstacle(a, b, obs)) return true;
    }
  }
  return false;
}

function colinearOverlap(a: RouteSegment, b: RouteSegment): boolean {
  if (a.isHorizontal !== b.isHorizontal) return false;
  if (a.isHorizontal) {
    if (Math.abs(a.y1 - b.y1) > 1e-6) return false;
    const aMin = Math.min(a.x1, a.x2);
    const aMax = Math.max(a.x1, a.x2);
    const bMin = Math.min(b.x1, b.x2);
    const bMax = Math.max(b.x1, b.x2);
    return Math.min(aMax, bMax) > Math.max(aMin, bMin);
  }
  if (Math.abs(a.x1 - b.x1) > 1e-6) return false;
  const aMin = Math.min(a.y1, a.y2);
  const aMax = Math.max(a.y1, a.y2);
  const bMin = Math.min(b.y1, b.y2);
  const bMax = Math.max(b.y1, b.y2);
  return Math.min(aMax, bMax) > Math.max(aMin, bMin);
}

type Point3 = [number, number, number];

function enforceOrthogonal(route: Point3[]): Point3[] {
  if (route.length < 2) return route;
  const result: Point3[] = [route[0]];
  for (let i = 1; i < route.length; i++) {
    const prev = result[result.length - 1];
    const curr = route[i];
    if (Math.abs(prev[0] - curr[0]) > 1e-6 && Math.abs(prev[1] - curr[1]) > 1e-6) {
      // Break diagonal into horizontal-then-vertical
      result.push([curr[0], prev[1], 0]);
    }
    result.push(curr);
  }
  return result;
}

function routeQuality(route: [number, number, number][], existing: RouteSegment[]): RouteQuality {
  const ours = segmentsFromRoute(route, '__candidate__');
  let overlaps = 0;
  let crossings = 0;
  let closeParallel = 0;

  for (const s of ours) {
    for (const e of existing) {
      if (colinearOverlap(s, e)) overlaps += 1;
      if (s.isHorizontal !== e.isHorizontal) {
        const h = s.isHorizontal ? s : e;
        const v = s.isHorizontal ? e : s;
        const hx1 = Math.min(h.x1, h.x2);
        const hx2 = Math.max(h.x1, h.x2);
        const vy1 = Math.min(v.y1, v.y2);
        const vy2 = Math.max(v.y1, v.y2);
        if (v.x1 > hx1 && v.x1 < hx2 && h.y1 > vy1 && h.y1 < vy2) crossings += 1;
      } else {
        if (s.isHorizontal && Math.abs(s.y1 - e.y1) <= 2.54 && !colinearOverlap(s, e)) closeParallel += 1;
        if (!s.isHorizontal && Math.abs(s.x1 - e.x1) <= 2.54 && !colinearOverlap(s, e)) closeParallel += 1;
      }
    }
  }

  return {
    overlaps,
    crossings,
    closeParallel,
    score: overlaps * 100 + crossings * 25 + closeParallel * 6 + Math.max(route.length - 4, 0) * 4,
  };
}

export function computeOrthogonalRoute(
  ax: number,
  ay: number,
  aSide: string,
  bx: number,
  by: number,
  bSide: string,
): [number, number, number][] {
  const a: [number, number, number] = [ax, ay, 0];
  const b: [number, number, number] = [bx, by, 0];
  const aStub = stubPoint(ax, ay, aSide);
  const bStub = stubPoint(bx, by, bSide);

  const middle = orthRoute(aStub, bStub);
  return [a, ...middle, b];
}

export function routeOrthogonalWithHeuristics(
  ax: number,
  ay: number,
  aSide: string,
  bx: number,
  by: number,
  bSide: string,
  options: RouteOptions = {},
): { route: [number, number, number][]; quality: RouteQuality } {
  const existing = options.existingSegments ?? [];
  const spacing = options.preferredSpacing ?? 2.54;
  const obstacles = options.obstacles ?? [];
  const ignored = options.ignoredObstacleIds ?? new Set<string>();

  const base = computeOrthogonalRoute(ax, ay, aSide, bx, by, bSide);
  const aStub = base[1];
  const bStub = base[base.length - 2];

  const candidates: [number, number, number][][] = [base];

  for (const delta of [spacing, -spacing, spacing * 2, -spacing * 2]) {
    candidates.push([
      [ax, ay, 0],
      aStub,
      [aStub[0], aStub[1] + delta, 0],
      [bStub[0], bStub[1] + delta, 0],
      bStub,
      [bx, by, 0],
    ]);
    candidates.push([
      [ax, ay, 0],
      aStub,
      [aStub[0] + delta, aStub[1], 0],
      [bStub[0] + delta, bStub[1], 0],
      bStub,
      [bx, by, 0],
    ]);
  }

  let best = enforceOrthogonal(candidates[0]);
  let bestQ = routeQuality(best, existing);
  let bestBlocked = routeIntersectsObstacles(best, obstacles, ignored);

  for (const candidate of candidates.slice(1)) {
    const fixed = enforceOrthogonal(candidate);
    const blocked = routeIntersectsObstacles(fixed, obstacles, ignored);
    const q = routeQuality(fixed, existing);
    const better =
      (bestBlocked && !blocked) ||
      (bestBlocked === blocked && q.score < bestQ.score);

    if (better) {
      best = fixed;
      bestQ = q;
      bestBlocked = blocked;
    }
  }

  return { route: best, quality: bestQ };
}

export function segmentsFromRoute(
  route: [number, number, number][],
  netId: string,
): RouteSegment[] {
  const out: RouteSegment[] = [];
  for (let i = 0; i < route.length - 1; i++) {
    const a = route[i];
    const b = route[i + 1];
    out.push({
      x1: a[0],
      y1: a[1],
      x2: b[0],
      y2: b[1],
      isHorizontal: Math.abs(a[1] - b[1]) < 1e-6,
      netId,
    });
  }
  return out;
}

export function findCrossings(segments: RouteSegment[]): Crossing[] {
  const out: Crossing[] = [];
  for (let i = 0; i < segments.length; i++) {
    for (let j = i + 1; j < segments.length; j++) {
      const a = segments[i];
      const b = segments[j];
      if (a.netId === b.netId) continue;
      if (a.isHorizontal === b.isHorizontal) continue;
      const h = a.isHorizontal ? a : b;
      const v = a.isHorizontal ? b : a;
      const minHX = Math.min(h.x1, h.x2);
      const maxHX = Math.max(h.x1, h.x2);
      const minVY = Math.min(v.y1, v.y2);
      const maxVY = Math.max(v.y1, v.y2);
      const x = v.x1;
      const y = h.y1;
      if (x > minHX && x < maxHX && y > minVY && y < maxVY) {
        out.push({
          x,
          y,
          hNetId: h.netId,
          vNetId: v.netId,
        });
      }
    }
  }
  return out;
}

export interface Junction {
  x: number;
  y: number;
  netId: string;
}

export function findJunctions(segments: RouteSegment[]): Junction[] {
  // Group segments by netId
  const byNet = new Map<string, RouteSegment[]>();
  for (const seg of segments) {
    let arr = byNet.get(seg.netId);
    if (!arr) {
      arr = [];
      byNet.set(seg.netId, arr);
    }
    arr.push(seg);
  }

  const junctions: Junction[] = [];

  for (const [netId, netSegments] of byNet) {
    if (netSegments.length < 2) continue;

    // Count how many segment endpoints share each (x,y) coordinate
    const pointCounts = new Map<string, { x: number; y: number; count: number }>();
    for (const seg of netSegments) {
      const k1 = `${seg.x1.toFixed(4)},${seg.y1.toFixed(4)}`;
      const k2 = `${seg.x2.toFixed(4)},${seg.y2.toFixed(4)}`;
      const e1 = pointCounts.get(k1);
      if (e1) {
        e1.count++;
      } else {
        pointCounts.set(k1, { x: seg.x1, y: seg.y1, count: 1 });
      }
      const e2 = pointCounts.get(k2);
      if (e2) {
        e2.count++;
      } else {
        pointCounts.set(k2, { x: seg.x2, y: seg.y2, count: 1 });
      }
    }

    // A T-junction has 3+ segment endpoints meeting; a 4-way crossing has 4
    for (const [, pt] of pointCounts) {
      if (pt.count >= 3) {
        junctions.push({ x: pt.x, y: pt.y, netId });
      }
    }
  }

  return junctions;
}

export function generateJumpArc(x: number, y: number): [number, number][] {
  const points: [number, number][] = [];
  const steps = 16;
  for (let i = 0; i <= steps; i++) {
    const t = i / steps;
    const px = x - JUMP_RADIUS + t * (2 * JUMP_RADIUS);
    const py = y + Math.sin(t * Math.PI) * JUMP_RADIUS;
    points.push([px, py]);
  }
  return points;
}

export function writeRouteToLine2(lineRef: any, route: [number, number, number][]): void {
  if (!lineRef || !route.length) return;
  if (typeof lineRef.setPoints === 'function') {
    lineRef.setPoints(route);
    return;
  }

  const flat = route.flatMap((p) => [p[0], p[1], p[2] ?? 0]);
  const geometry = lineRef.geometry;
  if (geometry && typeof geometry.setPositions === 'function') {
    geometry.setPositions(flat);
    if (typeof geometry.computeBoundingSphere === 'function') geometry.computeBoundingSphere();
  }
}
