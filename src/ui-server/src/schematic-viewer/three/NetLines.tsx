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

import { useMemo, useRef, memo, useEffect, useCallback } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
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
  getGridAlignmentOffset,
  getNormalizedComponentPinGeometry,
  getPortGridAlignmentOffset,
  getPowerPortGridAlignmentOffset,
  getRootSheet,
  resolveSheet,
  transformPinOffset,
  transformPinSide,
} from '../types/schematic';
import { useCurrentPorts, useCurrentPowerPorts } from '../stores/schematicStore';
import { type ThemeColors } from '../utils/theme';
import { useSchematicStore, liveDrag } from '../stores/schematicStore';
import {
  computeOrthogonalRoute,
  routeOrthogonalWithHeuristics,
  segmentsFromRoute,
  findCrossings,
  generateJumpArc,
  writeRouteToLine2,
  JUMP_RADIUS,
  type RouteSegment,
  type Crossing,
} from '../utils/orthoRouter';
import {
  detectBuses,
  type BusGroup,
  type BusEndpoint,
  type NetForBus,
} from '../utils/busDetector';
import { routeHitsObstacle, type RouteObstacle } from './routeObstacles';
import {
  getModulePinOrderForPath,
  getModuleRenderSize,
  getOrderedModuleInterfacePins,
} from '../utils/moduleInterfaces';
import {
  getSemanticConnectionColor,
  neutralConnectionColor,
} from './connectionColor';
import {
  getStandardInterfaceColor,
  resolveStandardInterfaceId,
} from '../../interfaceColors';

const STUB_LENGTH = 2.54;
const ROUTE_SPACING = 2.54;
const ROUTE_DRAG_HIT_THICKNESS = 2.2;
const ROUTE_PICK_HIT_THICKNESS = ROUTE_SPACING * 0.5;
const BUS_ROUTE_DRAG_HIT_THICKNESS = 3.0;
const BUS_ROUTE_PICK_HIT_THICKNESS = 2.1;
const JUMP_MASK_OVERDRAW = 0.06;
const JUMP_MASK_SEGMENTS = 32;
const JUMP_VERTICAL_REPAINT_MARGIN = 0.12;
const COMPLEX_ROUTE_SCORE = 210;
const COMPLEX_ROUTE_CROSSINGS = 2;
const COMPLEX_ROUTE_PARALLEL = 3;
const MAX_MULTI_ROUTE_PINS = 5;
const MULTI_ROUTE_MAX_SPAN = 48;
const POWER_PORT_DIRECT_MAX_DISTANCE = 30;
const BUS_LABEL_FONT_SIZE = 0.72;
const BUS_LABEL_LETTER_SPACING = 0.06;
const BUS_LABEL_SIDE_PADDING = 0.5;
const BUS_LABEL_ROUTE_CLEARANCE = 0.9;
const NO_RAYCAST = () => {};
const ROUTE_OBSTACLE_CLEARANCE = 0.5;
const TRACK_WIDTH_SIGNAL = 0.28;
const TRACK_WIDTH_ELECTRICAL = 0.24;
const TRACK_WIDTH_INTERFACE = 0.32;
const TRACK_WIDTH_BUS = 0.4;
const TRACK_WIDTH_ACTIVE_DELTA = 0.08;
const BUS_ENTRY_WIDTH = 0.3;
const BUS_ENTRY_WIDTH_ACTIVE = 0.36;
const JUMP_TRACK_WIDTH = 0.3;

// ── Helpers ────────────────────────────────────────────────────

function netColor(net: SchematicNet, theme: ThemeColors): string {
  if (net.type === 'power') return getSemanticConnectionColor('power') || neutralConnectionColor(theme);
  if (net.type === 'ground') return getSemanticConnectionColor('ground') || neutralConnectionColor(theme);
  return protocolColorForName(net.name) ?? neutralConnectionColor(theme);
}

function endpointCategoryPriority(category: string): number {
  const normalized = category.toLowerCase();
  if (normalized === 'power') return 99;
  if (normalized === 'ground') return 97;

  const id = resolveStandardInterfaceId(category);
  switch (id) {
    case 'i2c':
      return 100;
    case 'spi':
    case 'qspi':
      return 95;
    case 'uart':
      return 90;
    case 'i2s':
      return 88;
    case 'usb':
      return 86;
    case 'can':
      return 84;
    default:
      return id ? 80 : 0;
  }
}

function dominantEndpointCategory(categories: string[]): string | null {
  let bestCategory: string | null = null;
  let bestPriority = 0;
  for (const category of categories) {
    const priority = endpointCategoryPriority(category);
    if (priority > bestPriority) {
      bestPriority = priority;
      bestCategory = category;
    }
  }
  return bestCategory;
}

function resolvedNetColor(
  net: SchematicNet,
  categories: string[],
  theme: ThemeColors,
): string {
  const dominantCategory = dominantEndpointCategory(categories);
  if (dominantCategory) {
    const semanticColor = getSemanticConnectionColor(dominantCategory);
    if (semanticColor) return semanticColor;
  }
  return netColor(net, theme);
}

function extractVoltageToken(raw: string): string | null {
  const m = raw.toLowerCase().match(/(\d+(?:\.\d+)?v\d+|\d+(?:\.\d+)?v)/);
  if (!m) return null;
  return m[1].replace(/[^a-z0-9]/g, '');
}

function netStubLabel(
  net: SchematicNet,
  worldPins: WorldPin[],
  interfaceTrack: boolean,
): string {
  if (net.type === 'power' || net.type === 'ground') {
    // Electrical/component-level power wiring should retain canonical net
    // naming (hv/lv) for schematic readability.
    if (!interfaceTrack) return net.name;

    // Block-level/interface wiring should read as power rails so we avoid
    // exposing hv/lv internals; include voltage token when available.
    const candidates = [
      ...worldPins.map((wp) => wp.pinNumber),
      net.name,
      net.id,
    ];
    for (const value of candidates) {
      const voltage = extractVoltageToken(value);
      if (voltage) return `power${voltage}`;
    }
    return 'power';
  }
  return net.name;
}

function isNetEmphasized(
  netId: string,
  selectedNetId: string | null,
  highlightedNetIds: Set<string>,
): boolean {
  if (selectedNetId !== null) return selectedNetId === netId;
  return highlightedNetIds.has(netId);
}

function hasAnyNetEmphasis(
  selectedNetId: string | null,
  highlightedNetIds: Set<string>,
): boolean {
  return selectedNetId !== null || highlightedNetIds.size > 0;
}

