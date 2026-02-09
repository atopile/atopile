/**
 * Zustand store for multi-component schematic state with hierarchy navigation.
 *
 * Architecture:
 * - `schematic` holds the raw JSON data (SchematicData)
 * - `currentPath` tracks which module we're "inside" (breadcrumb trail)
 * - `currentSheet` is derived: resolves the path to get the active sheet
 * - Positions are scoped per sheet (keyed by path string)
 * - Live drag uses a shared mutable ref (zero re-renders during drag)
 * - Multi-select via `selectedComponentIds` array + group drag support
 */

import { create } from 'zustand';
import { subscribeWithSelector } from 'zustand/middleware';
import type {
  SchematicData,
  SchematicNet,
  SchematicComponent,
  SchematicModule,
  SchematicSheet,
  SchematicPort,
  ComponentPosition,
} from '../types/schematic';
import { getRootSheet, resolveSheet, derivePortsFromModule, derivePowerPorts } from '../types/schematic';
import type { SchematicPowerPort } from '../types/schematic';
import { autoLayoutSheet, mergePositions, snapToGrid } from '../lib/schematicLayout';
import { postToExtension } from '../lib/vscodeApi';

// ── Alignment types ─────────────────────────────────────────────

export type AlignMode =
  | 'left'
  | 'right'
  | 'top'
  | 'bottom'
  | 'center-h'
  | 'center-v'
  | 'distribute-h'
  | 'distribute-v';

// ── State shape ────────────────────────────────────────────────

interface SchematicState {
  // Data
  schematic: SchematicData | null;
  /** Positions keyed by "pathKey:itemId" for per-sheet scoping */
  positions: Record<string, ComponentPosition>;
  /** Per-port signal order overrides keyed by "pathKey:portId". */
  portSignalOrders: Record<string, string[]>;
  isLoading: boolean;
  loadError: string | null;

  // Hierarchy navigation
  /** Current navigation path — array of module IDs from root */
  currentPath: string[];

  // Interaction — multi-select
  /** Selected item IDs (components, modules, ports). Empty = nothing selected. */
  selectedComponentIds: string[];
  /** Backwards-compat: first selected item (or null) */
  selectedComponentId: string | null;
  selectedNetId: string | null;
  hoveredComponentId: string | null;
  hoveredNetId: string | null;
  dragComponentId: string | null;

  // Context menu
  contextMenu: {
    x: number;
    y: number;
    kind: 'align' | 'port';
    portId?: string;
  } | null;

  // Port edit mode (reorder + snap)
  portEditMode: boolean;
  /** Only this port is editable while port edit mode is active. */
  portEditTargetId: string | null;
  portEditSnapshot: Record<string, { x: number; y: number }[]> | null;

  // Actions
  loadSchematic: (url: string) => Promise<void>;
  loadSchematicData: (data: SchematicData) => void;
  /** Update schematic data without resetting navigation or positions. */
  updateSchematicData: (data: SchematicData) => void;
  commitPosition: (componentId: string, pos: ComponentPosition) => void;
  startDrag: (componentId: string) => void;
  endDrag: () => void;
  /** Single-select (replaces selection). Pass null to deselect all. */
  selectComponent: (id: string | null) => void;
  /** Toggle an item in/out of the current multi-selection. */
  toggleComponentSelection: (id: string) => void;
  /** Replace selection with a set of IDs (window select). */
  selectComponents: (ids: string[]) => void;
  /** Add item to selection without removing others. */
  addToSelection: (id: string) => void;
  selectNet: (id: string | null) => void;
  hoverComponent: (id: string | null) => void;
  hoverNet: (id: string | null) => void;
  resetLayout: () => void;

  // Transform (KiCad-style hotkeys) — operate on ALL selected items
  rotateSelected: () => void;
  mirrorSelectedX: () => void;
  mirrorSelectedY: () => void;
  /** Move all selected items by (dx, dy) in mm, snapped to grid. */
  nudgeSelected: (dx: number, dy: number) => void;
  /** Align/distribute all selected items. */
  alignSelected: (mode: AlignMode) => void;

  // Context menu
  openContextMenu: (x: number, y: number, kind?: 'align' | 'port', portId?: string) => void;
  closeContextMenu: () => void;

  // Port edit mode
  setPortEditMode: (enabled: boolean, portId?: string | null) => void;
  reorderPortSignals: (portId: string, orderedSignals: string[]) => void;

  // Undo / Redo
  undo: () => void;
  redo: () => void;

  // Navigation
  navigateInto: (moduleId: string) => void;
  navigateUp: () => void;
  navigateToPath: (path: string[]) => void;
}

// ── Live drag position (imperative, no React) ──────────────────

export const liveDrag = {
  componentId: null as string | null,
  x: 0,
  y: 0,
  version: 0,
  /** Group drag: offsets from the primary drag item for each other selected item. */
  groupOffsets: {} as Record<string, { x: number; y: number }>,
};

// ── Path key for position scoping ──────────────────────────────

function pathKey(path: string[]): string {
  return path.length === 0 ? '__root__' : path.join('/');
}

