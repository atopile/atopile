/**
 * NetLines — renders all net connections at the current sheet level.
 *
 * Three rendering modes:
 *   1. Bus connections — related signals (I2C, SPI, UART) grouped into a
 *      thick trunk with diagonal fan-out entries (Altium-style, modernized).
 *   2. Orthogonal direct connections — individual 90° routed wires.
 *   3. Net stubs — multi-pin / long-distance nets shown with name labels.
 *
 * Crossing detection produces jump arcs between different nets' routes.
 */

import { useMemo, useRef, memo } from 'react';
import { useFrame } from '@react-three/fiber';
import { Text, Line } from '@react-three/drei';
import * as THREE from 'three';
import type {
  SchematicNet,
  SchematicPort,
  SchematicPowerPort,
  SchematicSheet,
} from '../types/schematic';
import {
  getComponentGridAlignmentOffset,
  getNormalizedComponentPinGeometry,
  getModuleGridAlignmentOffset,
  getPortGridAlignmentOffset,
  getPowerPortGridAlignmentOffset,
  getRootSheet,
  resolveSheet,
  transformPinOffset,
  transformPinSide,
} from '../types/schematic';
import { useCurrentPorts, useCurrentPowerPorts } from '../stores/schematicStore';
import type { ThemeColors } from '../lib/theme';
import { useSchematicStore, liveDrag } from '../stores/schematicStore';
import {
  computeOrthogonalRoute,
  routeOrthogonalWithHeuristics,
  padRoute,
  segmentsFromRoute,
  findCrossings,
  generateJumpArc,
  writeRouteToLine2,
  JUMP_RADIUS,
  type RouteSegment,
  type Crossing,
} from '../lib/orthoRouter';
import {
  detectBuses,
  trunkMidpoint,
  type BusGroup,
  type BusEndpoint,
  type NetForBus,
} from '../lib/busDetector';
import { routeHitsObstacle, type RouteObstacle } from './routeObstacles';

const STUB_LENGTH = 2.54;
const DIRECT_LABEL_DISTANCE = 72;
const ROUTE_SPACING = 2.54;
const COMPLEX_ROUTE_SCORE = 210;
const COMPLEX_ROUTE_CROSSINGS = 2;
const COMPLEX_ROUTE_PARALLEL = 3;
const MAX_MULTI_ROUTE_PINS = 5;
const MULTI_ROUTE_MAX_SPAN = 48;
const NO_RAYCAST = () => {};
const ROUTE_OBSTACLE_CLEARANCE = 0.5;

// ── Helpers ────────────────────────────────────────────────────

function netColor(net: SchematicNet, theme: ThemeColors): string {
  switch (net.type) {
    case 'power':
      return theme.pinPower;
    case 'ground':
      return theme.pinGround;
    case 'electrical':
      return theme.netElectrical;
    case 'bus':
      if (/scl|sda|i2c/i.test(net.name)) return theme.busI2C;
      if (/spi|mosi|miso|sclk|cs/i.test(net.name)) return theme.busSPI;
      if (/uart|tx|rx/i.test(net.name)) return theme.busUART;
      return theme.pinSignal;
    case 'signal':
    default:
      return theme.pinSignal;
  }
}

function oppositeSide(side: string): string {
  switch (side) {
    case 'left':
      return 'right';
    case 'right':
      return 'left';
    case 'top':
      return 'bottom';
    case 'bottom':
      return 'top';
    default:
      return side;
  }
}

// ── Unified pin lookup ─────────────────────────────────────────

interface PinInfo {
  x: number;
  y: number;
  side: string;
}

interface ItemLookup {
  pinMap: Map<string, Map<string, PinInfo>>;
}

function resolvePinFromMap(
  pinMap: Map<string, PinInfo> | undefined,
  pinNumber: string,
): { pin: PinInfo; key: string } | null {
  if (!pinMap) return null;
  const pin = pinMap.get(pinNumber);
  if (!pin) return null;
  return { pin, key: pinNumber };
}

function buildLookup(
  sheet: SchematicSheet,
  ports: SchematicPort[] = [],
  powerPorts: SchematicPowerPort[] = [],
): ItemLookup {
  const pinMap = new Map<string, Map<string, PinInfo>>();

  for (const comp of sheet.components) {
    const pm = new Map<string, PinInfo>();
    const offset = getComponentGridAlignmentOffset(comp);
    for (const pin of comp.pins) {
      const norm = getNormalizedComponentPinGeometry(comp, pin);
      pm.set(pin.number, {
        x: norm.x + offset.x,
        y: norm.y + offset.y,
        side: pin.side,
      });
    }
    pinMap.set(comp.id, pm);
  }
  for (const mod of sheet.modules) {
    const pm = new Map<string, PinInfo>();
    const offset = getModuleGridAlignmentOffset(mod);
    for (const pin of mod.interfacePins) {
      pm.set(pin.id, {
        x: pin.x + offset.x,
        y: pin.y + offset.y,
        side: pin.side,
      });
    }
    pinMap.set(mod.id, pm);
  }
  for (const port of ports) {
    const pm = new Map<string, PinInfo>();
    const offset = getPortGridAlignmentOffset(port);
    if (port.signals && port.signalPins) {
      // Breakout port: register each signal pin.
      for (const sig of port.signals) {
        const sp = port.signalPins[sig];
        if (sp) {
          pm.set(sig, {
            x: sp.x + offset.x,
            y: sp.y + offset.y,
            side: port.pinSide,
          });
        }
      }
      // Line-level pin for nets that target the interface as a whole.
      // For breakout ports this sits on the opposite side from the
      // per-signal pins (explicit bus<->signal translation boundary).
      pm.set('1', {
        x: port.pinX + offset.x,
        y: port.pinY + offset.y,
        side: oppositeSide(port.pinSide),
      });
    } else {
      pm.set('1', {
        x: port.pinX + offset.x,
        y: port.pinY + offset.y,
        side: port.pinSide,
      });
    }
    pinMap.set(port.id, pm);
  }
  // Register power/ground port symbols — each has a single connection pin
  for (const pp of powerPorts) {
    const pm = new Map<string, PinInfo>();
    const offset = getPowerPortGridAlignmentOffset(pp);
    pm.set('1', {
      x: pp.pinX + offset.x,
      y: pp.pinY + offset.y,
      side: pp.pinSide,
    });
    pinMap.set(pp.id, pm);
  }

  return { pinMap };
}

