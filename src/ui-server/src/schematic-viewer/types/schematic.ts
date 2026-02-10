/**
 * Schematic-level data types for the hierarchical schematic viewer.
 *
 * Key concepts:
 * - SchematicSheet: what you see at one hierarchy level (modules + components + nets)
 * - SchematicModule: a sub-module that can be "entered" to reveal its contents
 * - SchematicComponent: a leaf atomic part with pins
 * - The root of the JSON is a SchematicSheet; each module contains its own sheet
 *
 * Runtime contract is v2-only: a hierarchical root sheet is required.
 */

import type { PinCategory, PinElectricalType, PinSide } from './symbol';

// ── Top-level build artifact ────────────────────────────────────

export interface SchematicData {
  version: string;
  /** Persisted item positions keyed by "path:itemId" from .ato_sch. */
  positions?: Record<string, ComponentPosition>;
  /** Optional per-port breakout signal ordering (scoped key: "path:portId"). */
  portSignalOrders?: Record<string, string[]>;
  /** Optional manually adjusted net routes (scoped key: "path:routeId"). */
  routeOverrides?: Record<string, [number, number, number][]>;
  /** Root sheet with modules, components, and nets */
  root: SchematicSheet;
}

/** Source location metadata for symbol-to-code navigation. */
export interface SchematicSourceRef {
  /** Atopile address, usually "file.ato::Module.path". */
  address?: string;
  /** Absolute filesystem path to the source file. */
  filePath?: string;
  /** Human-friendly instance path (e.g., "PinoutTest.pullup_sda"). */
  instancePath?: string;
  /** Optional 1-based line/column hints. */
  line?: number;
  column?: number;
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
  /** Optional source location for go-to-source actions. */
  source?: SchematicSourceRef;
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
  /** Single-signal GPIO/control bridge with explicit front/back anchors. */
  passThrough?: boolean;
  /** Optional source location for go-to-source actions. */
  source?: SchematicSourceRef;
}

// ── Component: a leaf atomic part ───────────────────────────────

export interface SchematicComponent {
  kind: 'component';
  id: string;                    // stable address e.g. "ldo" or "mcu.i2c_pullup"
  name: string;                  // display name e.g. "TLV75901"
  designator: string;            // "U1", "R3"
  reference: string;             // "U", "R", "C"
  symbolFamily?: SchematicSymbolFamily;
  symbolVariant?: string;
  packageCode?: string;
  polarity?: SchematicPolarity;
  pins: SchematicPin[];
  bodyWidth: number;             // mm
  bodyHeight: number;            // mm
  /** Optional source location for go-to-source actions. */
  source?: SchematicSourceRef;
}

export type SchematicSymbolFamily =
  | 'resistor'
  | 'capacitor'
  | 'capacitor_polarized'
  | 'inductor'
  | 'diode'
  | 'led'
  | 'connector'
  | 'testpoint';

export type SchematicPolarity = 'anode_cathode' | 'plus_minus' | 'pin1';

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

export type NetType = 'power' | 'ground' | 'signal' | 'bus' | 'electrical';

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

/** Canonical pin grid used for schematic handles and ortho routing anchors. */
export const PIN_GRID_MM = 2.54;

export function snapToPinGrid(v: number, grid = PIN_GRID_MM): number {
  return Math.round(v / grid) * grid;
}

/**
 * Snap to pin grid with deterministic tie-breaking.
 * On exact half-pitch ties, chooses the lower grid coordinate.
 */
export function snapToPinGridLowerTie(v: number, grid = PIN_GRID_MM): number {
  const scaled = v / grid;
  // Bias exact half-steps very slightly downward so both +0.5 and -0.5
  // cases resolve to the lower grid coordinate deterministically.
  const snappedSteps = Math.floor(scaled + 0.5 - 1e-6);
  return snappedSteps * grid;
}

/**
 * Normalize a component pin (and its body-edge anchor) onto the canonical
 * pin grid while preserving the pin→body vector.
 */
export function getNormalizedComponentPinGeometry(
  component: SchematicComponent,
  pin: Pick<SchematicPin, 'x' | 'y' | 'bodyX' | 'bodyY'> & Partial<Pick<SchematicPin, 'side'>>,
): { x: number; y: number; bodyX: number; bodyY: number } {
  const offset = getComponentGridAlignmentOffset(component);
  const x = snapToPinGridLowerTie(pin.x + offset.x) - offset.x;
  const y = snapToPinGridLowerTie(pin.y + offset.y) - offset.y;
  const dx = x - pin.x;
  const dy = y - pin.y;

  // Keep the body-edge anchor constrained to the symbol edge axis.
  // For left/right pins, preserve bodyX and only slide bodyY with row changes.
  // For top/bottom pins, preserve bodyY and only slide bodyX with column changes.
  let bodyX = pin.bodyX + dx;
  let bodyY = pin.bodyY + dy;
  if (pin.side === 'left' || pin.side === 'right') {
    bodyX = pin.bodyX;
    bodyY = pin.bodyY + dy;
  } else if (pin.side === 'top' || pin.side === 'bottom') {
    bodyX = pin.bodyX + dx;
    bodyY = pin.bodyY;
  }

  return {
    x,
    y,
    bodyX,
    bodyY,
  };
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

// ── Port: external interface entry ──────────────────────────────

/**
 * A port represents an external interface connection when viewing a module's
 * internal sheet. Derived at render time from the parent module's interfacePins.
 *
 * Ports are rendered with a unified rounded-box visual language.
 * Each port exposes one or more connection pins that participate in nets.
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
  /** Single-signal GPIO/control bridge with explicit front/back anchors. */
  passThrough?: boolean;
  /** Optional source location for go-to-source actions. */
  source?: SchematicSourceRef;
}