function scopedId(path: string[], itemId: string): string {
  return `${pathKey(path)}:${itemId}`;
}

function clonePortSignalOrders(
  orders: Record<string, string[]>,
): Record<string, string[]> {
  const out: Record<string, string[]> = {};
  for (const [key, arr] of Object.entries(orders)) out[key] = [...arr];
  return out;
}

function normalizePositionsMap(
  positions: Record<string, ComponentPosition>,
): Record<string, ComponentPosition> {
  const out: Record<string, ComponentPosition> = {};
  for (const [key, pos] of Object.entries(positions)) {
    out[key] = {
      ...pos,
      x: snapToGrid(pos.x),
      y: snapToGrid(pos.y),
    };
  }
  return out;
}

function getSignalOrderOverridesForPath(
  orders: Record<string, string[]>,
  path: string[],
): Record<string, string[]> {
  const prefix = pathKey(path) + ':';
  const out: Record<string, string[]> = {};
  for (const [key, value] of Object.entries(orders)) {
    if (!key.startsWith(prefix)) continue;
    out[key.slice(prefix.length)] = value;
  }
  return out;
}

function normalizeSignalOrder(
  baseSignals: string[],
  orderedSignals: string[],
): string[] | null {
  if (baseSignals.length !== orderedSignals.length) return null;
  const baseSet = new Set(baseSignals);
  const orderedSet = new Set(orderedSignals);
  if (baseSet.size !== baseSignals.length || orderedSet.size !== orderedSignals.length) return null;
  for (const sig of orderedSignals) {
    if (!baseSet.has(sig)) return null;
  }
  return orderedSignals;
}

function getCurrentPortsForState(state: {
  schematic: SchematicData | null;
  currentPath: string[];
  portSignalOrders: Record<string, string[]>;
}): SchematicPort[] {
  if (!state.schematic || state.currentPath.length === 0) return [];
  const root = getRootSheet(state.schematic);
  const parentPath = state.currentPath.slice(0, -1);
  const parentSheet = resolveSheet(root, parentPath);
  if (!parentSheet) return [];
  const moduleId = state.currentPath[state.currentPath.length - 1];
  const mod = parentSheet.modules.find((m) => m.id === moduleId);
  if (!mod) return [];
  return derivePortsFromModule(
    mod,
    getSignalOrderOverridesForPath(state.portSignalOrders, state.currentPath),
  );
}

function comparePortAxis(
  side: string,
  a: number,
  b: number,
): number {
  if (side === 'left' || side === 'right') return b - a; // top -> bottom
  return a - b; // left -> right
}

function buildPortEditSnapshot(
  ports: SchematicPort[],
  path: string[],
  positions: Record<string, ComponentPosition>,
): Record<string, { x: number; y: number }[]> {
  const grouped = new Map<string, Array<{ id: string; x: number; y: number; axis: number }>>();

  for (const port of ports) {
    const key = scopedId(path, port.id);
    const pos = positions[key] || { x: 0, y: 0 };
    const axis = (port.side === 'left' || port.side === 'right') ? pos.y : pos.x;
    const list = grouped.get(port.side) || [];
    list.push({ id: port.id, x: pos.x, y: pos.y, axis });
    grouped.set(port.side, list);
  }

  const snapshot: Record<string, { x: number; y: number }[]> = {};
  for (const [side, list] of grouped) {
    list.sort((a, b) => comparePortAxis(side, a.axis, b.axis));
    snapshot[side] = list.map((item) => ({
      x: snapToGrid(item.x),
      y: snapToGrid(item.y),
    }));
  }
  return snapshot;
}

function reorderPortsToSnapshot(
  draggedPortId: string,
  ports: SchematicPort[],
  path: string[],
  positions: Record<string, ComponentPosition>,
  snapshot: Record<string, { x: number; y: number }[]>,
): Record<string, ComponentPosition> | null {
  const dragged = ports.find((p) => p.id === draggedPortId);
  if (!dragged) return null;
  const side = dragged.side;
  const sidePorts = ports.filter((p) => p.side === side);
  if (sidePorts.length < 2) return null;

  const slots = snapshot[side];
  if (!slots || slots.length !== sidePorts.length) return null;

  const orderedPortIds = [...sidePorts]
    .map((port) => {
      const pos = positions[scopedId(path, port.id)] || { x: 0, y: 0 };
      const axis = (side === 'left' || side === 'right') ? pos.y : pos.x;
      return { id: port.id, axis };
    })
    .sort((a, b) => comparePortAxis(side, a.axis, b.axis))
    .map((item) => item.id);

  const out = { ...positions };
  let changed = false;
  for (let i = 0; i < orderedPortIds.length; i++) {
    const id = orderedPortIds[i];
    const slot = slots[i];
    const key = scopedId(path, id);
    const cur = out[key] || { x: 0, y: 0 };
    const nx = snapToGrid(slot.x);
    const ny = snapToGrid(slot.y);
    if (cur.x !== nx || cur.y !== ny) changed = true;
    out[key] = {
      ...cur,
      x: nx,
      y: ny,
    };
  }
  return changed ? out : null;
}