// ── Types ──────────────────────────────────────────────────────

interface WorldPin {
  x: number;
  y: number;
  side: string;
  compId: string;
  pinNumber: string;
}

interface DirectNetData {
  routeId: string;
  net: SchematicNet;
  worldPins: WorldPin[];
  route: [number, number, number][];
  color: string;
}

interface StubNetData {
  net: SchematicNet;
  worldPins: WorldPin[];
  color: string;
}

interface PendingDirectNetData {
  routeId: string;
  net: SchematicNet;
  worldPins: WorldPin[];
  color: string;
  distance: number;
  forceDirect: boolean;
}

interface PendingMultiNetData {
  net: SchematicNet;
  worldPins: WorldPin[];
  edges: Array<{ a: WorldPin; b: WorldPin }>;
  color: string;
  span: number;
}

function manhattanDistance(a: WorldPin, b: WorldPin): number {
  return Math.abs(a.x - b.x) + Math.abs(a.y - b.y);
}

function computePinSpan(worldPins: WorldPin[]): number {
  let minX = Number.POSITIVE_INFINITY;
  let minY = Number.POSITIVE_INFINITY;
  let maxX = Number.NEGATIVE_INFINITY;
  let maxY = Number.NEGATIVE_INFINITY;
  for (const p of worldPins) {
    if (p.x < minX) minX = p.x;
    if (p.y < minY) minY = p.y;
    if (p.x > maxX) maxX = p.x;
    if (p.y > maxY) maxY = p.y;
  }
  if (!Number.isFinite(minX) || !Number.isFinite(minY)) return 0;
  return Math.sqrt((maxX - minX) ** 2 + (maxY - minY) ** 2);
}

function buildMstEdges(
  worldPins: WorldPin[],
): Array<{ a: WorldPin; b: WorldPin }> {
  if (worldPins.length < 2) return [];

  const visited = new Set<number>([0]);
  const edges: Array<{ a: WorldPin; b: WorldPin }> = [];

  while (visited.size < worldPins.length) {
    let bestFrom = -1;
    let bestTo = -1;
    let bestDist = Number.POSITIVE_INFINITY;

    for (const from of visited) {
      for (let to = 0; to < worldPins.length; to++) {
        if (visited.has(to)) continue;
        const d = manhattanDistance(worldPins[from], worldPins[to]);
        if (d < bestDist) {
          bestDist = d;
          bestFrom = from;
          bestTo = to;
        }
      }
    }

    if (bestFrom < 0 || bestTo < 0) break;
    visited.add(bestTo);
    edges.push({ a: worldPins[bestFrom], b: worldPins[bestTo] });
  }

  return edges;
}

function routePriority(net: SchematicNet): number {
  if (net.type === 'power') return 0;
  if (net.type === 'ground') return 1;
  if (net.type === 'bus') return 2;
  if (net.type === 'electrical') return 3;
  return 3;
}

function buildRouteObstacles(
  sheet: SchematicSheet,
  ports: SchematicPort[],
  positions: Record<string, { x: number; y: number; rotation?: number }>,
  pk: string,
): RouteObstacle[] {
  const obstacles: RouteObstacle[] = [];

  const pushItem = (id: string, bodyWidth: number, bodyHeight: number) => {
    const pos = positions[pk + id];
    if (!pos) return;
    const rot = ((pos.rotation ?? 0) % 360 + 360) % 360;
    const rotated = rot === 90 || rot === 270;
    const w = rotated ? bodyHeight : bodyWidth;
    const h = rotated ? bodyWidth : bodyHeight;
    obstacles.push({
      id,
      minX: pos.x - w / 2 - ROUTE_OBSTACLE_CLEARANCE,
      maxX: pos.x + w / 2 + ROUTE_OBSTACLE_CLEARANCE,
      minY: pos.y - h / 2 - ROUTE_OBSTACLE_CLEARANCE,
      maxY: pos.y + h / 2 + ROUTE_OBSTACLE_CLEARANCE,
    });
  };

  for (const comp of sheet.components) {
    pushItem(comp.id, comp.bodyWidth, comp.bodyHeight);
  }
  for (const mod of sheet.modules) {
    pushItem(mod.id, mod.bodyWidth, mod.bodyHeight);
  }
  for (const port of ports) {
    pushItem(port.id, port.bodyWidth, port.bodyHeight);
  }

  return obstacles;
}

