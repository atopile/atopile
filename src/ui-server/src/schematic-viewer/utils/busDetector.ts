import type { ThemeColors } from './theme';

export interface NetForBus {
  netId: string;
  netName: string;
  netType: string;
  allowBundle: boolean;
  worldPins: Array<{
    x: number;
    y: number;
    side: string;
    compId: string;
  }>;
}

export interface BusEndpointPin {
  x: number;
  y: number;
  stubX: number;
  stubY: number;
  side: 'left' | 'right' | 'top' | 'bottom';
  netName: string;
}

export interface BusEndpoint {
  itemId: string;
  side: 'left' | 'right' | 'top' | 'bottom';
  mergeX: number;
  mergeY: number;
  pins: BusEndpointPin[];
}

export interface BusGroup {
  id: string;
  name: string;
  busType: 'i2c' | 'spi' | 'uart' | 'signal';
  color: string;
  memberNetIds: Set<string>;
  endpointA: BusEndpoint;
  endpointB: BusEndpoint;
  trunkRoute: [number, number, number][];
}

function protocolTypeFromName(name: string): BusGroup['busType'] {
  const lower = name.toLowerCase();
  if (lower.includes('i2c') || lower.includes('scl') || lower.includes('sda')) return 'i2c';
  if (lower.includes('spi') || lower.includes('miso') || lower.includes('mosi') || lower.includes('sck')) return 'spi';
  if (lower.includes('uart') || lower.includes('tx') || lower.includes('rx')) return 'uart';
  return 'signal';
}

function colorForType(type: BusGroup['busType'], theme: ThemeColors): string {
  if (type === 'i2c') return theme.busI2C;
  if (type === 'spi') return theme.busSPI;
  if (type === 'uart') return theme.busUART;
  return theme.pinSignal;
}

function chooseEndpoints(net: NetForBus): [NetForBus['worldPins'][number], NetForBus['worldPins'][number]] | null {
  if (net.worldPins.length < 2) return null;
  let left = net.worldPins[0];
  let right = net.worldPins[0];
  for (const pin of net.worldPins) {
    if (pin.x < left.x) left = pin;
    if (pin.x > right.x) right = pin;
  }
  return [left, right];
}

function endpointKey(pin: { compId: string; side: string }): string {
  return `${pin.compId}|${pin.side}`;
}

function stubPoint(pin: { x: number; y: number; side: string }): { x: number; y: number } {
  const side = pin.side === 'left' || pin.side === 'right' || pin.side === 'top' || pin.side === 'bottom'
    ? pin.side
    : 'right';
  const d = 0.8;
  switch (side) {
    case 'left':
      return { x: pin.x + d, y: pin.y };
    case 'right':
      return { x: pin.x - d, y: pin.y };
    case 'top':
      return { x: pin.x, y: pin.y - d };
    case 'bottom':
      return { x: pin.x, y: pin.y + d };
  }
}

function buildTrunk(a: BusEndpoint, b: BusEndpoint): [number, number, number][] {
  if (Math.abs(a.mergeY - b.mergeY) < 1e-6 || Math.abs(a.mergeX - b.mergeX) < 1e-6) {
    return [
      [a.mergeX, a.mergeY, 0],
      [b.mergeX, b.mergeY, 0],
    ];
  }
  const midX = (a.mergeX + b.mergeX) / 2;
  return [
    [a.mergeX, a.mergeY, 0],
    [midX, a.mergeY, 0],
    [midX, b.mergeY, 0],
    [b.mergeX, b.mergeY, 0],
  ];
}

export function detectBuses(inputs: NetForBus[], theme: ThemeColors): BusGroup[] {
  const candidates = inputs.filter((net) => net.allowBundle && net.netType === 'bus');
  const grouped = new Map<string, Array<{
    net: NetForBus;
    a: NetForBus['worldPins'][number];
    b: NetForBus['worldPins'][number];
  }>>();

  for (const net of candidates) {
    const endpoints = chooseEndpoints(net);
    if (!endpoints) continue;
    const [a, b] = endpoints;
    const keyA = endpointKey(a);
    const keyB = endpointKey(b);
    const key = keyA < keyB ? `${keyA}--${keyB}` : `${keyB}--${keyA}`;
    const bucket = grouped.get(key) ?? [];
    bucket.push({ net, a, b });
    grouped.set(key, bucket);
  }

  const out: BusGroup[] = [];
  for (const [key, entries] of grouped.entries()) {
    if (entries.length < 2) continue;

    const exemplar = entries[0];
    const type = protocolTypeFromName(exemplar.net.netName);
    const endpointA: BusEndpoint = {
      itemId: exemplar.a.compId,
      side: (exemplar.a.side === 'left' || exemplar.a.side === 'right' || exemplar.a.side === 'top' || exemplar.a.side === 'bottom') ? exemplar.a.side : 'right',
      mergeX: stubPoint(exemplar.a).x,
      mergeY: stubPoint(exemplar.a).y,
      pins: [],
    };
    const endpointB: BusEndpoint = {
      itemId: exemplar.b.compId,
      side: (exemplar.b.side === 'left' || exemplar.b.side === 'right' || exemplar.b.side === 'top' || exemplar.b.side === 'bottom') ? exemplar.b.side : 'left',
      mergeX: stubPoint(exemplar.b).x,
      mergeY: stubPoint(exemplar.b).y,
      pins: [],
    };

    const memberNetIds = new Set<string>();
    for (const entry of entries) {
      memberNetIds.add(entry.net.netId);
      const aStub = stubPoint(entry.a);
      const bStub = stubPoint(entry.b);
      endpointA.pins.push({
        x: entry.a.x,
        y: entry.a.y,
        stubX: aStub.x,
        stubY: aStub.y,
        side: (entry.a.side === 'left' || entry.a.side === 'right' || entry.a.side === 'top' || entry.a.side === 'bottom') ? entry.a.side : 'right',
        netName: entry.net.netName,
      });
      endpointB.pins.push({
        x: entry.b.x,
        y: entry.b.y,
        stubX: bStub.x,
        stubY: bStub.y,
        side: (entry.b.side === 'left' || entry.b.side === 'right' || entry.b.side === 'top' || entry.b.side === 'bottom') ? entry.b.side : 'left',
        netName: entry.net.netName,
      });
    }

    out.push({
      id: `bus:${key}`,
      name: type.toUpperCase(),
      busType: type,
      color: colorForType(type, theme),
      memberNetIds,
      endpointA,
      endpointB,
      trunkRoute: buildTrunk(endpointA, endpointB),
    });
  }

  return out;
}