// ── .ato_sch file path (set from config) ────────────────────────

/** The .ato_sch file path — unified schematic data + positions */
let _atoSchPath: string | null = null;

export function setAtoSchPath(path: string | null) {
  _atoSchPath = path;
}

export function getAtoSchPath(): string | null {
  return _atoSchPath;
}

// ── Debounced save ─────────────────────────────────────────────

let saveTimer: ReturnType<typeof setTimeout> | null = null;

function debouncedSave(
  positions: Record<string, ComponentPosition>,
  portSignalOrders: Record<string, string[]> = {},
) {
  if (saveTimer) clearTimeout(saveTimer);
  saveTimer = setTimeout(() => {
    try {
      // Save positions via VSCode extension (merges into .ato_sch file)
      postToExtension({
        type: 'save-layout',
        atoSchPath: _atoSchPath,
        positions,
        portSignalOrders,
      });
    } catch {
      /* ignore */
    }
  }, 500);
}

// ── Layout a sheet and scope positions to a path ────────────────

function layoutSheet(
  sheet: SchematicSheet,
  path: string[],
  savedPositions: Record<string, ComponentPosition> | null,
  ports: SchematicPort[] = [],
): {
  positions: Record<string, ComponentPosition>;
  suggestedPortSignalOrders: Record<string, string[]>;
} {
  const powerPorts = derivePowerPorts(sheet);
  const localSuggestedOrders: Record<string, string[]> = {};
  const autoPos = autoLayoutSheet(
    sheet,
    ports,
    powerPorts,
    localSuggestedOrders,
  );
  const savedForPath: Record<string, ComponentPosition> = {};

  // Extract saved positions for this path
  if (savedPositions) {
    const prefix = pathKey(path) + ':';
    for (const [key, pos] of Object.entries(savedPositions)) {
      if (key.startsWith(prefix)) {
        const itemId = key.slice(prefix.length);
        savedForPath[itemId] = pos;
      }
    }
  }

  const merged = mergePositions(autoPos, savedForPath);

  // Scope the positions with path prefix
  const scoped: Record<string, ComponentPosition> = {};
  for (const [id, pos] of Object.entries(merged)) {
    scoped[scopedId(path, id)] = pos;
  }
  const scopedSuggestedOrders: Record<string, string[]> = {};
  for (const [portId, order] of Object.entries(localSuggestedOrders)) {
    scopedSuggestedOrders[scopedId(path, portId)] = [...order];
  }

  return {
    positions: scoped,
    suggestedPortSignalOrders: scopedSuggestedOrders,
  };
}

function mergeAutoPortSignalOrders(
  existing: Record<string, string[]>,
  suggested: Record<string, string[]>,
): Record<string, string[]> {
  if (Object.keys(suggested).length === 0) return existing;
  const next = clonePortSignalOrders(existing);
  for (const [key, order] of Object.entries(suggested)) {
    if (next[key]) continue;
    if (!Array.isArray(order) || order.length < 2) continue;
    next[key] = [...order];
  }
  return next;
}

// ── Undo / Redo stacks (module-level, not in store state) ───────

const MAX_UNDO = 100;
interface HistorySnapshot {
  positions: Record<string, ComponentPosition>;
  portSignalOrders: Record<string, string[]>;
}

const undoStack: HistorySnapshot[] = [];
const redoStack: HistorySnapshot[] = [];

function pushUndo(
  positions: Record<string, ComponentPosition>,
  portSignalOrders: Record<string, string[]>,
) {
  undoStack.push({
    positions: { ...positions },
    portSignalOrders: clonePortSignalOrders(portSignalOrders),
  });
  if (undoStack.length > MAX_UNDO) undoStack.shift();
  // Any new action clears the redo stack
  redoStack.length = 0;
}

// ── Helper: derive selectedComponentId from array ───────────────

function deriveSelectedId(ids: string[]): string | null {
  return ids.length > 0 ? ids[0] : null;
}

// ── Store ──────────────────────────────────────────────────────

