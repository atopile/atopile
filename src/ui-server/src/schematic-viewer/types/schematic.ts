/**
 * Schematic-level data types for the hierarchical schematic viewer.
 *
 * Key concepts:
 * - SchematicSheet: what you see at one hierarchy level (modules + components + nets)
 * - SchematicModule: a sub-module that can be "entered" to reveal its contents
 * - SchematicComponent: a leaf atomic part with pins
 * - The root of the JSON is a SchematicSheet; each module contains its own sheet
 *
 * Backwards compatible: if the JSON has flat `components`/`nets` arrays (v1),
 * we treat it as a single root sheet with no sub-modules.
 */

import type { PinCategory, PinElectricalType, PinSide } from './symbol';

// ── Top-level build artifact ────────────────────────────────────

export interface SchematicData {
  version: string;

  // ── V2 hierarchical format ────────────────────────────────────
  /** Root sheet with modules, components, and nets */
  root?: SchematicSheet;

  // ── V1 flat format (backwards compat) ─────────────────────────
  /** Flat component list (v1 only — ignored if root is present) */
  components?: SchematicComponent[];
  /** Flat net list (v1 only — ignored if root is present) */
  nets?: SchematicNet[];
}

// ── Sheet: one level of hierarchy ───────────────────────────────

/**
 * A schematic sheet is what you see at one hierarchy level.
 * Contains modules (expandable blocks), components (leaf parts), and nets.
 */
export interface SchematicSheet {
  /** Sub-modules at this level (rendered as expandable blocks) */
  modules: SchematicModule[];
  /** Leaf components at this level (rendered with full pin detail) */
  components: SchematicComponent[];
  /** Nets connecting items at this level */
  nets: SchematicNet[];
}

// ── Module: an expandable sub-block ─────────────────────────────

/**
 * A module is a sub-block that can be drilled into.
 * When viewed from the parent level, it shows as a compact box with interface pins.
 * When entered, it reveals its internal sheet.
 */
export interface SchematicModule {
  kind: 'module';
  /** Stable hierarchical ID (e.g., "app.ldo_driver") */
  id: string;
  /** Instance name (e.g., "ldo_driver") */
  name: string;
  /** Type name (e.g., "TLV75901_driver") */
  typeName: string;
  /** Summary stats for the module badge */
  componentCount: number;
  /** Interface pins visible when viewing as a black box */
  interfacePins: SchematicInterfacePin[];
  /** Computed body dimensions (mm) */
  bodyWidth: number;
  bodyHeight: number;
  /** The module's internal contents — another sheet */
  sheet: SchematicSheet;
}

/**
 * An interface pin on a module block (the ports visible from outside).
 * These represent the module's external interfaces: power rails, I2C buses, etc.
 */
export interface SchematicInterfacePin {
  /** Unique ID within the module */
  id: string;
  /** Display label */
  name: string;
  /** Which side of the module box */
  side: PinSide;
  /** Functional category for coloring */
  category: PinCategory;
  /** Interface type (e.g., "ElectricPower", "I2C") */
  interfaceType: string;
  /** Offset from module center (mm) */
  x: number;
  y: number;
  /** Where the pin stub meets the body edge */
  bodyX: number;
  bodyY: number;
  /** Per-signal breakdown (e.g., ["scl", "sda"]). Present when >=2 signals. */
  signals?: string[];
}

// ── Component: a leaf atomic part ───────────────────────────────

export interface SchematicComponent {
  kind?: 'component';            // optional for v1 compat
  id: string;                    // stable address e.g. "ldo" or "mcu.i2c_pullup"
  name: string;                  // display name e.g. "TLV75901"
  designator: string;            // "U1", "R3"
  reference: string;             // "U", "R", "C"
  pins: SchematicPin[];
  bodyWidth: number;             // mm
  bodyHeight: number;            // mm
}

export interface SchematicPin {
  number: string;
  name: string;
  side: PinSide;
  electricalType: PinElectricalType;
  category: PinCategory;
  /** Offset from component center (KiCad coords, Y-up) */
  x: number;
  y: number;
  /** Where the pin meets the body edge */
  bodyX: number;
  bodyY: number;
}