// ── Main component ─────────────────────────────────────────────

export const NetLines = memo(function NetLines({
  theme,
}: {
  theme: ThemeColors;
}) {
  const schematic = useSchematicStore((s) => s.schematic);
  const currentPath = useSchematicStore((s) => s.currentPath);
  const positions = useSchematicStore((s) => s.positions);
  const selectedNetId = useSchematicStore((s) => s.selectedNetId);
  const ports = useCurrentPorts();
  const powerPorts = useCurrentPowerPorts();

  const sheet = useMemo(() => {
    if (!schematic) return null;
    return resolveSheet(getRootSheet(schematic), currentPath);
  }, [schematic, currentPath]);

  const lookup = useMemo<ItemLookup | null>(() => {
    if (!sheet) return null;
    return buildLookup(sheet, ports, powerPorts);
  }, [sheet, ports, powerPorts]);

  const pk = useMemo(
    () => (currentPath.length === 0 ? '__root__' : currentPath.join('/')) + ':',
    [currentPath],
  );

  // Net → color map (shared by crossing jumps + bus rendering)
  const netColorMap = useMemo(() => {
    const map = new Map<string, string>();
    if (!sheet) return map;
    for (const net of sheet.nets) map.set(net.id, netColor(net, theme));
    return map;
  }, [sheet, theme]);

  // ── Compute routes, detect buses, find crossings ──────────

  const { directNets, stubNets, busGroups, crossings } = useMemo(() => {
    if (!sheet || !lookup) {
      return {
        directNets: [] as DirectNetData[],
        stubNets: [] as StubNetData[],
        busGroups: [] as BusGroup[],
        crossings: [] as Crossing[],
      };
    }

    const directs: DirectNetData[] = [];
    const stubs: StubNetData[] = [];
    const pendingDirects: PendingDirectNetData[] = [];
    const pendingMultiNets: PendingMultiNetData[] = [];
    const allSegments: RouteSegment[] = [];
    const routeObstacles = buildRouteObstacles(sheet, ports, positions, pk);
    const breakoutPortIds = new Set(
      ports
        .filter((p) => !!p.signals && p.signals.length >= 2)
        .map((p) => p.id),
    );

    // Collect bus candidates alongside direct/stub classification
    const busInputs: NetForBus[] = [];

    for (const net of sheet.nets) {
      const color = netColorMap.get(net.id) || theme.pinSignal;

      // ── Power/ground nets: draw individual wires from each
      //    power port symbol to its connected component pin ──
      if (net.type === 'power' || net.type === 'ground') {
        for (const np of net.pins) {
          const ppId = `__pwr__${net.id}__${np.componentId}__${np.pinNumber}`;
          const ppPinMap = lookup.pinMap.get(ppId);
          const compPinMap = lookup.pinMap.get(np.componentId);
          if (!ppPinMap || !compPinMap) continue;

          const ppResolved = resolvePinFromMap(ppPinMap, '1');
          const compResolved = resolvePinFromMap(compPinMap, np.pinNumber);
          if (!ppResolved || !compResolved) continue;
          const ppPin = ppResolved.pin;
          const compPin = compResolved.pin;

          const ppPos = positions[pk + ppId] || { x: 0, y: 0 };
          const compPos = positions[pk + np.componentId] || { x: 0, y: 0 };

          const ppTp = transformPinOffset(ppPin.x, ppPin.y, ppPos.rotation, ppPos.mirrorX, ppPos.mirrorY);
          const ppTs = transformPinSide(ppPin.side, ppPos.rotation, ppPos.mirrorX, ppPos.mirrorY);
          const compTp = transformPinOffset(compPin.x, compPin.y, compPos.rotation, compPos.mirrorX, compPos.mirrorY);
          const compTs = transformPinSide(compPin.side, compPos.rotation, compPos.mirrorX, compPos.mirrorY);

          const wp0: WorldPin = {
            x: ppPos.x + ppTp.x, y: ppPos.y + ppTp.y,
            side: ppTs, compId: ppId, pinNumber: '1',
          };
          const wp1: WorldPin = {
            x: compPos.x + compTp.x, y: compPos.y + compTp.y,
            side: compTs, compId: np.componentId, pinNumber: np.pinNumber,
          };

          // Skip wire if power port pin is on (or very near) the component pin
          const dx = wp0.x - wp1.x;
          const dy = wp0.y - wp1.y;
          if (dx * dx + dy * dy < 0.5) continue;

          pendingDirects.push({
            routeId: ppId,
            net,
            worldPins: [wp0, wp1],
            color,
            distance: Math.sqrt(dx * dx + dy * dy),
            forceDirect: true,
          });
        }
        continue; // power/ground nets fully handled above
      }

      // ── Normal nets (signal / bus) ──
      const worldPins: WorldPin[] = [];
      const uniqueItems = new Set<string>();
      let hasBreakoutSignalEndpoint = false;

      for (const np of net.pins) {
        const pm = lookup.pinMap.get(np.componentId);
        const resolved = resolvePinFromMap(pm, np.pinNumber);
        if (!resolved) continue;
        const pin = resolved.pin;
        const pos = positions[pk + np.componentId] || { x: 0, y: 0 };
        const tp = transformPinOffset(pin.x, pin.y, pos.rotation, pos.mirrorX, pos.mirrorY);
        const ts = transformPinSide(pin.side, pos.rotation, pos.mirrorX, pos.mirrorY);
        worldPins.push({
          x: pos.x + tp.x,
          y: pos.y + tp.y,
          side: ts,
          compId: np.componentId,
          pinNumber: resolved.key,
        });
        if (breakoutPortIds.has(np.componentId) && resolved.key !== '1') {
          hasBreakoutSignalEndpoint = true;
        }
        uniqueItems.add(np.componentId);
      }

      if (worldPins.length < 2) continue;

      // 2-pin nets between exactly 2 items can be direct wires.
      const isTwoPinDirect = uniqueItems.size === 2 && worldPins.length === 2;

      if (isTwoPinDirect) {
        const dx = worldPins[0].x - worldPins[1].x;
        const dy = worldPins[0].y - worldPins[1].y;
        const dist = Math.sqrt(dx * dx + dy * dy);

        if (net.type === 'signal' && dist > DIRECT_LABEL_DISTANCE) {
          stubs.push({ net, worldPins, color });
          continue;
        }

        pendingDirects.push({
          routeId: net.id,
          net,
          worldPins,
          color,
          distance: dist,
          forceDirect: net.type !== 'signal',
        });

        // Also register as bus candidate
        busInputs.push({
          netId: net.id,
          netName: net.name,
          netType: net.type,
          allowBundle: !hasBreakoutSignalEndpoint,
          worldPins: worldPins.map((wp) => ({
            x: wp.x,
            y: wp.y,
            side: wp.side,
            compId: wp.compId,
          })),
        });
      } else if (
        net.type !== 'bus' &&
        worldPins.length >= 3 &&
        worldPins.length <= MAX_MULTI_ROUTE_PINS
      ) {
        const span = computePinSpan(worldPins);
        const edges = buildMstEdges(worldPins);
        if (edges.length > 0 && span <= MULTI_ROUTE_MAX_SPAN) {
          pendingMultiNets.push({
            net,
            worldPins,
            edges,
            color,
            span,
          });
        } else {
          stubs.push({ net, worldPins, color });
        }
      } else {
        stubs.push({ net, worldPins, color });
      }
    }

    // ── Bus detection ───────────────────────────────────────
    const buses = detectBuses(busInputs, theme);

    // Nets consumed by buses → suppress individual routes and add bus trunk.
    const busNetIds = new Set<string>();
    for (const bg of buses) {
      for (const nid of bg.memberNetIds) {
        busNetIds.add(nid);
      }
      allSegments.push(...segmentsFromRoute(bg.trunkRoute, bg.id));
    }

    const existingSegments: RouteSegment[] = [];
    for (const bg of buses) {
      existingSegments.push(...segmentsFromRoute(bg.trunkRoute, bg.id));
    }

    const routed = [...pendingDirects].sort((a, b) => {
      if (a.forceDirect !== b.forceDirect) return a.forceDirect ? -1 : 1;
      const pr = routePriority(a.net) - routePriority(b.net);
      if (pr !== 0) return pr;
      if (Math.abs(a.distance - b.distance) > 0.01) return a.distance - b.distance;
      return a.routeId.localeCompare(b.routeId);
    });

    for (const pd of routed) {
      if (busNetIds.has(pd.net.id)) continue;
      const a = pd.worldPins[0];
      const b = pd.worldPins[1];
      const routedResult = routeOrthogonalWithHeuristics(
        a.x, a.y, a.side,
        b.x, b.y, b.side,
        {
          existingSegments,
          preferredSpacing: ROUTE_SPACING,
          obstacles: routeObstacles,
          ignoredObstacleIds: new Set([a.compId, b.compId]),
        },
      );

      const q = routedResult.quality;
      const shortSignalForcesDirect = pd.net.type === 'signal' && pd.distance <= 24;
      const shouldFallbackToLabels = !pd.forceDirect &&
        !shortSignalForcesDirect &&
        pd.net.type === 'signal' &&
        (
          pd.distance > DIRECT_LABEL_DISTANCE ||
          q.overlaps > 0 ||
          q.crossings >= COMPLEX_ROUTE_CROSSINGS ||
          q.closeParallel > COMPLEX_ROUTE_PARALLEL ||
          q.score > COMPLEX_ROUTE_SCORE
        );

      if (shouldFallbackToLabels) {
        stubs.push({ net: pd.net, worldPins: pd.worldPins, color: pd.color });
        continue;
      }

      const route = padRoute(routedResult.route);
      if (
        routeHitsObstacle(
          route,
          routeObstacles,
          new Set([a.compId, b.compId]),
        )
      ) {
        stubs.push({ net: pd.net, worldPins: pd.worldPins, color: pd.color });
        continue;
      }
      directs.push({
        routeId: pd.routeId,
        net: pd.net,
        worldPins: pd.worldPins,
        route,
        color: pd.color,
      });
      allSegments.push(...segmentsFromRoute(route, pd.net.id));
      existingSegments.push(...segmentsFromRoute(route, pd.routeId));
    }

    const routedMulti = [...pendingMultiNets].sort((a, b) => {
      const pr = routePriority(a.net) - routePriority(b.net);
      if (pr !== 0) return pr;
      if (Math.abs(a.span - b.span) > 0.01) return a.span - b.span;
      return a.net.id.localeCompare(b.net.id);
    });

    for (const pm of routedMulti) {
      if (busNetIds.has(pm.net.id)) continue;

      const edgeRoutes: Array<{
        routeId: string;
        worldPins: [WorldPin, WorldPin];
        route: [number, number, number][];
      }> = [];
      const stagedSegments: RouteSegment[] = [];
      let failed = false;

      for (let i = 0; i < pm.edges.length; i++) {
        const edge = pm.edges[i];
        const routedResult = routeOrthogonalWithHeuristics(
          edge.a.x, edge.a.y, edge.a.side,
          edge.b.x, edge.b.y, edge.b.side,
          {
            existingSegments: existingSegments.concat(stagedSegments),
            preferredSpacing: ROUTE_SPACING,
            obstacles: routeObstacles,
            ignoredObstacleIds: new Set([edge.a.compId, edge.b.compId]),
          },
        );

        const q = routedResult.quality;
        const edgeDist = manhattanDistance(edge.a, edge.b);
        const shortSignalForcesDirect = pm.net.type === 'signal' && edgeDist <= 24;
        const shouldFallbackToLabels =
          pm.net.type === 'signal' &&
          !shortSignalForcesDirect &&
          (
            q.overlaps > 0 ||
            q.crossings >= COMPLEX_ROUTE_CROSSINGS ||
            q.closeParallel > COMPLEX_ROUTE_PARALLEL ||
            q.score > COMPLEX_ROUTE_SCORE
          );

        if (shouldFallbackToLabels) {
          failed = true;
          break;
        }

        const route = padRoute(routedResult.route);
        if (
          routeHitsObstacle(
            route,
            routeObstacles,
            new Set([edge.a.compId, edge.b.compId]),
          )
        ) {
          failed = true;
          break;
        }
        const routeId = `${pm.net.id}::${i}`;
        edgeRoutes.push({
          routeId,
          worldPins: [edge.a, edge.b],
          route,
        });
        stagedSegments.push(...segmentsFromRoute(route, routeId));
      }

      if (failed || edgeRoutes.length === 0) {
        stubs.push({ net: pm.net, worldPins: pm.worldPins, color: pm.color });
        continue;
      }

      for (const er of edgeRoutes) {
        directs.push({
          routeId: er.routeId,
          net: pm.net,
          worldPins: er.worldPins,
          route: er.route,
          color: pm.color,
        });
        allSegments.push(...segmentsFromRoute(er.route, pm.net.id));
      }
      existingSegments.push(...stagedSegments);
    }

    // ── Crossing detection ──────────────────────────────────
    const cx = findCrossings(allSegments);

    return {
      directNets: directs,
      stubNets: stubs,
      busGroups: buses,
      crossings: cx,
    };
  }, [sheet, lookup, positions, pk, netColorMap, theme, ports]);

  if (!sheet || !lookup) return null;

  return (
    <group raycast={NO_RAYCAST}>
      {/* Bus connections (thick trunk + fan entries) */}
      {busGroups.map((group) => (
        <BusConnection
          key={group.id}
          group={group}
          theme={theme}
          selectedNetId={selectedNetId}
        />
      ))}

      {/* Individual orthogonal connections */}
      {directNets.map(({ routeId, net, worldPins, route, color }) => {
        const isSelected = selectedNetId === net.id;
        const opacity = isSelected ? 1 : selectedNetId ? 0.25 : 0.8;
        return (
          <OrthogonalConnection
            key={routeId}
            net={net}
            worldPins={worldPins}
            initialRoute={route}
            lookup={lookup}
            pk={pk}
            color={color}
            opacity={opacity}
            isActive={isSelected}
          />
        );
      })}

      {/* Stub connections */}
      {stubNets.map(({ net, worldPins, color }) => {
        const isSelected = selectedNetId === net.id;
        const opacity = isSelected ? 1 : selectedNetId ? 0.25 : 0.8;
        return (
          <NetStubs
            key={net.id}
            net={net}
            worldPins={worldPins}
            lookup={lookup}
            pk={pk}
            color={color}
            opacity={opacity}
            isActive={isSelected}
          />
        );
      })}

      {/* Crossing jump arcs */}
      <CrossingJumps
        crossings={crossings}
        netColorMap={netColorMap}
        theme={theme}
        selectedNetId={selectedNetId}
      />
    </group>
  );
});