export const useSchematicStore = create<SchematicState>()(
  subscribeWithSelector((set, get) => ({
    schematic: null,
    positions: {},
    portSignalOrders: {},
    isLoading: false,
    loadError: null,
    currentPath: [],
    selectedComponentIds: [],
    selectedComponentId: null,
    selectedNetId: null,
    hoveredComponentId: null,
    hoveredNetId: null,
    dragComponentId: null,
    contextMenu: null,
    portEditMode: false,
    portEditTargetId: null,
    portEditSnapshot: null,

    loadSchematic: async (url: string) => {
      set({ isLoading: true, loadError: null });
      try {
        const resp = await fetch(url);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();
        const schematicData: SchematicData = data;
        const rootSheet = getRootSheet(schematicData);
        const embeddedPositions = data.positions ?? null;
        const savedSignalOrders = data.portSignalOrders ?? {};
        const { positions: rootPositions, suggestedPortSignalOrders } =
          layoutSheet(rootSheet, [], embeddedPositions);
        const mergedSignalOrders = mergeAutoPortSignalOrders(
          savedSignalOrders,
          suggestedPortSignalOrders,
        );
        const positions = normalizePositionsMap({
          ...(embeddedPositions ?? {}),
          ...rootPositions,
        });
        set({
          schematic: schematicData,
          positions,
          portSignalOrders: mergedSignalOrders,
          currentPath: [],
          isLoading: false,
          selectedComponentIds: [],
          selectedComponentId: null,
          selectedNetId: null,
          portEditMode: false,
          portEditTargetId: null,
          portEditSnapshot: null,
          contextMenu: null,
        });
      } catch (e) {
        set({
          isLoading: false,
          loadError: e instanceof Error ? e.message : 'Unknown error',
        });
      }
    },

    loadSchematicData: (data: SchematicData) => {
      const rootSheet = getRootSheet(data);
      const embeddedPositions = data.positions ?? null;
      const savedSignalOrders = data.portSignalOrders ?? {};
      const { positions: rootPositions, suggestedPortSignalOrders } =
        layoutSheet(rootSheet, [], embeddedPositions);
      const mergedSignalOrders = mergeAutoPortSignalOrders(
        savedSignalOrders,
        suggestedPortSignalOrders,
      );
      const positions = normalizePositionsMap({
        ...(embeddedPositions ?? {}),
        ...rootPositions,
      });
      set({
        schematic: data,
        positions,
        portSignalOrders: mergedSignalOrders,
        currentPath: [],
        isLoading: false,
        loadError: null,
        selectedComponentIds: [],
        selectedComponentId: null,
        selectedNetId: null,
        portEditMode: false,
        portEditTargetId: null,
        portEditSnapshot: null,
        contextMenu: null,
      });
    },

    updateSchematicData: (data: SchematicData) => {
      // Preserve navigation path and existing positions.
      // Only re-layout sheets that don't already have positions.
      const { currentPath, positions: existingPositions, portSignalOrders } = get();
      const rootSheet = getRootSheet(data);
      const embeddedPositions = data.positions ?? null;
      const incomingSignalOrders = data.portSignalOrders ?? portSignalOrders;

      // Re-layout the root sheet, merging with existing positions
      const { positions: rootPositions, suggestedPortSignalOrders } =
        layoutSheet(rootSheet, [], embeddedPositions);
      const mergedSignalOrders = mergeAutoPortSignalOrders(
        incomingSignalOrders,
        suggestedPortSignalOrders,
      );
      const merged = normalizePositionsMap({
        ...(embeddedPositions ?? {}),
        ...rootPositions,
        ...existingPositions,
      });

      // Validate that the current navigation path is still valid
      let validPath = currentPath;
      if (currentPath.length > 0 && resolveSheet(rootSheet, currentPath) === null) {
        validPath = [];
      }

      set({
        schematic: data,
        positions: merged,
        portSignalOrders: mergedSignalOrders,
        currentPath: validPath,
        isLoading: false,
        loadError: null,
        portEditMode: false,
        portEditTargetId: null,
        portEditSnapshot: null,
        contextMenu: null,
      });
    },

    commitPosition: (componentId, pos) => {
      const path = get().currentPath;
      const key = scopedId(path, componentId);
      const existing = get().positions[key];
      const snapped: ComponentPosition = {
        x: snapToGrid(pos.x),
        y: snapToGrid(pos.y),
        rotation: pos.rotation ?? existing?.rotation,
        mirrorX: pos.mirrorX ?? existing?.mirrorX,
        mirrorY: pos.mirrorY ?? existing?.mirrorY,
      };
      set((s) => {
        const newPositions = { ...s.positions, [key]: snapped };
        debouncedSave(newPositions, s.portSignalOrders);
        return { positions: newPositions };
      });
    },

    startDrag: (componentId) => set({ dragComponentId: componentId }),

    endDrag: () => {
      const commitPos = get().commitPosition;
      if (liveDrag.componentId) {
        pushUndo(get().positions, get().portSignalOrders);
        const id = liveDrag.componentId;
        // Commit primary drag item
        commitPos(id, { x: liveDrag.x, y: liveDrag.y });
        // Commit group drag items
        for (const [groupId, offset] of Object.entries(liveDrag.groupOffsets)) {
          commitPos(groupId, {
            x: liveDrag.x + offset.x,
            y: liveDrag.y + offset.y,
          });
        }
        const st = get();
        if (
          st.portEditMode &&
          st.portEditSnapshot &&
          (!st.portEditTargetId || st.portEditTargetId === id)
        ) {
          const ports = getCurrentPortsForState(st);
          if (ports.some((p) => p.id === id)) {
            const reordered = reorderPortsToSnapshot(
              id,
              ports,
              st.currentPath,
              st.positions,
              st.portEditSnapshot,
            );
            if (reordered) {
              set({ positions: reordered });
              debouncedSave(reordered, st.portSignalOrders);
            }
          }
        }
        liveDrag.componentId = null;
        liveDrag.groupOffsets = {};
        liveDrag.version++;
      }
      set({ dragComponentId: null });
    },

    // ── Selection ──────────────────────────────────────────────

    selectComponent: (id) => {
      if (id === null) {
        set({ selectedComponentIds: [], selectedComponentId: null, selectedNetId: null });
      } else {
        set((s) => {
          // If already the sole selection, toggle off
          if (s.selectedComponentIds.length === 1 && s.selectedComponentIds[0] === id) {
            return { selectedComponentIds: [], selectedComponentId: null, selectedNetId: null };
          }
          return {
            selectedComponentIds: [id],
            selectedComponentId: id,
            selectedNetId: null,
          };
        });
      }
    },

    toggleComponentSelection: (id) =>
      set((s) => {
        const ids = s.selectedComponentIds.includes(id)
          ? s.selectedComponentIds.filter((x) => x !== id)
          : [...s.selectedComponentIds, id];
        return {
          selectedComponentIds: ids,
          selectedComponentId: deriveSelectedId(ids),
          selectedNetId: null,
        };
      }),

    selectComponents: (ids) =>
      set({
        selectedComponentIds: ids,
        selectedComponentId: deriveSelectedId(ids),
        selectedNetId: null,
      }),

    addToSelection: (id) =>
      set((s) => {
        if (s.selectedComponentIds.includes(id)) return s;
        const ids = [...s.selectedComponentIds, id];
        return {
          selectedComponentIds: ids,
          selectedComponentId: deriveSelectedId(ids),
          selectedNetId: null,
        };
      }),

    selectNet: (id) =>
      set((s) => ({
        selectedNetId: s.selectedNetId === id ? null : id,
        selectedComponentIds: [],
        selectedComponentId: null,
      })),

    hoverComponent: (id) => set({ hoveredComponentId: id }),
    hoverNet: (id) => set({ hoveredNetId: id }),

    resetLayout: () => {
      const { schematic, currentPath } = get();
      if (!schematic) return;
      pushUndo(get().positions, get().portSignalOrders);
      const rootSheet = getRootSheet(schematic);
      const sheet = resolveSheet(rootSheet, currentPath);
      if (!sheet) return;
      let ports: SchematicPort[] = [];
      if (currentPath.length > 0) {
        const parentPath = currentPath.slice(0, -1);
        const parentSheet = resolveSheet(rootSheet, parentPath);
        const modId = currentPath[currentPath.length - 1];
        const mod = parentSheet?.modules.find((m) => m.id === modId);
        if (mod) {
          ports = derivePortsFromModule(
            mod,
            getSignalOrderOverridesForPath(get().portSignalOrders, currentPath),
          );
        }
      }
      const { positions, suggestedPortSignalOrders } = layoutSheet(
        sheet,
        currentPath,
        null,
        ports,
      );
      set((s) => {
        const prefix = pathKey(currentPath) + ':';
        const kept: Record<string, ComponentPosition> = {};
        for (const [k, v] of Object.entries(s.positions)) {
          if (!k.startsWith(prefix)) kept[k] = v;
        }
        const merged = { ...kept, ...positions };
        const mergedOrders = mergeAutoPortSignalOrders(
          s.portSignalOrders,
          suggestedPortSignalOrders,
        );
        debouncedSave(merged, mergedOrders);
        return {
          positions: merged,
          portSignalOrders: mergedOrders,
        };
      });
    },

    // ── Transform (operate on ALL selected items) ───────────────

    rotateSelected: () => {
      const { selectedComponentIds, currentPath, positions } = get();
      if (selectedComponentIds.length === 0) return;
      pushUndo(positions, get().portSignalOrders);
      set((s) => {
        const newPositions = { ...s.positions };
        for (const id of selectedComponentIds) {
          const key = scopedId(currentPath, id);
          const pos = newPositions[key] || { x: 0, y: 0 };
          newPositions[key] = { ...pos, rotation: ((pos.rotation || 0) + 90) % 360 };
        }
        debouncedSave(newPositions, s.portSignalOrders);
        return { positions: newPositions };
      });
    },

    mirrorSelectedX: () => {
      const { selectedComponentIds, currentPath, positions } = get();
      if (selectedComponentIds.length === 0) return;
      pushUndo(positions, get().portSignalOrders);
      set((s) => {
        const newPositions = { ...s.positions };
        for (const id of selectedComponentIds) {
          const key = scopedId(currentPath, id);
          const pos = newPositions[key] || { x: 0, y: 0 };
          newPositions[key] = { ...pos, mirrorX: !pos.mirrorX };
        }
        debouncedSave(newPositions, s.portSignalOrders);
        return { positions: newPositions };
      });
    },

    mirrorSelectedY: () => {
      const { selectedComponentIds, currentPath, positions } = get();
      if (selectedComponentIds.length === 0) return;
      pushUndo(positions, get().portSignalOrders);
      set((s) => {
        const newPositions = { ...s.positions };
        for (const id of selectedComponentIds) {
          const key = scopedId(currentPath, id);
          const pos = newPositions[key] || { x: 0, y: 0 };
          newPositions[key] = { ...pos, mirrorY: !pos.mirrorY };
        }
        debouncedSave(newPositions, s.portSignalOrders);
        return { positions: newPositions };
      });
    },

    nudgeSelected: (dx, dy) => {
      const { selectedComponentIds, currentPath, positions } = get();
      if (selectedComponentIds.length === 0) return;
      pushUndo(positions, get().portSignalOrders);
      set((s) => {
        const newPositions = { ...s.positions };
        for (const id of selectedComponentIds) {
          const key = scopedId(currentPath, id);
          const pos = newPositions[key] || { x: 0, y: 0 };
          newPositions[key] = {
            ...pos,
            x: snapToGrid(pos.x + dx),
            y: snapToGrid(pos.y + dy),
          };
        }
        debouncedSave(newPositions, s.portSignalOrders);
        return { positions: newPositions };
      });
    },

    alignSelected: (mode) => {
      const { selectedComponentIds, currentPath, positions } = get();
      if (selectedComponentIds.length < 2) return;
      pushUndo(positions, get().portSignalOrders);
      set((s) => {
        const newPositions = { ...s.positions };
        const items = selectedComponentIds.map((id) => {
          const key = scopedId(currentPath, id);
          return { id, key, pos: newPositions[key] || { x: 0, y: 0 } };
        });

        switch (mode) {
          case 'left': {
            const minX = Math.min(...items.map((i) => i.pos.x));
            for (const item of items) {
              newPositions[item.key] = { ...item.pos, x: minX };
            }
            break;
          }
          case 'right': {
            const maxX = Math.max(...items.map((i) => i.pos.x));
            for (const item of items) {
              newPositions[item.key] = { ...item.pos, x: maxX };
            }
            break;
          }
          case 'top': {
            const maxY = Math.max(...items.map((i) => i.pos.y));
            for (const item of items) {
              newPositions[item.key] = { ...item.pos, y: maxY };
            }
            break;
          }
          case 'bottom': {
            const minY = Math.min(...items.map((i) => i.pos.y));
            for (const item of items) {
              newPositions[item.key] = { ...item.pos, y: minY };
            }
            break;
          }
          case 'center-h': {
            const xs = items.map((i) => i.pos.x);
            const center = (Math.min(...xs) + Math.max(...xs)) / 2;
            for (const item of items) {
              newPositions[item.key] = { ...item.pos, x: snapToGrid(center) };
            }
            break;
          }
          case 'center-v': {
            const ys = items.map((i) => i.pos.y);
            const center = (Math.min(...ys) + Math.max(...ys)) / 2;
            for (const item of items) {
              newPositions[item.key] = { ...item.pos, y: snapToGrid(center) };
            }
            break;
          }
          case 'distribute-h': {
            const sorted = [...items].sort((a, b) => a.pos.x - b.pos.x);
            if (sorted.length < 3) break;
            const minX = sorted[0].pos.x;
            const maxX = sorted[sorted.length - 1].pos.x;
            const step = (maxX - minX) / (sorted.length - 1);
            for (let i = 0; i < sorted.length; i++) {
              const item = sorted[i];
              newPositions[item.key] = {
                ...item.pos,
                x: snapToGrid(minX + step * i),
              };
            }
            break;
          }
          case 'distribute-v': {
            const sorted = [...items].sort((a, b) => a.pos.y - b.pos.y);
            if (sorted.length < 3) break;
            const minY = sorted[0].pos.y;
            const maxY = sorted[sorted.length - 1].pos.y;
            const step = (maxY - minY) / (sorted.length - 1);
            for (let i = 0; i < sorted.length; i++) {
              const item = sorted[i];
              newPositions[item.key] = {
                ...item.pos,
                y: snapToGrid(minY + step * i),
              };
            }
            break;
          }
        }

        debouncedSave(newPositions, s.portSignalOrders);
        return { positions: newPositions };
      });
    },

    // ── Undo / Redo ──────────────────────────────────────────────

    undo: () => {
      const prev = undoStack.pop();
      if (!prev) return;
      redoStack.push({
        positions: { ...get().positions },
        portSignalOrders: clonePortSignalOrders(get().portSignalOrders),
      });
      set({
        positions: prev.positions,
        portSignalOrders: clonePortSignalOrders(prev.portSignalOrders),
      });
      debouncedSave(prev.positions, prev.portSignalOrders);
    },

    redo: () => {
      const next = redoStack.pop();
      if (!next) return;
      undoStack.push({
        positions: { ...get().positions },
        portSignalOrders: clonePortSignalOrders(get().portSignalOrders),
      });
      set({
        positions: next.positions,
        portSignalOrders: clonePortSignalOrders(next.portSignalOrders),
      });
      debouncedSave(next.positions, next.portSignalOrders);
    },

    // ── Context menu ────────────────────────────────────────────

    openContextMenu: (x, y, kind = 'align', portId) =>
      set({ contextMenu: { x, y, kind, portId } }),
    closeContextMenu: () => set({ contextMenu: null }),

    setPortEditMode: (enabled, portId) => {
      if (!enabled) {
        set({
          portEditMode: false,
          portEditTargetId: null,
          portEditSnapshot: null,
          contextMenu: null,
        });
        return;
      }
      const st = get();
      const targetId = portId ?? st.contextMenu?.portId ?? null;
      if (!targetId) {
        set({
          portEditMode: false,
          portEditTargetId: null,
          portEditSnapshot: null,
          contextMenu: null,
        });
        return;
      }
      const ports = getCurrentPortsForState(st);
      if (ports.length === 0 || !ports.some((p) => p.id === targetId)) {
        set({
          portEditMode: false,
          portEditTargetId: null,
          portEditSnapshot: null,
          contextMenu: null,
        });
        return;
      }
      const snapshot = buildPortEditSnapshot(ports, st.currentPath, st.positions);
      set({
        portEditMode: true,
        portEditTargetId: targetId,
        selectedComponentIds: [targetId],
        selectedComponentId: targetId,
        selectedNetId: null,
        portEditSnapshot: snapshot,
        contextMenu: null,
      });
    },

    reorderPortSignals: (portId, orderedSignals) => {
      const st = get();
      if (!st.schematic || st.currentPath.length === 0) return;

      const root = getRootSheet(st.schematic);
      const parentPath = st.currentPath.slice(0, -1);
      const parentSheet = resolveSheet(root, parentPath);
      if (!parentSheet) return;
      const moduleId = st.currentPath[st.currentPath.length - 1];
      const mod = parentSheet.modules.find((m) => m.id === moduleId);
      if (!mod) return;

      const ipin = mod.interfacePins.find((p) => p.id === portId);
      const baseSignals = ipin?.signals;
      if (!baseSignals || baseSignals.length < 2) return;

      const normalized = normalizeSignalOrder(baseSignals, orderedSignals);
      if (!normalized) return;

      const key = scopedId(st.currentPath, portId);
      const currentOverride = st.portSignalOrders[key];
      const matchesCurrentOverride = !!currentOverride &&
        currentOverride.length === normalized.length &&
        currentOverride.every((sig, i) => sig === normalized[i]);
      if (matchesCurrentOverride) return;

      const isDefaultOrder = normalized.every((sig, i) => sig === baseSignals[i]);
      if (!currentOverride && isDefaultOrder) return;

      pushUndo(st.positions, st.portSignalOrders);
      set((s) => {
        const next = clonePortSignalOrders(s.portSignalOrders);
        if (isDefaultOrder) {
          delete next[key];
        } else {
          next[key] = [...normalized];
        }
        debouncedSave(s.positions, next);
        return { portSignalOrders: next };
      });
    },

    // ── Navigation ──────────────────────────────────────────────

    navigateInto: (moduleId: string) => {
      const { schematic, currentPath } = get();
      if (!schematic) return;
      const rootSheet = getRootSheet(schematic);
      const currentSheet = resolveSheet(rootSheet, currentPath);
      if (!currentSheet) return;

      const mod = currentSheet.modules.find((m) => m.id === moduleId);
      if (!mod) return;

      const newPath = [...currentPath, moduleId];
      const saved = get().positions;

      const prefix = pathKey(newPath) + ':';
      const hasPositions = Object.keys(get().positions).some((k) =>
        k.startsWith(prefix),
      );

      if (!hasPositions) {
        const ports = derivePortsFromModule(
          mod,
          getSignalOrderOverridesForPath(get().portSignalOrders, newPath),
        );
        const { positions: childPositions, suggestedPortSignalOrders } =
          layoutSheet(mod.sheet, newPath, saved, ports);
        set((s) => ({
          currentPath: newPath,
          positions: { ...s.positions, ...childPositions },
          portSignalOrders: mergeAutoPortSignalOrders(
            s.portSignalOrders,
            suggestedPortSignalOrders,
          ),
          selectedComponentIds: [],
          selectedComponentId: null,
          selectedNetId: null,
          hoveredComponentId: null,
          portEditMode: false,
          portEditTargetId: null,
          portEditSnapshot: null,
          contextMenu: null,
        }));
      } else {
        set({
          currentPath: newPath,
          selectedComponentIds: [],
          selectedComponentId: null,
          selectedNetId: null,
          hoveredComponentId: null,
          portEditMode: false,
          portEditTargetId: null,
          portEditSnapshot: null,
          contextMenu: null,
        });
      }
    },

    navigateUp: () => {
      const { currentPath } = get();
      if (currentPath.length === 0) return;
      set({
        currentPath: currentPath.slice(0, -1),
        selectedComponentIds: [],
        selectedComponentId: null,
        selectedNetId: null,
        hoveredComponentId: null,
        portEditMode: false,
        portEditTargetId: null,
        portEditSnapshot: null,
        contextMenu: null,
      });
    },

    navigateToPath: (path: string[]) => {
      const { schematic } = get();
      if (!schematic) return;
      const rootSheet = getRootSheet(schematic);
      if (resolveSheet(rootSheet, path) === null) return;

      const saved = get().positions;
      const prefix = pathKey(path) + ':';
      const hasPositions = Object.keys(get().positions).some((k) =>
        k.startsWith(prefix),
      );

      if (!hasPositions && path.length > 0) {
        const sheet = resolveSheet(rootSheet, path);
        if (sheet) {
          const parentPath = path.slice(0, -1);
          const parentSheet = resolveSheet(rootSheet, parentPath);
          const modId = path[path.length - 1];
          const mod = parentSheet?.modules.find((m) => m.id === modId);
          const ports = mod
            ? derivePortsFromModule(
                mod,
                getSignalOrderOverridesForPath(get().portSignalOrders, path),
              )
            : [];
          const { positions: childPositions, suggestedPortSignalOrders } =
            layoutSheet(sheet, path, saved, ports);
          set((s) => ({
            currentPath: path,
            positions: { ...s.positions, ...childPositions },
            portSignalOrders: mergeAutoPortSignalOrders(
              s.portSignalOrders,
              suggestedPortSignalOrders,
            ),
            selectedComponentIds: [],
            selectedComponentId: null,
            selectedNetId: null,
            hoveredComponentId: null,
            portEditMode: false,
            portEditTargetId: null,
            portEditSnapshot: null,
            contextMenu: null,
          }));
          return;
        }
      }

      set({
        currentPath: path,
        selectedComponentIds: [],
        selectedComponentId: null,
        selectedNetId: null,
        hoveredComponentId: null,
        portEditMode: false,
        portEditTargetId: null,
        portEditSnapshot: null,
        contextMenu: null,
      });
    },
  })),
);