// ── Nets ────────────────────────────────────────────────────────

export interface SchematicNet {
  id: string;                    // net name e.g. "power_3v3-hv"
  name: string;                  // display label
  pins: NetPin[];
  type: NetType;
}

export type NetType = 'power' | 'ground' | 'signal' | 'bus';

export interface NetPin {
  componentId: string;           // can reference a component OR module id
  pinNumber: string;             // pin number or interfacePin id
}

// ── User layout file ────────────────────────────────────────────

export interface SchematicLayout {
  version: string;
  /** Positions keyed by item id, scoped per sheet path */
  positions: Record<string, ComponentPosition>;
}

export interface ComponentPosition {
  x: number;
  y: number;
  /** Rotation in degrees CCW: 0 | 90 | 180 | 270 */
  rotation?: number;
  /** Mirror horizontally (flip around Y axis) — KiCad "X" key */
  mirrorX?: boolean;
  /** Mirror vertically (flip around X axis) — KiCad "Y" key */
  mirrorY?: boolean;
}

/**
 * Transform a local pin offset (relative to component center) according to
 * the component's rotation and mirror state.
 *
 * Order: mirror first, then rotate (matches KiCad behavior).
 */
export function transformPinOffset(
  px: number,
  py: number,
  rotation: number = 0,
  mirrorX: boolean = false,
  mirrorY: boolean = false,
): { x: number; y: number } {
  let x = px;
  let y = py;

  // Mirror first
  if (mirrorX) x = -x;
  if (mirrorY) y = -y;

  // Rotate CCW
  switch (rotation) {
    case 90:  return { x: -y, y: x };
    case 180: return { x: -x, y: -y };
    case 270: return { x: y, y: -x };
    default:  return { x, y };
  }
}

/**
 * Transform a pin's side direction to match the component's orientation.
 * Same mirror-first-then-rotate order as transformPinOffset.
 */
export function transformPinSide(
  side: string,
  rotation: number = 0,
  mirrorX: boolean = false,
  mirrorY: boolean = false,
): string {
  let s = side;

  // Mirror first
  if (mirrorX) {
    if (s === 'left') s = 'right';
    else if (s === 'right') s = 'left';
  }
  if (mirrorY) {
    if (s === 'top') s = 'bottom';
    else if (s === 'bottom') s = 'top';
  }

  // Rotate CCW in 90° steps
  const steps = ((rotation % 360) / 90) | 0;
  if (steps > 0) {
    const order = ['right', 'top', 'left', 'bottom'];
    const idx = order.indexOf(s);
    if (idx >= 0) return order[(idx + steps) % 4];
  }
  return s;
}

// ── Port: external interface entry (Altium-style sheet port) ────

/**
 * A port represents an external interface connection when viewing a module's
 * internal sheet. Derived at render time from the parent module's interfacePins.
 *
 * Visually rendered as an Altium-style arrow/pentagon shape at the sheet edge.
 * Each port has a single connection pin at the arrow tip that participates in nets.
 */
export interface SchematicPort {
  kind: 'port';
  /** Same as the parent module's interfacePin ID — also used as componentId in nets */
  id: string;
  /** Display label (e.g., "VIN", "GND", "SCL") */
  name: string;
  /** Which side of the sheet this port enters from */
  side: PinSide;
  /** Functional category for coloring */
  category: PinCategory;
  /** Interface type (e.g., "ElectricPower", "I2C") */
  interfaceType: string;
  /** Computed body dimensions */
  bodyWidth: number;
  bodyHeight: number;
  /** Position of the single connection pin relative to port center */
  pinX: number;
  pinY: number;
  /** Which direction the pin connects from (for net routing) */
  pinSide: PinSide;
  /** Per-signal breakdown for breakout ports (e.g., ["scl", "sda"]). */
  signals?: string[];
  /** Per-signal pin positions relative to port center (for breakout ports). */
  signalPins?: Record<string, { x: number; y: number }>;
}

