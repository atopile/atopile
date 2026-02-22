import type { SchematicInterfacePin, SchematicModule } from '../types/schematic';
import { getGridAlignmentOffset, type GridAlignmentOffset } from '../types/schematic';

export function sortInterfacePinsForSide(
  pins: SchematicInterfacePin[],
  side: SchematicInterfacePin['side'],
): SchematicInterfacePin[] {
  const sorted = [...pins];
  if (side === 'left' || side === 'right') {
    sorted.sort((a, b) => b.y - a.y || a.id.localeCompare(b.id));
  } else {
    sorted.sort((a, b) => a.x - b.x || a.id.localeCompare(b.id));
  }
  return sorted;
}

export function getOrderedModuleInterfacePins(
  module: Pick<SchematicModule, 'interfacePins'>,
  pinOrderOverride?: string[],
): SchematicInterfacePin[] {
  const byId = new Map(module.interfacePins.map((pin) => [pin.id, pin] as const));
  const out: SchematicInterfacePin[] = [];
  const used = new Set<string>();

  if (pinOrderOverride && pinOrderOverride.length > 0) {
    for (const id of pinOrderOverride) {
      const pin = byId.get(id);
      if (!pin) continue;
      out.push(pin);
      used.add(id);
    }
  }

  for (const side of ['left', 'right', 'top', 'bottom'] as const) {
    const sidePins = sortInterfacePinsForSide(
      module.interfacePins.filter((pin) => pin.side === side && !used.has(pin.id)),
      side,
    );
    out.push(...sidePins);
  }

  return out;
}

export function getModuleRenderSize(
  module: Pick<SchematicModule, 'interfacePins'> & {
    bodyWidth?: number;
    bodyHeight?: number;
  },
): { width: number; height: number } {
  const leftCount = module.interfacePins.filter((p) => p.side === 'left').length;
  const rightCount = module.interfacePins.filter((p) => p.side === 'right').length;
  const topCount = module.interfacePins.filter((p) => p.side === 'top').length;
  const bottomCount = module.interfacePins.filter((p) => p.side === 'bottom').length;

  const pinPitch = 2.54;
  const minVertical = 7.62;
  const minHorizontal = 10.16;

  const verticalCount = Math.max(leftCount, rightCount, 1);
  const horizontalCount = Math.max(topCount, bottomCount, 1);

  const pinDrivenHeight = (verticalCount - 1) * pinPitch + 2 * pinPitch;
  const pinDrivenWidth = (horizontalCount - 1) * pinPitch + 4 * pinPitch;

  return {
    width: Math.max(module.bodyWidth ?? 0, pinDrivenWidth, minHorizontal),
    height: Math.max(module.bodyHeight ?? 0, pinDrivenHeight, minVertical),
  };
}

export function getModuleBodyAnchor(
  pin: Pick<SchematicInterfacePin, 'side' | 'x' | 'y'>,
  moduleWidth: number,
  moduleHeight: number,
): { x: number; y: number } {
  switch (pin.side) {
    case 'left':
      return { x: -moduleWidth / 2, y: pin.y };
    case 'right':
      return { x: moduleWidth / 2, y: pin.y };
    case 'top':
      return { x: pin.x, y: moduleHeight / 2 };
    case 'bottom':
      return { x: pin.x, y: -moduleHeight / 2 };
  }
}

export function getModuleGridOffsetFromPins(
  pins: SchematicInterfacePin[],
): GridAlignmentOffset {
  const anchor = pins[0];
  return getGridAlignmentOffset(anchor?.x, anchor?.y);
}

export function modulePinOrderKey(path: string[], moduleId: string): string {
  const pathPart = path.length === 0 ? '__root__' : path.join('/');
  return `${pathPart}:__modulePins__:${moduleId}`;
}

export function getModulePinOrderForPath(
  orders: Record<string, string[]>,
  path: string[],
  moduleId: string,
): string[] | undefined {
  return orders[modulePinOrderKey(path, moduleId)];
}