// ── Stable defaults ────────────────────────────────────────────

const ZERO_POS: ComponentPosition = { x: 0, y: 0 };

// ── Selectors ──────────────────────────────────────────────────

export function useCurrentSheet(): SchematicSheet | null {
  return useSchematicStore((s) => {
    if (!s.schematic) return null;
    const root = getRootSheet(s.schematic);
    return resolveSheet(root, s.currentPath);
  });
}

export function useComponentPosition(id: string): ComponentPosition {
  return useSchematicStore((s) => {
    const key = scopedId(s.currentPath, id);
    return s.positions[key] ?? ZERO_POS;
  });
}

export function useIsComponentSelected(id: string): boolean {
  return useSchematicStore((s) => s.selectedComponentIds.includes(id));
}

export function useIsComponentHovered(id: string): boolean {
  return useSchematicStore((s) => s.hoveredComponentId === id);
}

export function useIsComponentDragging(id: string): boolean {
  return useSchematicStore((s) => s.dragComponentId === id);
}

export function useComponentNets(componentId: string | null): SchematicNet[] {
  return useSchematicStore((s) => {
    if (!componentId || !s.schematic) return [];
    const root = getRootSheet(s.schematic);
    const sheet = resolveSheet(root, s.currentPath);
    if (!sheet) return [];
    return sheet.nets.filter((n) =>
      n.pins.some((p) => p.componentId === componentId),
    );
  });
}

