import type {
  ComponentPosition,
  SchematicComponent,
  SchematicModule,
  SchematicNet,
  SchematicPin,
  SchematicPort,
  SchematicPowerPort,
  SchematicSheet,
} from '../types/schematic';
import {
  PIN_GRID_MM,
  getComponentGridAlignmentOffset,
  getGridAlignmentOffset,
  getPortGridAlignmentOffset,
  getPowerPortGridAlignmentOffset,
  getNormalizedComponentPinGeometry,
  snapToPinGrid,
  transformPinOffset,
} from '../types/schematic';

const GRID_X = 70;
const GRID_Y = 40;
const PORT_OFFSET = PIN_GRID_MM * 5;
const POWER_PORT_OFFSET = PIN_GRID_MM;

type PositionMap = Record<string, ComponentPosition>;

export function snapToGrid(value: number): number {
  return snapToPinGrid(value);
}

export function mergePositions(base: PositionMap, saved: PositionMap): PositionMap {
  return {
    ...base,
    ...saved,
  };
}

function netPinsForComponent(net: SchematicNet, componentId: string): string[] {
  return net.pins.filter((p) => p.componentId === componentId).map((p) => p.pinNumber);
}

function findComponent(sheet: SchematicSheet, id: string): SchematicComponent | undefined {
  return sheet.components.find((c) => c.id === id);
}

function findModule(sheet: SchematicSheet, id: string): SchematicModule | undefined {
  return sheet.modules.find((m) => m.id === id);
}

function findPin(component: SchematicComponent, pinNumber: string): SchematicPin | undefined {
  return component.pins.find((p) => p.number === pinNumber);
}

function baseItemPosition(index: number): ComponentPosition {
  const col = index % 4;
  const row = Math.floor(index / 4);
  return {
    x: snapToGrid(col * GRID_X),
    y: snapToGrid(-row * GRID_Y),
    rotation: 0,
  };
}

function compPinWorld(pos: ComponentPosition, component: SchematicComponent, pin: SchematicPin): { x: number; y: number } {
  const align = getComponentGridAlignmentOffset(component);
  const norm = getNormalizedComponentPinGeometry(component, pin);
  const tp = transformPinOffset(
    norm.x + align.x,
    norm.y + align.y,
    pos.rotation,
    pos.mirrorX,
    pos.mirrorY,
  );
  return {
    x: snapToGrid(pos.x + tp.x),
    y: snapToGrid(pos.y + tp.y),
  };
}

function modulePinWorld(
  pos: ComponentPosition,
  module: SchematicModule,
  pinId: string,
): { x: number; y: number; side: 'left' | 'right' | 'top' | 'bottom' } | null {
  const pin = module.interfacePins.find((p) => p.id === pinId);
  if (!pin) return null;
  const align = getGridAlignmentOffset(pin.x, pin.y);
  const tp = transformPinOffset(pin.x + align.x, pin.y + align.y, pos.rotation, pos.mirrorX, pos.mirrorY);
  return {
    x: snapToGrid(pos.x + tp.x),
    y: snapToGrid(pos.y + tp.y),
    side: pin.side,
  };
}

function oppositeSide(side: 'left' | 'right' | 'top' | 'bottom'): 'left' | 'right' | 'top' | 'bottom' {
  if (side === 'left') return 'right';
  if (side === 'right') return 'left';
  if (side === 'top') return 'bottom';
  return 'top';
}

function desiredOffsetForSide(side: 'left' | 'right' | 'top' | 'bottom', distance: number): { x: number; y: number } {
  if (side === 'left') return { x: -distance, y: 0 };
  if (side === 'right') return { x: distance, y: 0 };
  if (side === 'top') return { x: 0, y: distance };
  return { x: 0, y: -distance };
}

function portPinLocal(
  port: SchematicPort,
  pinNumber: string,
): { x: number; y: number } | null {
  if (port.signals && port.signalPins) {
    if (pinNumber === '1') return { x: port.pinX, y: port.pinY };
    const signal = port.signalPins[pinNumber];
    return signal ? { x: signal.x, y: signal.y } : null;
  }
  if (pinNumber === '1') return { x: port.pinX, y: port.pinY };
  if (port.passThrough && pinNumber === '2') return { x: -port.pinX, y: -port.pinY };
  return null;
}