// Port geometry constants
export const PORT_W = 8;
export const PORT_H = 1.2;
export const PORT_STUB_LEN = 2.54;

// Breakout port geometry constants
export const BREAKOUT_PIN_SPACING = 2.54;
export const BREAKOUT_BOX_W = 12;
// Per-side top/bottom inset so stacked breakout ports keep a clean pin-pitch rhythm.
export const BREAKOUT_VERTICAL_PADDING = 0.6;

function reorderSignals(
  baseSignals: string[],
  override: string[] | undefined,
): string[] {
  if (!override || override.length !== baseSignals.length) return baseSignals;
  const baseSet = new Set(baseSignals);
  if (baseSet.size !== baseSignals.length) return baseSignals;
  const overrideSet = new Set(override);
  if (overrideSet.size !== override.length) return baseSignals;
  for (const sig of override) {
    if (!baseSet.has(sig)) return baseSignals;
  }
  return override;
}

/**
 * Derive SchematicPort objects from a module's interfacePins.
 * Called when navigating into a module to create sheet-edge port symbols.
 *
 * When an interface has >=2 signals, produces a breakout port with
 * per-signal pins plus one line-level interface pin ("1").
 *
 * Breakout translator contract:
 * - per-signal pins live on the sheet-facing side (where internal wiring lands),
 * - line-level pin "1" lives on the opposite side (bus-level access boundary).
 */
