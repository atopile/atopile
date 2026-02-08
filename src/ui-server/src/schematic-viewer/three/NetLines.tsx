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
  SchematicSheet,
} from '../types/schematic';
import {
  getRootSheet,
  resolveSheet,
  transformPinOffset,
  transformPinSide,
} from '../types/schematic';
import { useCurrentPorts } from '../stores/schematicStore';
import type { ThemeColors } from '../lib/theme';
import { useSchematicStore, liveDrag } from '../stores/schematicStore';
import {
  computeOrthogonalRoute,
  padRoute,
  extractSegments,
  findCrossings,
  generateJumpArc,
  writeRouteToLine2,
  JUMP_RADIUS,
  type Crossing,
} from '../lib/orthoRouter';
import {
  detectBuses,
  trunkMidpoint,
  type BusGroup,
  type BusEndpoint,
  type NetForBus,
} from '../lib/busDetector';

const STUB_LENGTH = 4;
const CLOSE_DISTANCE = 80;
const NO_RAYCAST = () => {};

// ── Helpers ────────────────────────────────────────────────────

function netColor(net: SchematicNet, theme: ThemeColors): string {
  switch (net.type) {
    case 'power':
      return theme.pinPower;
    case 'ground':
      return theme.pinGround;
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

function dist2d(ax: number, ay: number, bx: number, by: number): number {
  return Math.sqrt((ax - bx) ** 2 + (ay - by) ** 2);
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

function buildLookup(sheet: SchematicSheet, ports: SchematicPort[] = []): ItemLookup {
  const pinMap = new Map<string, Map<string, PinInfo>>();

  for (const comp of sheet.components) {
    const pm = new Map<string, PinInfo>();
    for (const pin of comp.pins) pm.set(pin.number, { x: pin.x, y: pin.y, side: pin.side });
    pinMap.set(comp.id, pm);
  }
  for (const mod of sheet.modules) {
    const pm = new Map<string, PinInfo>();
    for (const pin of mod.interfacePins) pm.set(pin.id, { x: pin.x, y: pin.y, side: pin.side });
    pinMap.set(mod.id, pm);
  }
  for (const port of ports) {
    const pm = new Map<string, PinInfo>();
    pm.set('1', { x: port.pinX, y: port.pinY, side: port.pinSide });
    pinMap.set(port.id, pm);
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

  const sheet = useMemo(() => {
    if (!schematic) return null;
    return resolveSheet(getRootSheet(schematic), currentPath);
  }, [schematic, currentPath]);

  const lookup = useMemo<ItemLookup | null>(() => {
    if (!sheet) return null;
    return buildLookup(sheet, ports);
  }, [sheet, ports]);

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
    const allRoutes = new Map<string, [number, number, number][]>();

    // Collect bus candidates alongside direct/stub classification
    const busInputs: NetForBus[] = [];

    for (const net of sheet.nets) {
      const color = netColorMap.get(net.id) || theme.pinSignal;

      const worldPins: WorldPin[] = [];
      const uniqueItems = new Set<string>();

      for (const np of net.pins) {
        const pm = lookup.pinMap.get(np.componentId);
        const pin = pm?.get(np.pinNumber);
        if (!pin) continue;
        const pos = positions[pk + np.componentId] || { x: 0, y: 0 };
        const tp = transformPinOffset(pin.x, pin.y, pos.rotation, pos.mirrorX, pos.mirrorY);
        const ts = transformPinSide(pin.side, pos.rotation, pos.mirrorX, pos.mirrorY);
        worldPins.push({
          x: pos.x + tp.x,
          y: pos.y + tp.y,
          side: ts,
          compId: np.componentId,
          pinNumber: np.pinNumber,
        });
        uniqueItems.add(np.componentId);
      }

      if (worldPins.length < 2) continue;

      const isDirect =
        uniqueItems.size === 2 &&
        worldPins.length === 2 &&
        dist2d(worldPins[0].x, worldPins[0].y, worldPins[1].x, worldPins[1].y) <
          CLOSE_DISTANCE;

      if (isDirect) {
        const rawRoute = computeOrthogonalRoute(
          worldPins[0].x, worldPins[0].y, worldPins[0].side,
          worldPins[1].x, worldPins[1].y, worldPins[1].side,
        );
        const route = padRoute(rawRoute);
        directs.push({ net, worldPins, route, color });
        allRoutes.set(net.id, route);

        // Also register as bus candidate
        busInputs.push({
          netId: net.id,
          netName: net.name,
          netType: net.type,
          worldPins: worldPins.map((wp) => ({
            x: wp.x,
            y: wp.y,
            side: wp.side,
            compId: wp.compId,
          })),
        });
      } else {
        stubs.push({ net, worldPins, color });
      }
    }

    // ── Bus detection ───────────────────────────────────────
    const buses = detectBuses(busInputs, theme);

    // Nets consumed by buses → remove from directs, add trunk to routes
    const busNetIds = new Set<string>();
    for (const bg of buses) {
      for (const nid of bg.memberNetIds) {
        busNetIds.add(nid);
        allRoutes.delete(nid); // remove individual routes
      }
      allRoutes.set(bg.id, bg.trunkRoute); // add trunk for crossing detection
    }

    const filteredDirects = directs.filter((d) => !busNetIds.has(d.net.id));

    // ── Crossing detection ──────────────────────────────────
    const segments = extractSegments(allRoutes);
    const cx = findCrossings(segments);

    return {
      directNets: filteredDirects,
      stubNets: stubs,
      busGroups: buses,
      crossings: cx,
    };
  }, [sheet, lookup, positions, pk, netColorMap, theme]);

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
      {directNets.map(({ net, worldPins, route, color }) => {
        const isSelected = selectedNetId === net.id;
        const opacity = isSelected ? 1 : selectedNetId ? 0.25 : 0.8;
        return (
          <OrthogonalConnection
            key={net.id}
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

    if (!worldPins.some((wp) => wp.compId === dragging)) return;

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