// Port geometry constants — sized so two ports fit at 2.54mm pin pitch
export const PORT_W = 8;
export const PORT_H = 1.2;

// Breakout port geometry constants
export const BREAKOUT_PIN_SPACING = 2.54;
export const BREAKOUT_BOX_W = 12;
export const BREAKOUT_PADDING = 2;

/**
 * Derive SchematicPort objects from a module's interfacePins.
 * Called when navigating into a module to create sheet-edge port symbols.
 *
 * When an interface has >=2 signals, produces a breakout port (component-like box)
 * instead of the simple pentagon port.
 */
export function derivePortsFromModule(mod: SchematicModule): SchematicPort[] {
  return mod.interfacePins.map((ipin) => {
    const signals = ipin.signals;
    const isBreakout = signals && signals.length >= 2;

    if (isBreakout) {
      // ── Breakout port: component-like box with per-signal stubs ──
      const bodyW = BREAKOUT_BOX_W;
      const bodyH = signals.length * BREAKOUT_PIN_SPACING + BREAKOUT_PADDING;
      const halfW = bodyW / 2;

      // Pin side is the direction stubs extend (into the sheet)
      let pinSide: PinSide = 'right';
      switch (ipin.side) {
        case 'left':  pinSide = 'right'; break;
        case 'right': pinSide = 'left';  break;
        case 'top':   pinSide = 'bottom'; break;
        case 'bottom': pinSide = 'top';  break;
      }

      // Compute per-signal pin positions (relative to port center)
      const signalPins: Record<string, { x: number; y: number }> = {};
      const totalSpan = (signals.length - 1) * BREAKOUT_PIN_SPACING;
      const stubLen = 2.54;

      for (let i = 0; i < signals.length; i++) {
        const sig = signals[i];
        const sy = totalSpan / 2 - i * BREAKOUT_PIN_SPACING;

        let sx: number;
        if (ipin.side === 'left') {
          // Stubs extend right (into sheet)
          sx = halfW + stubLen;
        } else if (ipin.side === 'right') {
          // Stubs extend left
          sx = -(halfW + stubLen);
        } else if (ipin.side === 'top') {
          // Stubs extend down — use y for horizontal spread, sx for vertical
          sx = totalSpan / 2 - i * BREAKOUT_PIN_SPACING;
          signalPins[sig] = { x: sx, y: -(halfW + stubLen) };
          continue;
        } else {
          // bottom — stubs extend up
          sx = totalSpan / 2 - i * BREAKOUT_PIN_SPACING;
          signalPins[sig] = { x: sx, y: halfW + stubLen };
          continue;
        }

        signalPins[sig] = { x: sx, y: sy };
      }

      // Default pin position (center, for fallback "1" compat)
      let pinX = 0, pinY = 0;
      if (ipin.side === 'left') pinX = halfW + stubLen;
      else if (ipin.side === 'right') pinX = -(halfW + stubLen);
      else if (ipin.side === 'top') pinY = -(halfW + stubLen);
      else pinY = halfW + stubLen;

      return {
        kind: 'port' as const,
        id: ipin.id,
        name: ipin.name,
        side: ipin.side,
        category: ipin.category,
        interfaceType: ipin.interfaceType,
        bodyWidth: bodyW,
        bodyHeight: bodyH,
        pinX,
        pinY,
        pinSide,
        signals,
        signalPins,
      };
    }

    // ── Standard pentagon port (single signal) ──
    let pinX = 0, pinY = 0;
    let pinSide: PinSide = 'right';

    // Port arrow points INTO the sheet — pin is at the tip
    switch (ipin.side) {
      case 'left':
        pinX = PORT_W / 2;
        pinSide = 'right';
        break;
      case 'right':
        pinX = -PORT_W / 2;
        pinSide = 'left';
        break;
      case 'top':
        pinY = -PORT_H / 2;
        pinSide = 'bottom';
        break;
      case 'bottom':
        pinY = PORT_H / 2;
        pinSide = 'top';
        break;
    }

    return {
      kind: 'port' as const,
      id: ipin.id,
      name: ipin.name,
      side: ipin.side,
      category: ipin.category,
      interfaceType: ipin.interfaceType,
      bodyWidth: PORT_W,
      bodyHeight: PORT_H,
      pinX,
      pinY,
      pinSide,
    };
  });
}