function transformedPortPin(
  port: SchematicPort,
  pinNumber: string,
  rotation: number,
): { x: number; y: number } | null {
  const local = portPinLocal(port, pinNumber);
  if (!local) return null;
  const align = getPortGridAlignmentOffset(port);
  const tp = transformPinOffset(local.x + align.x, local.y + align.y, rotation, false, false);
  return { x: tp.x, y: tp.y };
}

function transformedPortSide(
  port: SchematicPort,
  pinNumber: string,
  rotation: number,
): 'left' | 'right' | 'top' | 'bottom' {
  const base =
    pinNumber === '2' && port.passThrough
      ? oppositeSide(port.pinSide)
      : pinNumber === '1'
        ? port.pinSide
        : port.pinSide;
  const tp = transformPinOffset(
    base === 'left' ? -1 : base === 'right' ? 1 : 0,
    base === 'bottom' ? -1 : base === 'top' ? 1 : 0,
    rotation,
    false,
    false,
  );
  if (Math.abs(tp.x) >= Math.abs(tp.y)) return tp.x >= 0 ? 'right' : 'left';
  return tp.y >= 0 ? 'top' : 'bottom';
}

function choosePortRotation(
  port: SchematicPort,
  pinNumber: string,
  target: { x: number; y: number },
  desiredOffset: { x: number; y: number },
): number {
  const pinWorld = { x: target.x + desiredOffset.x, y: target.y + desiredOffset.y };
  const desiredVecLen = Math.hypot(desiredOffset.x, desiredOffset.y) || 1;
  let bestRot = 0;
  let bestScore = -Infinity;

  for (const rotation of [0, 90, 180, 270]) {
    const tp = transformedPortPin(port, pinNumber, rotation);
    if (!tp) continue;
    const center = { x: pinWorld.x - tp.x, y: pinWorld.y - tp.y };
    const centerVec = { x: center.x - target.x, y: center.y - target.y };
    const score = (centerVec.x * desiredOffset.x + centerVec.y * desiredOffset.y) / desiredVecLen;
    if (score > bestScore) {
      bestScore = score;
      bestRot = rotation;
    }
  }

  return bestRot;
}

function placePort(
  port: SchematicPort,
  target: { x: number; y: number; side: 'left' | 'right' | 'top' | 'bottom' },
  pinNumber: string,
  rotationOverride?: number,
): ComponentPosition {
  const desiredOffset = desiredOffsetForSide(target.side, PORT_OFFSET);
  const rotation = rotationOverride ?? choosePortRotation(port, pinNumber, target, desiredOffset);
  const tp = transformedPortPin(port, pinNumber, rotation) ?? { x: 0, y: 0 };
  const pinWorld = {
    x: snapToGrid(target.x + desiredOffset.x),
    y: snapToGrid(target.y + desiredOffset.y),
  };

  return {
    x: snapToGrid(pinWorld.x - tp.x),
    y: snapToGrid(pinWorld.y - tp.y),
    rotation,
  };
}

function placePowerPort(
  powerPort: SchematicPowerPort,
  target: { x: number; y: number; side: 'left' | 'right' | 'top' | 'bottom' },
): ComponentPosition {
  const offset = desiredOffsetForSide(target.side, POWER_PORT_OFFSET);
  const align = getPowerPortGridAlignmentOffset(powerPort);
  const pinWorld = {
    x: snapToGrid(target.x + offset.x),
    y: snapToGrid(target.y + offset.y),
  };

  return {
    x: snapToGrid(pinWorld.x - (powerPort.pinX + align.x)),
    y: snapToGrid(pinWorld.y - (powerPort.pinY + align.y)),
    rotation: 0,
  };
}

function isDecoupler(component: SchematicComponent): boolean {
  return component.reference.toUpperCase().startsWith('C');
}