// ════════════════════════════════════════════════════════════════
// ── Bus connection (trunk + entries + badge)
// ════════════════════════════════════════════════════════════════

const BusConnection = memo(function BusConnection({
  group,
  theme,
  selectedNetId,
}: {
  group: BusGroup;
  theme: ThemeColors;
  selectedNetId: string | null;
}) {
  const selectNet = useSchematicStore((s) => s.selectNet);
  const hoverNet = useSchematicStore((s) => s.hoverNet);

  const isActive = selectedNetId != null && group.memberNetIds.has(selectedNetId);
  const opacity = isActive ? 1 : selectedNetId ? 0.25 : 0.85;
  const firstNetId = [...group.memberNetIds][0];

  const { trunkRoute, endpointA, endpointB, color, name } = group;
  const signalCount = group.memberNetIds.size;

  const badge = useMemo(() => trunkMidpoint(trunkRoute), [trunkRoute]);

  return (
    <group
      onClick={(e) => {
        e.stopPropagation();
        selectNet(firstNetId);
      }}
      onPointerEnter={() => hoverNet(firstNetId)}
      onPointerLeave={() => hoverNet(null)}
    >
      {/* Thick bus trunk */}
      <Line
        points={trunkRoute}
        lineWidth={isActive ? 4.5 : 3.5}
        color={color}
        transparent
        opacity={opacity}
      />

      {/* Fan-out entries at each endpoint */}
      <BusEntries
        endpoint={endpointA}
        color={color}
        opacity={opacity}
        lineWidth={isActive ? 2.2 : 1.5}
      />
      <BusEntries
        endpoint={endpointB}
        color={color}
        opacity={opacity}
        lineWidth={isActive ? 2.2 : 1.5}
      />

      {/* Bus name badge on the trunk */}
      <BusBadge
        x={badge.x}
        y={badge.y}
        name={name}
        count={signalCount}
        color={color}
        bgColor={theme.bgPrimary}
        opacity={opacity}
      />

      {/* Animated flow dot when selected */}
      {isActive && <FlowDot points={trunkRoute} color={color} />}
    </group>
  );
});