function isBusGroupEmphasized(
  group: BusGroup,
  selectedNetId: string | null,
  highlightedNetIds: Set<string>,
): boolean {
  if (selectedNetId !== null) return group.memberNetIds.has(selectedNetId);
  for (const netId of group.memberNetIds) {
    if (highlightedNetIds.has(netId)) return true;
  }
  return false;
}

function busRouteId(group: BusGroup): string {
  return `__bus__${group.id}`;
}

function busTrunkLabelPose(route: [number, number, number][]): {
  x: number;
  y: number;
  angle: number;
  segmentLength: number;
} {
  if (route.length < 2) return { x: 0, y: 0, angle: 0, segmentLength: 0 };

  let bestLen = -1;
  let bestX = route[0][0];
  let bestY = route[0][1];
  let bestAngle = 0;
  let bestSegmentLength = 0;

  for (let i = 0; i < route.length - 1; i++) {
    const a = route[i];
    const b = route[i + 1];
    const dx = b[0] - a[0];
    const dy = b[1] - a[1];
    const lenSq = dx * dx + dy * dy;
    if (lenSq <= bestLen) continue;
    bestLen = lenSq;
    bestX = (a[0] + b[0]) / 2;
    bestY = (a[1] + b[1]) / 2;
    bestSegmentLength = Math.sqrt(lenSq);
    let angle = Math.atan2(dy, dx);
    if (angle > Math.PI / 2 || angle < -Math.PI / 2) {
      angle += Math.PI;
      if (angle > Math.PI) angle -= Math.PI * 2;
    }
    bestAngle = angle;
  }

  return { x: bestX, y: bestY, angle: bestAngle, segmentLength: bestSegmentLength };
}

function estimateBusLabelGap(name: string): number {
  const chars = Math.max(name.trim().length, 1);
  const glyphWidth = BUS_LABEL_FONT_SIZE * 0.56;
  const spacingWidth = Math.max(0, chars - 1) * BUS_LABEL_FONT_SIZE * BUS_LABEL_LETTER_SPACING;
  return chars * glyphWidth + spacingWidth + BUS_LABEL_SIDE_PADDING * 2;
}

function protocolTypeForCategory(category: string | null): string | null {
  return resolveStandardInterfaceId(category);
}

function protocolTypeForName(name: string): string | null {
  return resolveStandardInterfaceId(name);
}