export function useComponent(id: string | null): SchematicComponent | null {
  return useSchematicStore((s) => {
    if (!id || !s.schematic) return null;
    const root = getRootSheet(s.schematic);
    const sheet = resolveSheet(root, s.currentPath);
    if (!sheet) return null;
    return sheet.components.find((c) => c.id === id) ?? null;
  });
}

export function useModule(id: string | null): SchematicModule | null {
  return useSchematicStore((s) => {
    if (!id || !s.schematic) return null;
    const root = getRootSheet(s.schematic);
    const sheet = resolveSheet(root, s.currentPath);
    if (!sheet) return null;
    return sheet.modules.find((m) => m.id === id) ?? null;
  });
}

const EMPTY_PORTS: SchematicPort[] = [];

export function useCurrentPorts(): SchematicPort[] {
  return useSchematicStore((s) => {
    if (!s.schematic || s.currentPath.length === 0) return EMPTY_PORTS;
    const root = getRootSheet(s.schematic);
    const parentPath = s.currentPath.slice(0, -1);
    const parentSheet = resolveSheet(root, parentPath);
    if (!parentSheet) return EMPTY_PORTS;
    const moduleId = s.currentPath[s.currentPath.length - 1];
    const mod = parentSheet.modules.find((m) => m.id === moduleId);
    if (!mod) return EMPTY_PORTS;
    return derivePortsFromModule(
      mod,
      getSignalOrderOverridesForPath(s.portSignalOrders, s.currentPath),
    );
  });
}

const EMPTY_POWER_PORTS: SchematicPowerPort[] = [];

export function useCurrentPowerPorts(): SchematicPowerPort[] {
  return useSchematicStore((s) => {
    if (!s.schematic) return EMPTY_POWER_PORTS;
    const root = getRootSheet(s.schematic);
    const sheet = resolveSheet(root, s.currentPath);
    if (!sheet) return EMPTY_POWER_PORTS;
    return derivePowerPorts(sheet);
  });
}

export function useParentModule(): SchematicModule | null {
  return useSchematicStore((s) => {
    if (!s.schematic || s.currentPath.length === 0) return null;
    const root = getRootSheet(s.schematic);
    const parentPath = s.currentPath.slice(0, -1);
    const parentSheet = resolveSheet(root, parentPath);
    if (!parentSheet) return null;
    const moduleId = s.currentPath[s.currentPath.length - 1];
    return parentSheet.modules.find((m) => m.id === moduleId) ?? null;
  });
}