// ── Bus entry fan-out at one endpoint ──────────────────────────

function BusEntries({
  endpoint,
  color,
  opacity,
  lineWidth,
}: {
  endpoint: BusEndpoint;
  color: string;
  opacity: number;
  lineWidth: number;
}) {
  return (
    <group raycast={NO_RAYCAST}>
      {endpoint.pins.map((pin, i) => {
        // Label positioning
        let labelX = pin.stubX;
        let labelY = pin.stubY;
        let anchor: 'left' | 'right' | 'center' = 'center';

        if (pin.side === 'right') {
          labelX = pin.x - 0.5;
          anchor = 'right';
        } else if (pin.side === 'left') {
          labelX = pin.x + 0.5;
          anchor = 'left';
        } else if (pin.side === 'top') {
          labelY = pin.y - 0.5;
        } else {
          labelY = pin.y + 0.5;
        }

        return (
          <group key={i}>
            {/* Horizontal stub from pin */}
            <Line
              points={[
                [pin.x, pin.y, 0],
                [pin.stubX, pin.stubY, 0],
              ]}
              lineWidth={lineWidth}
              color={color}
              transparent
              opacity={opacity}
              raycast={NO_RAYCAST}
            />

            {/* Diagonal entry to merge point */}
            <Line
              points={[
                [pin.stubX, pin.stubY, 0],
                [endpoint.mergeX, endpoint.mergeY, 0],
              ]}
              lineWidth={lineWidth}
              color={color}
              transparent
              opacity={opacity}
              raycast={NO_RAYCAST}
            />

            {/* Signal name near pin */}
            <Text
              position={[labelX, labelY, 0.03]}
              fontSize={0.55}
              color={color}
              anchorX={anchor}
              anchorY="middle"
              fillOpacity={opacity * 0.8}
              font={undefined}
              raycast={NO_RAYCAST}
            >
              {pin.netName}
            </Text>
          </group>
        );
      })}
    </group>
  );
}