function protocolColorForName(name: string): string | null {
  return getStandardInterfaceColor(name);
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
  category?: string;
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
  portSignalOrders: Record<string, string[]> = {},
  currentPath: string[] = [],
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
        category: pin.category,
      });
    }
    pinMap.set(comp.id, pm);
  }
  for (const mod of sheet.modules) {
    const pm = new Map<string, PinInfo>();
    const orderedPins = getOrderedModuleInterfacePins(
      mod,
      getModulePinOrderForPath(portSignalOrders, currentPath, mod.id),
    );
    const anchor = orderedPins[0];
    const offset = getGridAlignmentOffset(anchor?.x, anchor?.y);
    for (const pin of orderedPins) {
      pm.set(pin.id, {
        x: pin.x + offset.x,
        y: pin.y + offset.y,
        side: pin.side,
        category: pin.category,
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
            category: port.category,
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
        category: port.category,
      });
    } else {
      pm.set('1', {
        x: port.pinX + offset.x,
        y: port.pinY + offset.y,
        side: port.pinSide,
        category: port.category,
      });
      if (port.passThrough) {
        pm.set('2', {
          x: -port.pinX + offset.x,
          y: -port.pinY + offset.y,
          side: oppositeSide(port.pinSide),
          category: port.category,
        });
      }
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
      category: pp.type,
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
  interfaceTrack: boolean;
}

interface StubNetData {
  net: SchematicNet;
  worldPins: WorldPin[];
  color: string;
  interfaceTrack: boolean;
}

interface PendingDirectNetData {
  routeId: string;
  net: SchematicNet;
  worldPins: WorldPin[];
  color: string;
  distance: number;
  forceDirect: boolean;
  preferStub: boolean;
  interfaceTrack: boolean;
}

interface PendingMultiNetData {
  net: SchematicNet;
  worldPins: WorldPin[];
  edges: Array<{ a: WorldPin; b: WorldPin }>;
  color: string;
  span: number;
  interfaceTrack: boolean;
}

interface RouteSegmentHandle {
  pointIndex: number;
  a: [number, number, number];
  b: [number, number, number];
  horizontal: boolean;
  length: number;
  cx: number;
  cy: number;
}

interface RouteHitSegment {
  pointIndex: number;
  horizontal: boolean;
  length: number;
  cx: number;
  cy: number;
}

function isPowerPortEndpoint(compId: string): boolean {
  return compId.startsWith('__pwr__');
}

function sideToward(from: { x: number; y: number }, to: { x: number; y: number }): string {
  const dx = to.x - from.x;
  const dy = to.y - from.y;
  if (Math.abs(dx) >= Math.abs(dy)) {
    return dx >= 0 ? 'right' : 'left';
  }
  return dy >= 0 ? 'top' : 'bottom';
}

function routeSideForEndpoint(pin: WorldPin, other: WorldPin): string {
  if (!isPowerPortEndpoint(pin.compId)) return pin.side;
  // Power/ground symbols are single-dot endpoints; route toward the counterpart
  // to avoid artificial down-then-up detours from a fixed pin-side constraint.
  return sideToward(pin, other);
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

function buildPassThroughBridgeEdges(
  worldPins: WorldPin[],
  passThroughPortIds: Set<string>,
): Array<{ a: WorldPin; b: WorldPin }> | null {
  if (worldPins.length < 3 || passThroughPortIds.size === 0) return null;

  const byPort = new Map<string, { pin1?: WorldPin; pin2?: WorldPin }>();
  for (const wp of worldPins) {
    if (!passThroughPortIds.has(wp.compId)) continue;
    if (wp.pinNumber !== '1' && wp.pinNumber !== '2') continue;
    const entry = byPort.get(wp.compId) || {};
    if (wp.pinNumber === '1') entry.pin1 = wp;
    if (wp.pinNumber === '2') entry.pin2 = wp;
    byPort.set(wp.compId, entry);
  }

  // Keep this conservative: one bridge port per net for now.
  const completePorts = [...byPort.entries()].filter(
    ([, pins]) => !!pins.pin1 && !!pins.pin2,
  );
  if (completePorts.length !== 1) return null;

  const [bridgePortId, pins] = completePorts[0];
  const pin1 = pins.pin1!;
  const pin2 = pins.pin2!;
  const others = worldPins.filter((wp) => wp.compId !== bridgePortId);
  if (others.length < 2) return null;

  const midX = (pin1.x + pin2.x) / 2;
  const midY = (pin1.y + pin2.y) / 2;
  const mostlyHorizontal = Math.abs(pin1.x - pin2.x) >= Math.abs(pin1.y - pin2.y);
  const leftLike = pin1.x <= pin2.x ? pin1 : pin2;
  const rightLike = pin1.x <= pin2.x ? pin2 : pin1;
  const bottomLike = pin1.y <= pin2.y ? pin1 : pin2;
  const topLike = pin1.y <= pin2.y ? pin2 : pin1;

  const edges: Array<{ a: WorldPin; b: WorldPin }> = [];
  const seen = new Set<string>();

  for (const other of others) {
    const d1 = manhattanDistance(other, pin1);
    const d2 = manhattanDistance(other, pin2);
    let target = d1 <= d2 ? pin1 : pin2;

    // Tie-break using relative side around bridge midpoint.
    if (Math.abs(d1 - d2) <= ROUTE_SPACING * 0.1) {
      if (mostlyHorizontal) {
        target = other.x <= midX ? leftLike : rightLike;
      } else {
        target = other.y <= midY ? bottomLike : topLike;
      }
    }

    const key = `${other.compId}:${other.pinNumber}->${target.compId}:${target.pinNumber}`;
    if (seen.has(key)) continue;
    seen.add(key);
    edges.push({ a: other, b: target });
  }

  return edges.length >= 2 ? edges : null;
}

function routePriority(net: SchematicNet): number {
  if (net.type === 'power') return 0;
  if (net.type === 'ground') return 1;
  if (net.type === 'bus') return 2;
  if (net.type === 'electrical') return 3;
  return 3;
}

function baseTrackWidth(net: SchematicNet, interfaceTrack: boolean): number {
  if (net.type === 'bus') return TRACK_WIDTH_BUS;
  if (interfaceTrack) return TRACK_WIDTH_INTERFACE;
  if (net.type === 'electrical') return TRACK_WIDTH_ELECTRICAL;
  return TRACK_WIDTH_SIGNAL;
}

function cloneRoute(route: [number, number, number][]): [number, number, number][] {
  return route.map((pt) => [pt[0], pt[1], pt[2] ?? 0]);
}

function dedupeRoute(route: [number, number, number][]): [number, number, number][] {
  if (route.length <= 1) return cloneRoute(route);
  const out: [number, number, number][] = [route[0]];
  for (let i = 1; i < route.length; i++) {
    const prev = out[out.length - 1];
    const cur = route[i];
    if (Math.abs(prev[0] - cur[0]) < 1e-6 && Math.abs(prev[1] - cur[1]) < 1e-6) continue;
    out.push([cur[0], cur[1], cur[2] ?? 0]);
  }
  return out;
}

function simplifyOrthRoute(route: [number, number, number][]): [number, number, number][] {
  const deduped = dedupeRoute(route);
  if (deduped.length <= 2) return deduped;
  const out: [number, number, number][] = [deduped[0]];
  for (let i = 1; i < deduped.length - 1; i++) {
    const a = out[out.length - 1];
    const b = deduped[i];
    const c = deduped[i + 1];
    const colinear =
      (Math.abs(a[0] - b[0]) < 1e-6 && Math.abs(b[0] - c[0]) < 1e-6) ||
      (Math.abs(a[1] - b[1]) < 1e-6 && Math.abs(b[1] - c[1]) < 1e-6);
    if (!colinear) out.push(b);
  }
  out.push(deduped[deduped.length - 1]);
  return out.length >= 2 ? out : deduped;
}

function anchorManualRoute(
  route: [number, number, number][],
  start: WorldPin,
  end: WorldPin,
): [number, number, number][] | null {
  if (!Array.isArray(route) || route.length < 2) return null;
  const next = simplifyOrthRoute(route);
  if (next.length < 2) return null;

  const firstSegDx = next[1][0] - next[0][0];
  const firstSegDy = next[1][1] - next[0][1];
  const lastIdx = next.length - 1;
  const lastSegDx = next[lastIdx][0] - next[lastIdx - 1][0];
  const lastSegDy = next[lastIdx][1] - next[lastIdx - 1][1];

  next[0] = [start.x, start.y, 0];
  next[lastIdx] = [end.x, end.y, 0];

  if (Math.abs(firstSegDx) >= Math.abs(firstSegDy)) {
    next[1] = [next[1][0], start.y, 0];
  } else {
    next[1] = [start.x, next[1][1], 0];
  }
  if (Math.abs(lastSegDx) >= Math.abs(lastSegDy)) {
    next[lastIdx - 1] = [next[lastIdx - 1][0], end.y, 0];
  } else {
    next[lastIdx - 1] = [end.x, next[lastIdx - 1][1], 0];
  }

  const anchored = simplifyOrthRoute(next);
  return anchored.length >= 2 ? anchored : null;
}

function getInteriorSegmentHandles(route: [number, number, number][]): RouteSegmentHandle[] {
  const simplified = simplifyOrthRoute(route);
  const handles: RouteSegmentHandle[] = [];
  for (let i = 0; i < simplified.length - 1; i++) {
    if (i === 0 || i + 1 === simplified.length - 1) continue;
    const a = simplified[i];
    const b = simplified[i + 1];
    const dx = b[0] - a[0];
    const dy = b[1] - a[1];
    const horizontal = Math.abs(dy) < 1e-6;
    const vertical = Math.abs(dx) < 1e-6;
    if (!horizontal && !vertical) continue;
    const length = Math.sqrt(dx * dx + dy * dy);
    if (length < 0.8) continue;
    handles.push({
      pointIndex: i,
      a,
      b,
      horizontal,
      length,
      cx: (a[0] + b[0]) / 2,
      cy: (a[1] + b[1]) / 2,
    });
  }
  return handles;
}

function getRouteHitSegments(route: [number, number, number][]): RouteHitSegment[] {
  const simplified = simplifyOrthRoute(route);
  const hits: RouteHitSegment[] = [];
  for (let i = 0; i < simplified.length - 1; i++) {
    const a = simplified[i];
    const b = simplified[i + 1];
    const dx = b[0] - a[0];
    const dy = b[1] - a[1];
    const horizontal = Math.abs(dy) < 1e-6;
    const vertical = Math.abs(dx) < 1e-6;
    if (!horizontal && !vertical) continue;
    const length = Math.sqrt(dx * dx + dy * dy);
    if (length < 0.2) continue;
    hits.push({
      pointIndex: i,
      horizontal,
      length,
      cx: (a[0] + b[0]) / 2,
      cy: (a[1] + b[1]) / 2,
    });
  }
  return hits;
}

function snapRouteCoord(v: number): number {
  return Math.round(v / ROUTE_SPACING) * ROUTE_SPACING;
}

function routesEqual(
  a: [number, number, number][],
  b: [number, number, number][],
): boolean {
  if (a.length !== b.length) return false;
  for (let i = 0; i < a.length; i++) {
    if (
      Math.abs(a[i][0] - b[i][0]) > 1e-6 ||
      Math.abs(a[i][1] - b[i][1]) > 1e-6 ||
      Math.abs((a[i][2] ?? 0) - (b[i][2] ?? 0)) > 1e-6
    ) {
      return false;
    }
  }
  return true;
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
    const size = getModuleRenderSize(mod);
    pushItem(mod.id, size.width, size.height);
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
  const portSignalOrders = useSchematicStore((s) => s.portSignalOrders);
  const routeOverrides = useSchematicStore((s) => s.routeOverrides);
  const selectedNetId = useSchematicStore((s) => s.selectedNetId);
  const selectedComponentIds = useSchematicStore((s) => s.selectedComponentIds);
  const ports = useCurrentPorts();
  const powerPorts = useCurrentPowerPorts();

  const sheet = useMemo(() => {
    if (!schematic) return null;
    return resolveSheet(getRootSheet(schematic), currentPath);
  }, [schematic, currentPath]);

  const lookup = useMemo<ItemLookup | null>(() => {
    if (!sheet) return null;
    return buildLookup(sheet, ports, powerPorts, portSignalOrders, currentPath);
  }, [sheet, ports, powerPorts, portSignalOrders, currentPath]);

  const pk = useMemo(
    () => (currentPath.length === 0 ? '__root__' : currentPath.join('/')) + ':',
    [currentPath],
  );

  // Net → color map (shared by crossing jumps + bus rendering)
  const netColorMap = useMemo(() => {
    const map = new Map<string, string>();
    if (!sheet || !lookup) return map;
    for (const net of sheet.nets) {
      const endpointCategories: string[] = [];
      for (const np of net.pins) {
        const resolved = resolvePinFromMap(lookup.pinMap.get(np.componentId), np.pinNumber);
        if (!resolved?.pin.category) continue;
        endpointCategories.push(resolved.pin.category);
      }
      map.set(net.id, resolvedNetColor(net, endpointCategories, theme));
    }
    return map;
  }, [sheet, lookup, theme]);

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
    const moduleIds = new Set(sheet.modules.map((m) => m.id));
    const portIds = new Set(ports.map((p) => p.id));
    const breakoutPortIds = new Set(
      ports
        .filter((p) => !!p.signals && p.signals.length >= 2)
        .map((p) => p.id),
    );
    const passThroughPortIds = new Set(
      ports
        .filter((p) => !!p.passThrough)
        .map((p) => p.id),
    );

    // Collect bus candidates alongside direct/stub classification
    const busInputs: NetForBus[] = [];

    for (const net of sheet.nets) {
      const color = netColorMap.get(net.id) || neutralConnectionColor(theme);

      // ── Power/ground nets: draw individual wires from each
      //    power port symbol to its connected component pin ──
      if (net.type === 'power' || net.type === 'ground') {
        const canUsePowerSymbols = net.pins.length > 0 && net.pins.every((np) => {
          const ppId = `__pwr__${net.id}__${np.componentId}__${np.pinNumber}`;
          return lookup.pinMap.has(ppId) && lookup.pinMap.has(np.componentId);
        });

        if (canUsePowerSymbols) {
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
            const dist = Math.sqrt(dx * dx + dy * dy);
            if (dx * dx + dy * dy < 0.5) continue;

            pendingDirects.push({
              routeId: ppId,
              net,
              worldPins: [wp0, wp1],
              color,
              distance: dist,
              forceDirect: true,
              preferStub: dist > POWER_PORT_DIRECT_MAX_DISTANCE,
              interfaceTrack: false,
            });
          }
          continue; // this net is fully rendered through power symbols
        }
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
      const interfaceTrack = worldPins.some(
        (wp) => moduleIds.has(wp.compId) || portIds.has(wp.compId),
      );
      const endpointCategories = worldPins
        .map((wp) => lookup.pinMap.get(wp.compId)?.get(wp.pinNumber)?.category)
        .filter((category): category is string => !!category);

      // 2-pin nets between exactly 2 items can be direct wires.
      const isTwoPinDirect = uniqueItems.size === 2 && worldPins.length === 2;

      if (isTwoPinDirect) {
        const dx = worldPins[0].x - worldPins[1].x;
        const dy = worldPins[0].y - worldPins[1].y;
        const dist = Math.sqrt(dx * dx + dy * dy);

        pendingDirects.push({
          routeId: net.id,
          net,
          worldPins,
          color,
          distance: dist,
          forceDirect: net.type !== 'signal',
          preferStub: false,
          interfaceTrack,
        });

        // Also register as bus candidate
        if (net.type !== 'power' && net.type !== 'ground') {
          // Promote interface-level electrical protocol lines (UART/SPI/I2C)
          // into bus candidates so they render as one bundled module link.
          const protocolType =
            protocolTypeForName(net.name) ||
            protocolTypeForCategory(dominantEndpointCategory(endpointCategories));
          const busCandidateType =
            net.type === 'bus' || (interfaceTrack && protocolType)
              ? 'bus'
              : net.type;
          busInputs.push({
            netId: net.id,
            netName: protocolType ?? net.name,
            netType: busCandidateType,
            allowBundle: !hasBreakoutSignalEndpoint,
            worldPins: worldPins.map((wp) => ({
              x: wp.x,
              y: wp.y,
              side: wp.side,
              compId: wp.compId,
            })),
          });
        }
      } else if (
        net.type !== 'bus' &&
        worldPins.length >= 3 &&
        worldPins.length <= MAX_MULTI_ROUTE_PINS
      ) {
        const span = computePinSpan(worldPins);
        const bridgeEdges = buildPassThroughBridgeEdges(worldPins, passThroughPortIds);
        const edges = bridgeEdges ?? buildMstEdges(worldPins);
        if (edges.length > 0 && span <= MULTI_ROUTE_MAX_SPAN) {
          pendingMultiNets.push({
            net,
            worldPins,
            edges,
            color,
            span,
            interfaceTrack,
          });
        } else {
          stubs.push({ net, worldPins, color, interfaceTrack });
        }
      } else {
        stubs.push({ net, worldPins, color, interfaceTrack });
      }
    }

    // ── Bus detection ───────────────────────────────────────
    const buses = detectBuses(busInputs, theme).map((group) => {
      const manualRoute = anchorManualRoute(
        routeOverrides[pk + busRouteId(group)] ?? [],
        {
          x: group.endpointA.mergeX,
          y: group.endpointA.mergeY,
          side: group.endpointA.side,
          compId: group.endpointA.itemId,
          pinNumber: '1',
        },
        {
          x: group.endpointB.mergeX,
          y: group.endpointB.mergeY,
          side: group.endpointB.side,
          compId: group.endpointB.itemId,
          pinNumber: '1',
        },
      );
      if (!manualRoute) return group;
      return {
        ...group,
        trunkRoute: manualRoute,
      };
    });

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
      const manualRoute = anchorManualRoute(
        routeOverrides[pk + pd.routeId] ?? [],
        a,
        b,
      );

      if (manualRoute) {
        directs.push({
          routeId: pd.routeId,
          net: pd.net,
          worldPins: pd.worldPins,
          route: manualRoute,
          color: pd.color,
          interfaceTrack: pd.interfaceTrack,
        });
        allSegments.push(...segmentsFromRoute(manualRoute, pd.net.id));
        existingSegments.push(...segmentsFromRoute(manualRoute, pd.routeId));
        continue;
      }

      if (pd.preferStub) {
        stubs.push({
          net: pd.net,
          worldPins: pd.worldPins,
          color: pd.color,
          interfaceTrack: pd.interfaceTrack,
        });
        continue;
      }

      const routedResult = routeOrthogonalWithHeuristics(
        a.x, a.y, routeSideForEndpoint(a, b),
        b.x, b.y, routeSideForEndpoint(b, a),
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
          q.overlaps > 0 ||
          q.crossings >= COMPLEX_ROUTE_CROSSINGS ||
          q.closeParallel > COMPLEX_ROUTE_PARALLEL ||
          q.score > COMPLEX_ROUTE_SCORE
        );

      if (shouldFallbackToLabels) {
        stubs.push({
          net: pd.net,
          worldPins: pd.worldPins,
          color: pd.color,
          interfaceTrack: pd.interfaceTrack,
        });
        continue;
      }

      const route = simplifyOrthRoute(routedResult.route);
      if (
        routeHitsObstacle(
          route,
          routeObstacles,
          new Set([a.compId, b.compId]),
        )
      ) {
        stubs.push({
          net: pd.net,
          worldPins: pd.worldPins,
          color: pd.color,
          interfaceTrack: pd.interfaceTrack,
        });
        continue;
      }
      directs.push({
        routeId: pd.routeId,
        net: pd.net,
        worldPins: pd.worldPins,
        route,
        color: pd.color,
        interfaceTrack: pd.interfaceTrack,
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
        const routeId = `${pm.net.id}::${i}`;
        const manualRoute = anchorManualRoute(
          routeOverrides[pk + routeId] ?? [],
          edge.a,
          edge.b,
        );
        if (manualRoute) {
          edgeRoutes.push({
            routeId,
            worldPins: [edge.a, edge.b],
            route: manualRoute,
          });
          stagedSegments.push(...segmentsFromRoute(manualRoute, routeId));
          continue;
        }

        const routedResult = routeOrthogonalWithHeuristics(
          edge.a.x, edge.a.y, routeSideForEndpoint(edge.a, edge.b),
          edge.b.x, edge.b.y, routeSideForEndpoint(edge.b, edge.a),
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

        const route = simplifyOrthRoute(routedResult.route);
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
        edgeRoutes.push({
          routeId,
          worldPins: [edge.a, edge.b],
          route,
        });
        stagedSegments.push(...segmentsFromRoute(route, routeId));
      }

      if (failed || edgeRoutes.length === 0) {
        stubs.push({
          net: pm.net,
          worldPins: pm.worldPins,
          color: pm.color,
          interfaceTrack: pm.interfaceTrack,
        });
        continue;
      }

      for (const er of edgeRoutes) {
        directs.push({
          routeId: er.routeId,
          net: pm.net,
          worldPins: er.worldPins,
          route: er.route,
          color: pm.color,
          interfaceTrack: pm.interfaceTrack,
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
  }, [sheet, lookup, positions, pk, netColorMap, theme, ports, routeOverrides]);

  const highlightedNetIds = useMemo(() => {
    const out = new Set<string>();
    if (!sheet || selectedComponentIds.length === 0) return out;
    const selectedIds = new Set(selectedComponentIds);
    for (const net of sheet.nets) {
      if (net.pins.some((pin) => selectedIds.has(pin.componentId))) {
        out.add(net.id);
      }
    }
    return out;
  }, [sheet, selectedComponentIds]);

  if (!sheet || !lookup) return null;

  const hasEmphasis = hasAnyNetEmphasis(selectedNetId, highlightedNetIds);

  return (
    <group raycast={NO_RAYCAST}>
      {/* Bus connections (thick trunk + fan entries) */}
      {busGroups.map((group) => (
        <BusConnection
          key={group.id}
          group={group}
          pk={pk}
          theme={theme}
          selectedNetId={selectedNetId}
          highlightedNetIds={highlightedNetIds}
        />
      ))}

      {/* Individual orthogonal connections */}
      {directNets.map(({ routeId, net, worldPins, route, color, interfaceTrack }) => {
        const isSelected = isNetEmphasized(net.id, selectedNetId, highlightedNetIds);
        const opacity = isSelected ? 1 : hasEmphasis ? 0.25 : 0.8;
        return (
          <OrthogonalConnection
            key={routeId}
            routeId={routeId}
            net={net}
            worldPins={worldPins}
            initialRoute={route}
            lookup={lookup}
            pk={pk}
            color={color}
            opacity={opacity}
            isActive={isSelected}
            interfaceTrack={interfaceTrack}
          />
        );
      })}

      {/* Stub connections */}
      {stubNets.map(({ net, worldPins, color, interfaceTrack }) => {
        const isSelected = isNetEmphasized(net.id, selectedNetId, highlightedNetIds);
        const opacity = isSelected ? 1 : hasEmphasis ? 0.25 : 0.8;
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
            interfaceTrack={interfaceTrack}
          />
        );
      })}

      {/* Crossing jump arcs */}
      <CrossingJumps
        crossings={crossings}
        netColorMap={netColorMap}
        theme={theme}
        selectedNetId={selectedNetId}
        highlightedNetIds={highlightedNetIds}
      />
    </group>
  );
});

// ════════════════════════════════════════════════════════════════
// ── Bus connection (trunk + entries + badge)
// ════════════════════════════════════════════════════════════════

const BusConnection = memo(function BusConnection({
  group,
  pk,
  theme,
  selectedNetId,
  highlightedNetIds,
}: {
  group: BusGroup;
  pk: string;
  theme: ThemeColors;
  selectedNetId: string | null;
  highlightedNetIds: Set<string>;
}) {
  const selectNet = useSchematicStore((s) => s.selectNet);
  const hoverNet = useSchematicStore((s) => s.hoverNet);
  const setRouteOverride = useSchematicStore((s) => s.setRouteOverride);
  const { camera, gl } = useThree();
  const lineRef = useRef<any>(null);
  const segmentDragActive = useRef(false);
  const raycaster = useRef(new THREE.Raycaster());
  const zPlane = useRef(new THREE.Plane(new THREE.Vector3(0, 0, 1), 0));
  const worldTarget = useRef(new THREE.Vector3());
  const ndc = useRef(new THREE.Vector2());

  const isActive = isBusGroupEmphasized(group, selectedNetId, highlightedNetIds);
  const opacity = isActive ? 1 : hasAnyNetEmphasis(selectedNetId, highlightedNetIds) ? 0.25 : 0.85;
  const firstNetId = [...group.memberNetIds][0];
  const explicitlySelected = selectedNetId !== null && group.memberNetIds.has(selectedNetId);
  const routeId = busRouteId(group);

  const { trunkRoute, endpointA, endpointB, color, name } = group;
  const labelPose = useMemo(() => busTrunkLabelPose(trunkRoute), [trunkRoute]);
  const labelGapLength = useMemo(() => {
    const preferredGap = estimateBusLabelGap(name);
    const maxGap = Math.max(0, labelPose.segmentLength - BUS_LABEL_ROUTE_CLEARANCE);
    return Math.min(preferredGap, maxGap);
  }, [labelPose.segmentLength, name]);
  const editableSegments = useMemo(
    () => getInteriorSegmentHandles(trunkRoute),
    [trunkRoute],
  );
  const routeHitSegments = useMemo(
    () => getRouteHitSegments(trunkRoute),
    [trunkRoute],
  );
  const editableSegmentByIndex = useMemo(
    () => new Map(editableSegments.map((seg) => [seg.pointIndex, seg] as const)),
    [editableSegments],
  );

  const screenToWorld = useCallback((clientX: number, clientY: number) => {
    const rect = gl.domElement.getBoundingClientRect();
    ndc.current.set(
      ((clientX - rect.left) / rect.width) * 2 - 1,
      -((clientY - rect.top) / rect.height) * 2 + 1,
    );
    raycaster.current.setFromCamera(ndc.current, camera);
    const hit = raycaster.current.ray.intersectPlane(zPlane.current, worldTarget.current);
    if (!hit) return null;
    return { x: worldTarget.current.x, y: worldTarget.current.y };
  }, [camera, gl]);

  useEffect(() => {
    if (!lineRef.current) return;
    writeRouteToLine2(lineRef.current, trunkRoute);
  }, [trunkRoute]);

  const beginSegmentDrag = useCallback((e: any, segment: RouteSegmentHandle) => {
    if (e.button !== 0) return;
    if (liveDrag.componentId) return;
    e.stopPropagation();

    const baseRoute = simplifyOrthRoute(trunkRoute);
    const idx = segment.pointIndex;
    if (idx <= 0 || idx + 1 >= baseRoute.length - 1) return;
    const startWorld = screenToWorld(
      (e.nativeEvent?.clientX ?? e.clientX) as number,
      (e.nativeEvent?.clientY ?? e.clientY) as number,
    );
    if (!startWorld) return;

    selectNet(firstNetId);
    segmentDragActive.current = true;

    const axis: 'x' | 'y' = segment.horizontal ? 'y' : 'x';
    const startCoord = axis === 'y' ? baseRoute[idx][1] : baseRoute[idx][0];
    const pointerStart = axis === 'y' ? startWorld.y : startWorld.x;
    let changed = false;
    let draggedRoute = baseRoute;

    const onMove = (me: PointerEvent) => {
      const world = screenToWorld(me.clientX, me.clientY);
      if (!world) return;
      const pointerNow = axis === 'y' ? world.y : world.x;
      const snapped = snapRouteCoord(startCoord + (pointerNow - pointerStart));
      const prevCoord = axis === 'y'
        ? draggedRoute[idx][1]
        : draggedRoute[idx][0];
      if (Math.abs(snapped - prevCoord) < 1e-6) return;

      const next = cloneRoute(baseRoute);
      if (axis === 'y') {
        next[idx][1] = snapped;
        next[idx + 1][1] = snapped;
      } else {
        next[idx][0] = snapped;
        next[idx + 1][0] = snapped;
      }
      draggedRoute = simplifyOrthRoute(next);
      changed = true;
      writeRouteToLine2(lineRef.current, draggedRoute);
      gl.domElement.style.cursor = axis === 'y' ? 'ns-resize' : 'ew-resize';
    };

    const onUp = () => {
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
      segmentDragActive.current = false;
      gl.domElement.style.cursor = 'auto';

      if (!changed) {
        writeRouteToLine2(lineRef.current, trunkRoute);
        return;
      }

      if (routesEqual(draggedRoute, simplifyOrthRoute(trunkRoute))) {
        writeRouteToLine2(lineRef.current, trunkRoute);
        return;
      }

      setRouteOverride(pk + routeId, draggedRoute);
    };

    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
  }, [trunkRoute, screenToWorld, selectNet, firstNetId, gl, setRouteOverride, pk, routeId]);

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
        ref={lineRef}
        points={trunkRoute}
        lineWidth={isActive ? TRACK_WIDTH_BUS + TRACK_WIDTH_ACTIVE_DELTA : TRACK_WIDTH_BUS}
        worldUnits
        color={color}
        transparent
        opacity={opacity}
      />

      {routeHitSegments.map((seg) => {
        const editable = editableSegmentByIndex.get(seg.pointIndex);
        const isEditableSegment = explicitlySelected && !!editable;
        const hitThickness = isEditableSegment
          ? BUS_ROUTE_DRAG_HIT_THICKNESS
          : BUS_ROUTE_PICK_HIT_THICKNESS;
        return (
          <mesh
            key={`${routeId}:hit:${seg.pointIndex}`}
            position={[seg.cx, seg.cy, 0.03]}
            onPointerDown={(e) => {
              if (!isEditableSegment || !editable) return;
              beginSegmentDrag(e, editable);
            }}
            onClick={(e) => {
              e.stopPropagation();
              if (isEditableSegment) return;
              selectNet(firstNetId);
            }}
            onPointerEnter={(e) => {
              e.stopPropagation();
              gl.domElement.style.cursor = isEditableSegment
                ? (seg.horizontal ? 'ns-resize' : 'ew-resize')
                : 'pointer';
            }}
            onPointerLeave={(e) => {
              e.stopPropagation();
              if (!segmentDragActive.current) {
                gl.domElement.style.cursor = 'auto';
              }
            }}
          >
            <planeGeometry
              args={seg.horizontal
                ? [seg.length, hitThickness]
                : [hitThickness, seg.length]}
            />
            <meshBasicMaterial transparent opacity={0.001} depthWrite={false} />
          </mesh>
        );
      })}

      {/* Fan-out entries at each endpoint */}
      <BusEntries
        endpoint={endpointA}
        color={color}
        opacity={opacity}
        lineWidth={isActive ? BUS_ENTRY_WIDTH_ACTIVE : BUS_ENTRY_WIDTH}
      />
      <BusEntries
        endpoint={endpointB}
        color={color}
        opacity={opacity}
        lineWidth={isActive ? BUS_ENTRY_WIDTH_ACTIVE : BUS_ENTRY_WIDTH}
      />

      {/* Inline protocol label on trunk */}
      <group
        position={[labelPose.x, labelPose.y, 0.04]}
        rotation={[0, 0, labelPose.angle]}
        raycast={NO_RAYCAST}
      >
        {labelGapLength > 0.8 && (
          <Line
            points={[
              [-labelGapLength * 0.5, 0, 0],
              [labelGapLength * 0.5, 0, 0],
            ]}
            lineWidth={(
              isActive
                ? TRACK_WIDTH_BUS + TRACK_WIDTH_ACTIVE_DELTA
                : TRACK_WIDTH_BUS
            ) + 0.14}
            worldUnits
            color={theme.bgPrimary}
            transparent={false}
            toneMapped={false}
            depthTest={false}
            raycast={NO_RAYCAST}
          />
        )}
        <Text
          fontSize={BUS_LABEL_FONT_SIZE}
          color={color}
          anchorX="center"
          anchorY="middle"
          letterSpacing={BUS_LABEL_LETTER_SPACING}
          fillOpacity={opacity * 0.9}
          font={undefined}
          raycast={NO_RAYCAST}
        >
          {name}
        </Text>
      </group>

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
              worldUnits
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
              worldUnits
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

// ════════════════════════════════════════════════════════════════
// ── Orthogonal direct connection
// ════════════════════════════════════════════════════════════════

const OrthogonalConnection = memo(function OrthogonalConnection({
  routeId,
  net,
  worldPins,
  initialRoute,
  lookup,
  pk,
  color,
  opacity,
  isActive,
  interfaceTrack,
}: {
  routeId: string;
  net: SchematicNet;
  worldPins: WorldPin[];
  initialRoute: [number, number, number][];
  lookup: ItemLookup;
  pk: string;
  color: string;
  opacity: number;
  isActive: boolean;
  interfaceTrack: boolean;
}) {
  const selectNet = useSchematicStore((s) => s.selectNet);
  const hoverNet = useSchematicStore((s) => s.hoverNet);
  const setRouteOverride = useSchematicStore((s) => s.setRouteOverride);
  const { camera, gl } = useThree();
  const lineRef = useRef<any>(null);
  const wasModified = useRef(false);
  const lastVersion = useRef(-1);
  const segmentDragActive = useRef(false);

  const raycaster = useRef(new THREE.Raycaster());
  const zPlane = useRef(new THREE.Plane(new THREE.Vector3(0, 0, 1), 0));
  const worldTarget = useRef(new THREE.Vector3());
  const ndc = useRef(new THREE.Vector2());

  const editableSegments = useMemo(
    () => getInteriorSegmentHandles(initialRoute),
    [initialRoute],
  );
  const routeHitSegments = useMemo(
    () => getRouteHitSegments(initialRoute),
    [initialRoute],
  );
  const editableSegmentByIndex = useMemo(
    () => new Map(editableSegments.map((seg) => [seg.pointIndex, seg] as const)),
    [editableSegments],
  );

  const screenToWorld = useCallback((clientX: number, clientY: number) => {
    const rect = gl.domElement.getBoundingClientRect();
    ndc.current.set(
      ((clientX - rect.left) / rect.width) * 2 - 1,
      -((clientY - rect.top) / rect.height) * 2 + 1,
    );
    raycaster.current.setFromCamera(ndc.current, camera);
    const hit = raycaster.current.ray.intersectPlane(zPlane.current, worldTarget.current);
    if (!hit) return null;
    return { x: worldTarget.current.x, y: worldTarget.current.y };
  }, [camera, gl]);

  useEffect(() => {
    if (!lineRef.current) return;
    writeRouteToLine2(lineRef.current, initialRoute);
  }, [initialRoute]);

  useFrame(() => {
    if (!lineRef.current) return;
    if (segmentDragActive.current) return;
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

    const liveRoute = simplifyOrthRoute(
      computeOrthogonalRoute(
        liveWP[0].x, liveWP[0].y, routeSideForEndpoint(liveWP[0], liveWP[1]),
        liveWP[1].x, liveWP[1].y, routeSideForEndpoint(liveWP[1], liveWP[0]),
      ),
    );
    writeRouteToLine2(lineRef.current, liveRoute);
  });

  const beginSegmentDrag = useCallback((e: any, segment: RouteSegmentHandle) => {
    if (e.button !== 0) return;
    if (liveDrag.componentId) return;
    e.stopPropagation();

    const baseRoute = simplifyOrthRoute(initialRoute);
    const idx = segment.pointIndex;
    if (idx <= 0 || idx + 1 >= baseRoute.length - 1) return;
    const startWorld = screenToWorld(
      (e.nativeEvent?.clientX ?? e.clientX) as number,
      (e.nativeEvent?.clientY ?? e.clientY) as number,
    );
    if (!startWorld) return;

    selectNet(net.id);
    segmentDragActive.current = true;

    const axis: 'x' | 'y' = segment.horizontal ? 'y' : 'x';
    const startCoord = axis === 'y' ? baseRoute[idx][1] : baseRoute[idx][0];
    const pointerStart = axis === 'y' ? startWorld.y : startWorld.x;
    let changed = false;
    let draggedRoute = baseRoute;

    const onMove = (me: PointerEvent) => {
      const world = screenToWorld(me.clientX, me.clientY);
      if (!world) return;
      const pointerNow = axis === 'y' ? world.y : world.x;
      const snapped = snapRouteCoord(startCoord + (pointerNow - pointerStart));
      const prevCoord = axis === 'y'
        ? draggedRoute[idx][1]
        : draggedRoute[idx][0];
      if (Math.abs(snapped - prevCoord) < 1e-6) return;

      const next = cloneRoute(baseRoute);
      if (axis === 'y') {
        next[idx][1] = snapped;
        next[idx + 1][1] = snapped;
      } else {
        next[idx][0] = snapped;
        next[idx + 1][0] = snapped;
      }
      draggedRoute = simplifyOrthRoute(next);
      changed = true;
      writeRouteToLine2(lineRef.current, draggedRoute);
      gl.domElement.style.cursor = axis === 'y' ? 'ns-resize' : 'ew-resize';
    };

    const onUp = () => {
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
      segmentDragActive.current = false;
      gl.domElement.style.cursor = 'auto';

      if (!changed) {
        writeRouteToLine2(lineRef.current, initialRoute);
        return;
      }

      if (routesEqual(draggedRoute, simplifyOrthRoute(initialRoute))) {
        writeRouteToLine2(lineRef.current, initialRoute);
        return;
      }

      setRouteOverride(pk + routeId, draggedRoute);
    };

    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
  }, [pk, routeId, initialRoute, screenToWorld, selectNet, net.id, setRouteOverride, gl]);

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
        lineWidth={isActive
          ? baseTrackWidth(net, interfaceTrack) + TRACK_WIDTH_ACTIVE_DELTA
          : baseTrackWidth(net, interfaceTrack)}
        worldUnits
        transparent
        opacity={opacity}
      />

      {routeHitSegments.map((seg) => {
        const editable = editableSegmentByIndex.get(seg.pointIndex);
        const isEditableSegment = isActive && !!editable;
        const hitThickness = isEditableSegment
          ? ROUTE_DRAG_HIT_THICKNESS
          : ROUTE_PICK_HIT_THICKNESS;
        return (
        <mesh
          key={`${routeId}:hit:${seg.pointIndex}`}
          position={[seg.cx, seg.cy, 0.02]}
          onPointerDown={(e) => {
            if (!isEditableSegment || !editable) return;
            beginSegmentDrag(e, editable);
          }}
          onClick={(e) => {
            e.stopPropagation();
            if (isEditableSegment) return;
            selectNet(net.id);
          }}
          onPointerEnter={(e) => {
            e.stopPropagation();
            gl.domElement.style.cursor = isEditableSegment
              ? (seg.horizontal ? 'ns-resize' : 'ew-resize')
              : 'pointer';
          }}
          onPointerLeave={(e) => {
            e.stopPropagation();
            if (!segmentDragActive.current) {
              gl.domElement.style.cursor = 'auto';
            }
          }}
        >
          <planeGeometry
            args={seg.horizontal
              ? [seg.length, hitThickness]
              : [hitThickness, seg.length]}
          />
          <meshBasicMaterial transparent opacity={0.001} depthWrite={false} />
        </mesh>
        );
      })}

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
  interfaceTrack,
}: {
  net: SchematicNet;
  worldPins: WorldPin[];
  lookup: ItemLookup;
  pk: string;
  color: string;
  opacity: number;
  isActive: boolean;
  interfaceTrack: boolean;
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
              lineWidth={isActive
                ? baseTrackWidth(net, interfaceTrack) + TRACK_WIDTH_ACTIVE_DELTA
                : baseTrackWidth(net, interfaceTrack)}
              worldUnits
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
              {netStubLabel(net, worldPins, interfaceTrack)}
            </Text>
            <mesh position={[endX, endY, 0.02]} raycast={NO_RAYCAST}>
              <circleGeometry args={[0.1, 8]} />
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
  highlightedNetIds,
}: {
  crossings: Crossing[];
  netColorMap: Map<string, string>;
  theme: ThemeColors;
  selectedNetId: string | null;
  highlightedNetIds: Set<string>;
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
          highlightedNetIds={highlightedNetIds}
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
  highlightedNetIds,
}: {
  crossing: Crossing;
  netColorMap: Map<string, string>;
  theme: ThemeColors;
  selectedNetId: string | null;
  highlightedNetIds: Set<string>;
}) {
  const { x, y, hNetId, vNetId } = crossing;
  const hColor = netColorMap.get(hNetId) || neutralConnectionColor(theme);
  const vColor = netColorMap.get(vNetId) || neutralConnectionColor(theme);

  const hActive = isNetEmphasized(hNetId, selectedNetId, highlightedNetIds);
  const vActive = isNetEmphasized(vNetId, selectedNetId, highlightedNetIds);
  const hasEmphasis = hasAnyNetEmphasis(selectedNetId, highlightedNetIds);
  const hOpacity = hActive ? 1 : hasEmphasis ? 0.25 : 0.8;
  const vOpacity = vActive ? 1 : hasEmphasis ? 0.25 : 0.8;

  const arcPts = useMemo(
    (): [number, number, number][] =>
      generateJumpArc(x, y).map((p) => [p[0], p[1], 0.003]),
    [x, y],
  );

  const r = JUMP_RADIUS;
  const maskRadius = r + JUMP_MASK_OVERDRAW;
  const verticalHalfSpan = maskRadius + JUMP_VERTICAL_REPAINT_MARGIN;

  return (
    <group>
      <mesh position={[x, y, 0.001]} raycast={NO_RAYCAST}>
        <circleGeometry args={[maskRadius, JUMP_MASK_SEGMENTS]} />
        <meshBasicMaterial color={theme.bgPrimary} toneMapped={false} />
      </mesh>
      <Line
        points={[[x, y - verticalHalfSpan, 0.002], [x, y + verticalHalfSpan, 0.002]]}
        color={vColor}
        lineWidth={JUMP_TRACK_WIDTH}
        worldUnits
        transparent
        opacity={vOpacity}
        raycast={NO_RAYCAST}
      />
      <Line
        points={arcPts}
        color={hColor}
        lineWidth={JUMP_TRACK_WIDTH}
        worldUnits
        transparent
        opacity={hOpacity}
        raycast={NO_RAYCAST}
      />
    </group>
  );
});