function placeDecouplers(sheet: SchematicSheet, positions: PositionMap): void {
  const decouplers = sheet.components.filter(isDecoupler);
  if (decouplers.length === 0) return;

  const placed = new Set<string>();
  let bandOffset = 0;

  for (const net of sheet.nets) {
    if (net.type !== 'power') continue;
    const decPins = net.pins.filter((p) => findComponent(sheet, p.componentId) && isDecoupler(findComponent(sheet, p.componentId)!));
    if (decPins.length === 0) continue;

    const anchors = net.pins.filter((p) => {
      const c = findComponent(sheet, p.componentId);
      return c && !isDecoupler(c);
    });

    const anchorComp = anchors.length > 0 ? findComponent(sheet, anchors[0].componentId) : undefined;
    const anchorPos = anchorComp ? positions[anchorComp.id] : undefined;
    const baseX = anchorPos ? anchorPos.x : 0;
    const baseY = anchorPos ? anchorPos.y + (anchorComp?.bodyHeight ?? 10) / 2 + 8 + bandOffset : bandOffset;

    let cursorX = baseX;
    let topAlignY = baseY;
    for (const pin of decPins) {
      const comp = findComponent(sheet, pin.componentId);
      if (!comp || placed.has(comp.id)) continue;
      const x = snapToGrid(cursorX);
      const y = snapToGrid(topAlignY - comp.bodyHeight / 2);
      positions[comp.id] = { x, y, rotation: 0 };
      placed.add(comp.id);
      cursorX += comp.bodyWidth + 8;
    }

    bandOffset += 14;
  }

  for (const c of decouplers) {
    if (positions[c.id]) continue;
    positions[c.id] = baseItemPosition(Object.keys(positions).length);
  }
}