// ── Power / Ground symbols ───────────────────────────────────────

/**
 * A power or ground symbol placed on the schematic, one per pin on a
 * power/ground net.  Behaves like a small component — draggable, with
 * a single connection pin that wires to its associated component pin.
 */
export interface SchematicPowerPort {
  kind: 'powerport';
  /** Unique id: `__pwr__{netId}__{componentId}__{pinNumber}` */
  id: string;
  /** Display label (net name, e.g. "VCC", "GND") */
  name: string;
  /** 'power' or 'ground' */
  type: 'power' | 'ground';
  /** Net this symbol belongs to */
  netId: string;
  /** The component pin this symbol connects to */
  componentId: string;
  pinNumber: string;
  /** Body dimensions (small, to fit at pin pitch) */
  bodyWidth: number;
  bodyHeight: number;
  /** Connection pin offset from symbol center */
  pinX: number;
  pinY: number;
  /** Direction the wire exits toward the component */
  pinSide: PinSide;
}

export const POWER_PORT_W = 2.0;
export const POWER_PORT_H = 1.2;

/**
 * Derive power/ground port symbols from a sheet's nets.
 * Each pin on a power or ground net gets its own movable symbol.
 */
export function derivePowerPorts(sheet: SchematicSheet): SchematicPowerPort[] {
  const ports: SchematicPowerPort[] = [];

  for (const net of sheet.nets) {
    if (net.type !== 'power' && net.type !== 'ground') continue;

    for (const pin of net.pins) {
      const id = `__pwr__${net.id}__${pin.componentId}__${pin.pinNumber}`;
      const isGround = net.type === 'ground';
      ports.push({
        kind: 'powerport',
        id,
        name: net.name,
        type: net.type,
        netId: net.id,
        componentId: pin.componentId,
        pinNumber: pin.pinNumber,
        bodyWidth: POWER_PORT_W,
        bodyHeight: POWER_PORT_H,
        pinX: 0,
        // Power: pin at bottom (symbol above, wire down to component)
        // Ground: pin at top (symbol below, wire up to component)
        pinY: isGround ? POWER_PORT_H / 2 : -POWER_PORT_H / 2,
        pinSide: isGround ? 'top' : 'bottom',
      });
    }
  }

  return ports;
}

// ── Helpers ─────────────────────────────────────────────────────

/** All renderable items at a sheet level */
export type SchematicItem = SchematicModule | SchematicComponent | SchematicPort | SchematicPowerPort;

/**
 * Normalize a SchematicData (v1 or v2) into a root sheet.
 * V1 flat format gets wrapped as a single sheet with no sub-modules.
 */
export function getRootSheet(data: SchematicData): SchematicSheet {
  if (data.root) {
    return data.root;
  }
  // V1 backwards compat: wrap flat arrays in a sheet
  return {
    modules: [],
    components: data.components ?? [],
    nets: data.nets ?? [],
  };
}

/**
 * Resolve a sheet at a given navigation path.
 * Returns null if the path is invalid (module not found).
 */
export function resolveSheet(
  root: SchematicSheet,
  path: string[],
): SchematicSheet | null {
  let current = root;
  for (const moduleId of path) {
    const mod = current.modules.find((m) => m.id === moduleId);
    if (!mod) return null;
    current = mod.sheet;
  }
  return current;
}

/**
 * Get the module names along a navigation path (for breadcrumbs).
 */
export function getPathLabels(
  root: SchematicSheet,
  path: string[],
): { id: string; name: string; typeName?: string }[] {
  const labels: { id: string; name: string; typeName?: string }[] = [];
  let current = root;
  for (const moduleId of path) {
    const mod = current.modules.find((m) => m.id === moduleId);
    if (!mod) break;
    labels.push({ id: mod.id, name: mod.name, typeName: mod.typeName });
    current = mod.sheet;
  }
  return labels;
}