export function derivePortsFromModule(
  mod: SchematicModule,
  signalOrderOverrides?: Record<string, string[]>,
): SchematicPort[] {
  return mod.interfacePins.map((ipin) => {
    const signals = ipin.signals
      ? reorderSignals(ipin.signals, signalOrderOverrides?.[ipin.id])
      : undefined;
    const isBreakout = signals && signals.length >= 2;

    if (isBreakout) {
      // ── Breakout port: component-like box with per-signal stubs ──
      const bodyW = BREAKOUT_BOX_W;
      const totalSpan = (signals.length - 1) * BREAKOUT_PIN_SPACING;
      const linePinIndex = Math.floor((signals.length - 1) / 2);
      const linePinAxis = totalSpan / 2 - linePinIndex * BREAKOUT_PIN_SPACING;
      const bodyH = Math.max(
        PORT_H,
        totalSpan + BREAKOUT_VERTICAL_PADDING * 2,
      );
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
      const stubLen = PORT_STUB_LEN;
      const breakoutPinReach = snapToPinGrid(halfW + stubLen);

      for (let i = 0; i < signals.length; i++) {
        const sig = signals[i];
        const sy = totalSpan / 2 - i * BREAKOUT_PIN_SPACING;

        let sx: number;
        if (ipin.side === 'left') {
          // Stubs extend right (into sheet)
          sx = breakoutPinReach;
        } else if (ipin.side === 'right') {
          // Stubs extend left
          sx = -breakoutPinReach;
        } else if (ipin.side === 'top') {
          // Stubs extend down — use y for horizontal spread, sx for vertical
          sx = totalSpan / 2 - i * BREAKOUT_PIN_SPACING;
          signalPins[sig] = { x: sx, y: -breakoutPinReach };
          continue;
        } else {
          // bottom — stubs extend up
          sx = totalSpan / 2 - i * BREAKOUT_PIN_SPACING;
          signalPins[sig] = { x: sx, y: breakoutPinReach };
          continue;
        }

        signalPins[sig] = { x: sx, y: sy };
      }

      // Primary line-level pin lives on the opposite side of the
      // per-signal breakout pins (translator boundary).
      let pinX = 0, pinY = 0;
      if (ipin.side === 'left') {
        pinX = -breakoutPinReach;
        pinY = linePinAxis;
      } else if (ipin.side === 'right') {
        pinX = breakoutPinReach;
        pinY = linePinAxis;
      } else if (ipin.side === 'top') {
        pinY = breakoutPinReach;
        pinX = linePinAxis;
      } else {
        pinY = -breakoutPinReach;
        pinX = linePinAxis;
      }

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
        source: ipin.source,
      };
    }

    // ── Single-signal port (match breakout framing + stub model) ──
    const singleBodyW = BREAKOUT_BOX_W;
    // Keep single ports compact so stacked ports remain on pin-pitch rhythm.
    const singleBodyH = PORT_H;
    const singlePinReach = snapToPinGrid(singleBodyW / 2 + PORT_STUB_LEN);

    let pinX = 0, pinY = 0;
    let pinSide: PinSide = 'right';

    // Pin sits at body edge + stub length (consistent with breakout ports).
    switch (ipin.side) {
      case 'left':
        pinX = singlePinReach;
        pinSide = 'right';
        break;
      case 'right':
        pinX = -singlePinReach;
        pinSide = 'left';
        break;
      case 'top':
        pinY = -singlePinReach;
        pinSide = 'bottom';
        break;
      case 'bottom':
        pinY = singlePinReach;
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
      bodyWidth: singleBodyW,
      bodyHeight: singleBodyH,
      pinX,
      pinY,
      pinSide,
      passThrough: !!ipin.passThrough,
      source: ipin.source,
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
const DEPRECATED_POWER_PORT_NAMES = new Set(['vcc', 'gnd']);

function isDeprecatedPowerPortName(name: string): boolean {
  return DEPRECATED_POWER_PORT_NAMES.has(name.trim().toLowerCase());
}

/**
 * Derive power/ground port symbols from a sheet's nets.
 * Each pin on a power or ground net gets its own movable symbol.
 */
export function derivePowerPorts(sheet: SchematicSheet): SchematicPowerPort[] {
  const ports: SchematicPowerPort[] = [];
  const moduleIds = new Set(sheet.modules.map((mod) => mod.id));

  for (const net of sheet.nets) {
    if (net.type !== 'power' && net.type !== 'ground') continue;
    // Temporary compatibility shim:
    // hide legacy VCC/GND power symbols now that HV/LV is the canonical naming.
    // Safe when legacy nets are fully removed because this simply won't match.
    if (isDeprecatedPowerPortName(net.name) || isDeprecatedPowerPortName(net.id)) continue;

    // Block-level sheets should route module power links like regular nets.
    // If a power/ground net touches module pins, skip symbolizing this net.
    const hasBlockLevelEndpoint = net.pins.some((pin) => {
      if (moduleIds.has(pin.componentId)) return true;
      return false;
    });
    if (hasBlockLevelEndpoint) continue;

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

export interface GridAlignmentOffset {
  x: number;
  y: number;
}

/**
 * Translate an item so a chosen anchor lands exactly on the pin grid.
 * Apply this offset to the whole symbol, not individual pins.
 */
export function getGridAlignmentOffset(
  anchorX: number | null | undefined,
  anchorY: number | null | undefined,
): GridAlignmentOffset {
  if (anchorX == null || anchorY == null) return { x: 0, y: 0 };
  return {
    x: snapToPinGrid(anchorX) - anchorX,
    y: snapToPinGrid(anchorY) - anchorY,
  };
}

export function getComponentGridAlignmentOffset(
  component: SchematicComponent,
): GridAlignmentOffset {
  const anchor = component.pins[0];
  return getGridAlignmentOffset(anchor?.x, anchor?.y);
}

export function getModuleGridAlignmentOffset(
  module: SchematicModule,
): GridAlignmentOffset {
  const anchor = module.interfacePins[0];
  return getGridAlignmentOffset(anchor?.x, anchor?.y);
}

export function getPortGridAlignmentOffset(
  port: SchematicPort,
): GridAlignmentOffset {
  if (port.signals && port.signalPins) {
    for (const signalName of port.signals) {
      const sp = port.signalPins[signalName];
      if (sp) {
        return getGridAlignmentOffset(sp.x, sp.y);
      }
    }
  }
  return getGridAlignmentOffset(port.pinX, port.pinY);
}

export function getPowerPortGridAlignmentOffset(
  powerPort: SchematicPowerPort,
): GridAlignmentOffset {
  return getGridAlignmentOffset(powerPort.pinX, powerPort.pinY);
}

/**
 * Canonical pin-number contract for ports.
 * - Single-signal ports expose only "1".
 * - Breakout ports expose per-signal pins and line-level pin "1".
 */
export function getPortPinNumbers(port: SchematicPort): string[] {
  if (port.signals && port.signals.length > 0) {
    return [...port.signals, '1'];
  }
  if (port.passThrough) {
    return ['1', '2'];
  }
  return ['1'];
}

/** All renderable items at a sheet level */
export type SchematicItem = SchematicModule | SchematicComponent | SchematicPort | SchematicPowerPort;

/**
 * Return the root sheet (v2-only contract).
 */
export function getRootSheet(data: SchematicData): SchematicSheet {
  if (!data.root) {
    throw new Error('Invalid schematic payload: missing root sheet');
  }
  return data.root;
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