export function autoLayoutSheet(
  sheet: SchematicSheet,
  ports: SchematicPort[],
  powerPorts: SchematicPowerPort[],
  suggestedSignalOrders: Record<string, string[]> = {},
): PositionMap {
  const positions: PositionMap = {};

  const mainModules = [...sheet.modules];
  const mainComponents = sheet.components.filter((c) => !isDecoupler(c));
  const mainItems: Array<{ id: string }> = [
    ...mainModules.map((m) => ({ id: m.id })),
    ...mainComponents.map((c) => ({ id: c.id })),
  ];

  for (let i = 0; i < mainItems.length; i++) {
    positions[mainItems[i].id] = baseItemPosition(i);
  }

  placeDecouplers(sheet, positions);

  // Anchor ports based on connected net endpoints.
  const sideOccupancy = new Map<string, number>();
  const portById = new Map(ports.map((p) => [p.id, p] as const));
  for (const port of ports) {
    const connectedNets = sheet.nets.filter((n) => n.pins.some((p) => p.componentId === port.id));
    if (connectedNets.length === 0) {
      positions[port.id] = { x: 0, y: 0, rotation: 0 };
      continue;
    }

    // Build signal ordering hints from target pin Y ordering.
    if (port.signals && port.signals.length > 1) {
      const signalToTargetY: Array<{ signal: string; y: number }> = [];
      for (const signal of port.signals) {
        const net = connectedNets.find((n) => n.pins.some((p) => p.componentId === port.id && p.pinNumber === signal));
        if (!net) continue;
        const endpoint = net.pins.find((p) => p.componentId !== port.id);
        if (!endpoint) continue;
        const comp = findComponent(sheet, endpoint.componentId);
        const compPos = comp ? positions[comp.id] : undefined;
        const pin = comp && compPos ? findPin(comp, endpoint.pinNumber) : undefined;
        if (!comp || !compPos || !pin) continue;
        const world = compPinWorld(compPos, comp, pin);
        signalToTargetY.push({ signal, y: world.y });
      }
      if (signalToTargetY.length === port.signals.length) {
        signalToTargetY.sort((a, b) => b.y - a.y);
        const ordered = signalToTargetY.map((s) => s.signal);
        suggestedSignalOrders[port.id] = ordered;
        port.signals = ordered;
      }
    }

    let chosenTarget: { x: number; y: number; side: 'left' | 'right' | 'top' | 'bottom' } | null = null;
    let chosenPinNumber = '1';
    let rotationOverride: number | undefined;

    for (const net of connectedNets) {
      const portPins = netPinsForComponent(net, port.id);
      if (portPins.length === 0) continue;
      const endpointCandidates = net.pins.filter((p) => p.componentId !== port.id);
      if (endpointCandidates.length === 0) continue;

      // For breakout ports, prefer anchoring to already-placed pass-through ports.
      let endpoint = endpointCandidates[0];
      if (port.signals && port.signals.length > 1) {
        const passThroughEndpoint = endpointCandidates.find((p) => {
          const otherPort = portById.get(p.componentId);
          return !!otherPort?.passThrough && positions[p.componentId] && p.pinNumber === '2';
        });
        if (passThroughEndpoint) endpoint = passThroughEndpoint;
      }

      const endpointPort = portById.get(endpoint.componentId);
      const endpointPortPos = endpointPort ? positions[endpoint.componentId] : undefined;
      if (endpointPort && endpointPortPos) {
        const epRotation = endpointPortPos.rotation ?? 0;
        const epLocal = transformedPortPin(endpointPort, endpoint.pinNumber, epRotation);
        if (epLocal) {
          const epSide =
            endpointPort.passThrough && endpoint.pinNumber === '2'
              ? endpointPort.side
              : transformedPortSide(endpointPort, endpoint.pinNumber, epRotation);
          chosenTarget = {
            x: snapToGrid(endpointPortPos.x + epLocal.x),
            y: snapToGrid(endpointPortPos.y + epLocal.y),
            side: epSide,
          };
          chosenPinNumber = portPins[0] ?? '1';
          // Keep breakout signal ordering stable when staging from pass-through bridges.
          if (port.signals && port.signals.length > 1 && endpointPort.passThrough) {
            rotationOverride = 0;
          }
          break;
        }
      }

      const comp = findComponent(sheet, endpoint.componentId);
      if (comp) {
        const compPos = positions[comp.id];
        const pin = findPin(comp, endpoint.pinNumber);
        if (compPos && pin) {
          const world = compPinWorld(compPos, comp, pin);
          chosenTarget = { x: world.x, y: world.y, side: pin.side };
          chosenPinNumber = portPins[0] ?? '1';
          break;
        }
      }

      const mod = findModule(sheet, endpoint.componentId);
      if (mod) {
        const modPos = positions[mod.id];
        if (modPos) {
          const world = modulePinWorld(modPos, mod, endpoint.pinNumber);
          if (world) {
            chosenTarget = world;
            chosenPinNumber = portPins[0] ?? '1';
            break;
          }
        }
      }
    }

    if (!chosenTarget) {
      positions[port.id] = { x: 0, y: 0, rotation: 0 };
      continue;
    }

    const base = placePort(port, chosenTarget, chosenPinNumber, rotationOverride);

    const sideKey = `${oppositeSide(chosenTarget.side)}:${Math.round(chosenTarget.x)}:${Math.round(chosenTarget.y)}`;
    const used = sideOccupancy.get(sideKey) ?? 0;
    sideOccupancy.set(sideKey, used + 1);

    if (used > 0) {
      const axisOffset = used * (port.bodyHeight + PIN_GRID_MM);
      if (chosenTarget.side === 'left' || chosenTarget.side === 'right') {
        base.y = snapToGrid(base.y + axisOffset);
      } else {
        base.x = snapToGrid(base.x + axisOffset);
      }
    }

    positions[port.id] = base;
  }

  // Anchor power/ground symbols directly to their component pins.
  for (const pwr of powerPorts) {
    const comp = findComponent(sheet, pwr.componentId);
    const compPos = comp ? positions[comp.id] : undefined;
    const pin = comp ? findPin(comp, pwr.pinNumber) : undefined;
    if (comp && compPos && pin) {
      const world = compPinWorld(compPos, comp, pin);
      positions[pwr.id] = placePowerPort(pwr, { x: world.x, y: world.y, side: pin.side });
      continue;
    }

    const mod = findModule(sheet, pwr.componentId);
    const modPos = mod ? positions[mod.id] : undefined;
    if (mod && modPos) {
      const world = modulePinWorld(modPos, mod, pwr.pinNumber);
      if (world) {
        positions[pwr.id] = placePowerPort(pwr, world);
        continue;
      }
    }

    positions[pwr.id] = { x: 0, y: 0, rotation: 0 };
  }

  for (const [id, pos] of Object.entries(positions)) {
    positions[id] = {
      ...pos,
      x: snapToGrid(pos.x),
      y: snapToGrid(pos.y),
      rotation: ((Math.round((pos.rotation ?? 0) / 90) * 90) % 360 + 360) % 360,
    };
  }

  return positions;
}