// ── Bus name badge ─────────────────────────────────────────────

function BusBadge({
  x,
  y,
  name,
  count,
  color,
  bgColor,
  opacity,
}: {
  x: number;
  y: number;
  name: string;
  count: number;
  color: string;
  bgColor: string;
  opacity: number;
}) {
  const label = `${name}`;
  const badgeW = Math.max(name.length * 0.65 + 2, 4.5);
  const badgeH = 2.2;

  return (
    <group position={[x, y, 0.04]}>
      {/* Background mask — hides trunk line behind badge */}
      <mesh raycast={NO_RAYCAST}>
        <planeGeometry args={[badgeW + 0.6, badgeH + 0.4]} />
        <meshBasicMaterial color={bgColor} />
      </mesh>

      {/* Colored fill (subtle tint) */}
      <mesh position={[0, 0, 0.001]} raycast={NO_RAYCAST}>
        <planeGeometry args={[badgeW, badgeH]} />
        <meshBasicMaterial color={color} transparent opacity={0.12 * (opacity / 0.85)} />
      </mesh>

      {/* Thin colored border effect */}
      <mesh position={[0, 0, 0.0005]} raycast={NO_RAYCAST}>
        <planeGeometry args={[badgeW + 0.25, badgeH + 0.25]} />
        <meshBasicMaterial color={color} transparent opacity={0.3 * (opacity / 0.85)} />
      </mesh>

      {/* Bus protocol name */}
      <Text
        position={[0, 0.25, 0.002]}
        fontSize={0.85}
        color={color}
        anchorX="center"
        anchorY="middle"
        fillOpacity={opacity}
        font={undefined}
        raycast={NO_RAYCAST}
      >
        {label}
      </Text>

      {/* Signal count */}
      <Text
        position={[0, -0.55, 0.002]}
        fontSize={0.5}
        color={color}
        anchorX="center"
        anchorY="middle"
        fillOpacity={opacity * 0.6}
        font={undefined}
        raycast={NO_RAYCAST}
      >
        {count} signals
      </Text>
    </group>
  );
}

// ════════════════════════════════════════════════════════════════
// ── Orthogonal direct connection
// ════════════════════════════════════════════════════════════════

const OrthogonalConnection = memo(function OrthogonalConnection({
  net,
  worldPins,
  initialRoute,
  lookup,
  pk,
  color,
  opacity,
  isActive,
}: {
  net: SchematicNet;
  worldPins: WorldPin[];
  initialRoute: [number, number, number][];
  lookup: ItemLookup;
  pk: string;
  color: string;
  opacity: number;
  isActive: boolean;
}) {
  const selectNet = useSchematicStore((s) => s.selectNet);
  const hoverNet = useSchematicStore((s) => s.hoverNet);
  const lineRef = useRef<any>(null);
  const wasModified = useRef(false);
  const lastVersion = useRef(-1);

  useFrame(() => {
    if (!lineRef.current) return;
    const dragging = liveDrag.componentId;

    if (!dragging) {
      if (wasModified.current) {
        wasModified.current = false;
        writeRouteToLine2(lineRef.current, initialRoute);
      }
      return;
    }

    if (liveDrag.version === lastVersion.current) return;
    lastVersion.current = liveDrag.version;

    // Check if any endpoint is being dragged (primary or group member)
    const isAffected = worldPins.some(
      (wp) => wp.compId === dragging || liveDrag.groupOffsets[wp.compId] !== undefined,
    );
    if (!isAffected) return;

    wasModified.current = true;
    const storePositions = useSchematicStore.getState().positions;
    const liveWP = worldPins.map((wp) => {
      const pin = lookup.pinMap.get(wp.compId)?.get(wp.pinNumber);
      if (!pin) return wp;
      const pos = storePositions[pk + wp.compId] || { x: 0, y: 0 };
      const tp = transformPinOffset(pin.x, pin.y, pos.rotation, pos.mirrorX, pos.mirrorY);
      const ts = transformPinSide(pin.side, pos.rotation, pos.mirrorX, pos.mirrorY);
      if (wp.compId === dragging) {
        return { ...wp, x: liveDrag.x + tp.x, y: liveDrag.y + tp.y, side: ts };
      }
      const groupOff = liveDrag.groupOffsets[wp.compId];
      if (groupOff) {
        return { ...wp, x: liveDrag.x + groupOff.x + tp.x, y: liveDrag.y + groupOff.y + tp.y, side: ts };
      }
      return { ...wp, x: pos.x + tp.x, y: pos.y + tp.y, side: ts };
    });

    const liveRoute = padRoute(
      computeOrthogonalRoute(
        liveWP[0].x, liveWP[0].y, liveWP[0].side,
        liveWP[1].x, liveWP[1].y, liveWP[1].side,
      ),
    );
    writeRouteToLine2(lineRef.current, liveRoute);
  });

  return (
    <group
      onClick={(e) => { e.stopPropagation(); selectNet(net.id); }}
      onPointerEnter={() => hoverNet(net.id)}
      onPointerLeave={() => hoverNet(null)}
    >
      <Line
        ref={lineRef}
        points={initialRoute}
        color={color}
        lineWidth={isActive ? 2.8 : net.type === 'bus' ? 2.2 : 1.5}
        transparent
        opacity={opacity}
      />
      {isActive && <FlowDot points={initialRoute} color={color} />}
    </group>
  );
});

// ════════════════════════════════════════════════════════════════
// ── Flow dot (animated indicator on selected net)
// ════════════════════════════════════════════════════════════════

function FlowDot({
  points,
  color,
}: {
  points: [number, number, number][];
  color: string;
}) {
  const ref = useRef<THREE.Mesh>(null);

  const lengths = useMemo(() => {
    const acc: number[] = [0];
    for (let i = 1; i < points.length; i++) {
      const dx = points[i][0] - points[i - 1][0];
      const dy = points[i][1] - points[i - 1][1];
      acc.push(acc[i - 1] + Math.sqrt(dx * dx + dy * dy));
    }
    return acc;
  }, [points]);

  useFrame(({ clock }) => {
    if (!ref.current || lengths.length < 2) return;
    const total = lengths[lengths.length - 1];
    if (total < 0.01) return;

    const t = (clock.getElapsedTime() * 6) % total;
    let seg = 0;
    for (let i = 1; i < lengths.length; i++) {
      if (lengths[i] >= t) { seg = i - 1; break; }
    }
    const segLen = lengths[seg + 1] - lengths[seg];
    const frac = segLen > 0.001 ? (t - lengths[seg]) / segLen : 0;
    const a = points[seg];
    const b = points[Math.min(seg + 1, points.length - 1)];
    ref.current.position.set(
      a[0] + (b[0] - a[0]) * frac,
      a[1] + (b[1] - a[1]) * frac,
      0.04,
    );
  });

  return (
    <mesh ref={ref} raycast={NO_RAYCAST}>
      <circleGeometry args={[0.45, 12]} />
      <meshBasicMaterial color={color} transparent opacity={0.9} />
    </mesh>
  );
}

// ════════════════════════════════════════════════════════════════
// ── Net stubs (multi-pin / long-distance)
// ════════════════════════════════════════════════════════════════

function NetStubs({
  net,
  worldPins,
  lookup,
  pk,
  color,
  opacity,
  isActive,
}: {
  net: SchematicNet;
  worldPins: WorldPin[];
  lookup: ItemLookup;
  pk: string;
  color: string;
  opacity: number;
  isActive: boolean;
}) {
  const selectNet = useSchematicStore((s) => s.selectNet);
  const hoverNet = useSchematicStore((s) => s.hoverNet);
  const groupRefs = useRef<(THREE.Group | null)[]>([]);
  const lastVersion = useRef(-1);

  if (groupRefs.current.length !== worldPins.length) {
    groupRefs.current = new Array(worldPins.length).fill(null);
  }

  useFrame(() => {
    const dragging = liveDrag.componentId;
    const versionChanged = liveDrag.version !== lastVersion.current;
    if (dragging && versionChanged) lastVersion.current = liveDrag.version;

    for (let i = 0; i < worldPins.length; i++) {
      const grp = groupRefs.current[i];
      if (!grp) continue;
      const wp = worldPins[i];

      if (dragging && wp.compId === dragging) {
        const pin = lookup.pinMap.get(wp.compId)?.get(wp.pinNumber);
        if (!pin) continue;
        const pos = useSchematicStore.getState().positions[pk + wp.compId] || { x: 0, y: 0 };
        const tp = transformPinOffset(pin.x, pin.y, pos.rotation, pos.mirrorX, pos.mirrorY);
        grp.position.x = liveDrag.x + tp.x - wp.x;
        grp.position.y = liveDrag.y + tp.y - wp.y;
      } else if (grp.position.x !== 0 || grp.position.y !== 0) {
        grp.position.x = 0;
        grp.position.y = 0;
      }
    }
  });

  return (
    <group
      onClick={(e) => { e.stopPropagation(); selectNet(net.id); }}
      onPointerEnter={() => hoverNet(net.id)}
      onPointerLeave={() => hoverNet(null)}
    >
      {worldPins.map((pin, i) => {
        let endX = pin.x, endY = pin.y;
        let labelX = pin.x, labelY = pin.y;
        let anchor: 'left' | 'right' | 'center' = 'center';

        if (pin.side === 'right') {
          endX += STUB_LENGTH; labelX = endX + 0.5; anchor = 'left';
        } else if (pin.side === 'left') {
          endX -= STUB_LENGTH; labelX = endX - 0.5; anchor = 'right';
        } else if (pin.side === 'top') {
          endY += STUB_LENGTH; labelY = endY + 0.8;
        } else {
          endY -= STUB_LENGTH; labelY = endY - 0.8;
        }

        return (
          <group key={`${net.id}-${i}`} ref={(el) => { groupRefs.current[i] = el; }}>
            <Line
              points={[[pin.x, pin.y, 0], [endX, endY, 0]]}
              color={color}
              lineWidth={isActive ? 2.8 : 1.5}
              transparent
              opacity={opacity}
              raycast={NO_RAYCAST}
            />
            <Text
              position={[labelX, labelY, 0.03]}
              fontSize={0.75}
              color={color}
              anchorX={anchor}
              anchorY="middle"
              fillOpacity={opacity}
              font={undefined}
              raycast={NO_RAYCAST}
            >
              {net.name}
            </Text>
            <mesh position={[endX, endY, 0.02]} raycast={NO_RAYCAST}>
              <circleGeometry args={[0.2, 8]} />
              <meshBasicMaterial color={color} transparent opacity={opacity} />
            </mesh>
          </group>
        );
      })}
    </group>
  );
}

// ════════════════════════════════════════════════════════════════
// ── Crossing jumps
// ════════════════════════════════════════════════════════════════

const CrossingJumps = memo(function CrossingJumps({
  crossings,
  netColorMap,
  theme,
  selectedNetId,
}: {
  crossings: Crossing[];
  netColorMap: Map<string, string>;
  theme: ThemeColors;
  selectedNetId: string | null;
}) {
  if (crossings.length === 0) return null;

  return (
    <group raycast={NO_RAYCAST}>
      {crossings.map((c, i) => (
        <CrossingJump
          key={i}
          crossing={c}
          netColorMap={netColorMap}
          theme={theme}
          selectedNetId={selectedNetId}
        />
      ))}
    </group>
  );
});

const CrossingJump = memo(function CrossingJump({
  crossing,
  netColorMap,
  theme,
  selectedNetId,
}: {
  crossing: Crossing;
  netColorMap: Map<string, string>;
  theme: ThemeColors;
  selectedNetId: string | null;
}) {
  const { x, y, hNetId, vNetId } = crossing;
  const hColor = netColorMap.get(hNetId) || theme.pinSignal;
  const vColor = netColorMap.get(vNetId) || theme.pinSignal;

  const hActive = selectedNetId === hNetId;
  const vActive = selectedNetId === vNetId;
  const hOpacity = hActive ? 1 : selectedNetId ? 0.25 : 0.8;
  const vOpacity = vActive ? 1 : selectedNetId ? 0.25 : 0.8;

  const arcPts = useMemo(
    (): [number, number, number][] =>
      generateJumpArc(x, y).map((p) => [p[0], p[1], 0.003]),
    [x, y],
  );

  const r = JUMP_RADIUS;

  return (
    <group>
      <mesh position={[x, y, 0.001]} raycast={NO_RAYCAST}>
        <circleGeometry args={[r + 0.2, 16]} />
        <meshBasicMaterial color={theme.bgPrimary} />
      </mesh>
      <Line
        points={[[x, y - r - 0.3, 0.002], [x, y + r + 0.3, 0.002]]}
        color={vColor}
        lineWidth={1.5}
        transparent
        opacity={vOpacity}
        raycast={NO_RAYCAST}
      />
      <Line
        points={arcPts}
        color={hColor}
        lineWidth={1.5}
        transparent
        opacity={hOpacity}
        raycast={NO_RAYCAST}
      />
    </group>
  );
});
