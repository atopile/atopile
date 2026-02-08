/**
 * Zustand store for multi-component schematic state with hierarchy navigation.
 *
 * Architecture:
 * - `schematic` holds the raw JSON data (SchematicData)
 * - `currentPath` tracks which module we're "inside" (breadcrumb trail)
 * - `currentSheet` is derived: resolves the path to get the active sheet
 * - Positions are scoped per sheet (keyed by path string)
 * - Live drag uses a shared mutable ref (zero re-renders during drag)
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
  SchematicLayout,
} from '../types/schematic';
import { getRootSheet, resolveSheet, derivePortsFromModule } from '../types/schematic';
import { autoLayoutSheet, mergePositions, snapToGrid } from '../lib/schematicLayout';

// ── State shape ────────────────────────────────────────────────

interface SchematicState {
  // Data
  schematic: SchematicData | null;
  /** Positions keyed by "pathKey:itemId" for per-sheet scoping */
  positions: Record<string, ComponentPosition>;
  isLoading: boolean;
  loadError: string | null;

  // Hierarchy navigation
  /** Current navigation path — array of module IDs from root */
  currentPath: string[];

  // Interaction
  selectedComponentId: string | null;
  selectedNetId: string | null;
  hoveredComponentId: string | null;
  hoveredNetId: string | null;
  dragComponentId: string | null;

  // Actions
  loadSchematic: (url: string) => Promise<void>;
  loadSchematicData: (data: SchematicData) => void;
  commitPosition: (componentId: string, pos: ComponentPosition) => void;
  startDrag: (componentId: string) => void;
  endDrag: () => void;
  selectComponent: (id: string | null) => void;
  selectNet: (id: string | null) => void;
  hoverComponent: (id: string | null) => void;
  hoverNet: (id: string | null) => void;
  resetLayout: () => void;

  // Transform (KiCad-style hotkeys)
  rotateSelected: () => void;
  mirrorSelectedX: () => void;
  mirrorSelectedY: () => void;

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
};

// ── Path key for position scoping ──────────────────────────────

function pathKey(path: string[]): string {
  return path.length === 0 ? '__root__' : path.join('/');
}

function scopedId(path: string[], itemId: string): string {
  return `${pathKey(path)}:${itemId}`;
}

// ── Debounced save ─────────────────────────────────────────────

let saveTimer: ReturnType<typeof setTimeout> | null = null;

function debouncedSave(positions: Record<string, ComponentPosition>) {
  if (saveTimer) clearTimeout(saveTimer);
  saveTimer = setTimeout(() => {
    const layout: SchematicLayout = { version: '2.0', positions };
    try {
      if (window.parent !== window) {
        window.parent.postMessage({ type: 'save-layout', layout }, '*');
      }
      localStorage.setItem('schematic-layout', JSON.stringify(layout));
    } catch {
      /* ignore */
    }
  }, 500);
}

function loadSavedLayout(): SchematicLayout | null {
  try {
    const raw = localStorage.getItem('schematic-layout');
    if (raw) return JSON.parse(raw) as SchematicLayout;
  } catch {
    /* ignore */
  }
  return null;
}

// ── Layout a sheet and scope positions to a path ────────────────

function layoutSheet(
  sheet: SchematicSheet,
  path: string[],
  saved: SchematicLayout | null,
  ports: SchematicPort[] = [],
): Record<string, ComponentPosition> {
  const autoPos = autoLayoutSheet(sheet, ports);
  const savedForPath: Record<string, ComponentPosition> = {};

  // Extract saved positions for this path
  if (saved?.positions) {
    const prefix = pathKey(path) + ':';
    for (const [key, pos] of Object.entries(saved.positions)) {
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
  return scoped;
}

// ── Store ──────────────────────────────────────────────────────

export const useSchematicStore = create<SchematicState>()(
  subscribeWithSelector((set, get) => ({
    schematic: null,
    positions: {},
    isLoading: false,
    loadError: null,
    currentPath: [],
    selectedComponentId: null,
    selectedNetId: null,
    hoveredComponentId: null,
    hoveredNetId: null,
    dragComponentId: null,

    loadSchematic: async (url: string) => {
      set({ isLoading: true, loadError: null });
      try {
        const resp = await fetch(url);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data: SchematicData = await resp.json();
        const rootSheet = getRootSheet(data);
        const saved = loadSavedLayout();
        const positions = layoutSheet(rootSheet, [], saved);
        set({
          schematic: data,
          positions,
          currentPath: [],
          isLoading: false,
          selectedComponentId: null,
          selectedNetId: null,
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
      const saved = loadSavedLayout();
      const positions = layoutSheet(rootSheet, [], saved);
      set({
        schematic: data,
        positions,
        currentPath: [],
        isLoading: false,
        loadError: null,
        selectedComponentId: null,
        selectedNetId: null,
      });
    },

    commitPosition: (componentId, pos) => {
      const path = get().currentPath;
      const key = scopedId(path, componentId);
      // Preserve rotation/mirror from existing position when committing drag
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
        debouncedSave(newPositions);
        return { positions: newPositions };
      });
    },

    startDrag: (componentId) => set({ dragComponentId: componentId }),

    endDrag: () => {
      if (liveDrag.componentId) {
        const id = liveDrag.componentId;
        const pos = { x: liveDrag.x, y: liveDrag.y };
        liveDrag.componentId = null;
        liveDrag.version++;
        get().commitPosition(id, pos);
      }
      set({ dragComponentId: null });
    },

    selectComponent: (id) =>
      set((s) => ({
        selectedComponentId: s.selectedComponentId === id ? null : id,
        selectedNetId: null,
      })),

    selectNet: (id) =>
      set((s) => ({
        selectedNetId: s.selectedNetId === id ? null : id,
        selectedComponentId: null,
      })),

    hoverComponent: (id) => set({ hoveredComponentId: id }),
    hoverNet: (id) => set({ hoveredNetId: id }),

    resetLayout: () => {
      const { schematic, currentPath } = get();
      if (!schematic) return;
      const rootSheet = getRootSheet(schematic);
      const sheet = resolveSheet(rootSheet, currentPath);
      if (!sheet) return;
      // Derive ports from parent module if navigated inside
      let ports: SchematicPort[] = [];
      if (currentPath.length > 0) {
        const parentPath = currentPath.slice(0, -1);
        const parentSheet = resolveSheet(rootSheet, parentPath);
        const modId = currentPath[currentPath.length - 1];
        const mod = parentSheet?.modules.find((m) => m.id === modId);
        if (mod) ports = derivePortsFromModule(mod);
      }
      const positions = layoutSheet(sheet, currentPath, null, ports);
      set((s) => {
        // Merge — keep other sheets' positions, replace current sheet's
        const prefix = pathKey(currentPath) + ':';
        const kept: Record<string, ComponentPosition> = {};
        for (const [k, v] of Object.entries(s.positions)) {
          if (!k.startsWith(prefix)) kept[k] = v;
        }
        const merged = { ...kept, ...positions };
        debouncedSave(merged);
        return { positions: merged };
      });
      try {
        localStorage.removeItem('schematic-layout');
      } catch {
        /* ignore */
      }
    },

    // ── Transform (KiCad-style: R = rotate, X = mirror H, Y = mirror V)

    rotateSelected: () => {
      const { selectedComponentId, currentPath } = get();
      if (!selectedComponentId) return;
      const key = scopedId(currentPath, selectedComponentId);
      set((s) => {
        const pos = s.positions[key] || { x: 0, y: 0 };
        const cur = pos.rotation || 0;
        const newPos = { ...pos, rotation: (cur + 90) % 360 };
        const newPositions = { ...s.positions, [key]: newPos };
        debouncedSave(newPositions);
        return { positions: newPositions };
      });
    },

    mirrorSelectedX: () => {
      const { selectedComponentId, currentPath } = get();
      if (!selectedComponentId) return;
      const key = scopedId(currentPath, selectedComponentId);
      set((s) => {
        const pos = s.positions[key] || { x: 0, y: 0 };
        const newPos = { ...pos, mirrorX: !pos.mirrorX };
        const newPositions = { ...s.positions, [key]: newPos };
        debouncedSave(newPositions);
        return { positions: newPositions };
      });
    },

    mirrorSelectedY: () => {
      const { selectedComponentId, currentPath } = get();
      if (!selectedComponentId) return;
      const key = scopedId(currentPath, selectedComponentId);
      set((s) => {
        const pos = s.positions[key] || { x: 0, y: 0 };
        const newPos = { ...pos, mirrorY: !pos.mirrorY };
        const newPositions = { ...s.positions, [key]: newPos };
        debouncedSave(newPositions);
        return { positions: newPositions };
      });
    },

    // ── Navigation ──────────────────────────────────────────────

    navigateInto: (moduleId: string) => {
      const { schematic, currentPath } = get();
      if (!schematic) return;
      const rootSheet = getRootSheet(schematic);
      const currentSheet = resolveSheet(rootSheet, currentPath);
      if (!currentSheet) return;

      // Verify the module exists
      const mod = currentSheet.modules.find((m) => m.id === moduleId);
      if (!mod) return;

      const newPath = [...currentPath, moduleId];
      const saved = loadSavedLayout();

      // Layout the child sheet if not already done
      const prefix = pathKey(newPath) + ':';
      const hasPositions = Object.keys(get().positions).some((k) =>
        k.startsWith(prefix),
      );

      if (!hasPositions) {
        const ports = derivePortsFromModule(mod);
        const childPositions = layoutSheet(mod.sheet, newPath, saved, ports);
        set((s) => ({
          currentPath: newPath,
          positions: { ...s.positions, ...childPositions },
          selectedComponentId: null,
          selectedNetId: null,
          hoveredComponentId: null,
        }));
      } else {
        set({
          currentPath: newPath,
          selectedComponentId: null,
          selectedNetId: null,
          hoveredComponentId: null,
        });
      }
    },

    navigateUp: () => {
      const { currentPath } = get();
      if (currentPath.length === 0) return;
      set({
        currentPath: currentPath.slice(0, -1),
        selectedComponentId: null,
        selectedNetId: null,
        hoveredComponentId: null,
      });
    },

    navigateToPath: (path: string[]) => {
      const { schematic } = get();
      if (!schematic) return;
      const rootSheet = getRootSheet(schematic);
      // Verify the path is valid
      if (resolveSheet(rootSheet, path) === null) return;

      // Ensure positions exist for the target sheet
      const saved = loadSavedLayout();
      const prefix = pathKey(path) + ':';
      const hasPositions = Object.keys(get().positions).some((k) =>
        k.startsWith(prefix),
      );

      if (!hasPositions && path.length > 0) {
        const sheet = resolveSheet(rootSheet, path);
        if (sheet) {
          // Derive ports from the parent module
          const parentPath = path.slice(0, -1);
          const parentSheet = resolveSheet(rootSheet, parentPath);
          const modId = path[path.length - 1];
          const mod = parentSheet?.modules.find((m) => m.id === modId);
          const ports = mod ? derivePortsFromModule(mod) : [];
          const childPositions = layoutSheet(sheet, path, saved, ports);
          set((s) => ({
            currentPath: path,
            positions: { ...s.positions, ...childPositions },
            selectedComponentId: null,
            selectedNetId: null,
            hoveredComponentId: null,
          }));
          return;
        }
      }

      set({
        currentPath: path,
        selectedComponentId: null,
        selectedNetId: null,
        hoveredComponentId: null,
      });
    },
  })),
);

// ── Stable fallback ────────────────────────────────────────────

const ZERO_POS: ComponentPosition = { x: 0, y: 0 };

// ── Selectors ──────────────────────────────────────────────────

/**
 * Get the current sheet (resolved from path).
 * Returns the root sheet if path is empty, or the resolved sub-sheet.
 */
export function useCurrentSheet(): SchematicSheet | null {
  return useSchematicStore((s) => {
    if (!s.schematic) return null;
    const root = getRootSheet(s.schematic);
    return resolveSheet(root, s.currentPath);
  });
}

/**
 * Get committed position for a single item, scoped to current path.
 */
export function useComponentPosition(id: string): ComponentPosition {
  return useSchematicStore((s) => {
    const key = scopedId(s.currentPath, id);
    return s.positions[key] ?? ZERO_POS;
  });
}

export function useIsComponentSelected(id: string): boolean {
  return useSchematicStore((s) => s.selectedComponentId === id);
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

/**
 * Get the ports for the current sheet level.
 * Ports exist only when navigated inside a module — they represent
 * the parent module's interfacePins as Altium-style sheet entries.
 * Returns [] at root level.
 */
const EMPTY_PORTS: SchematicPort[] = [];

export function useCurrentPorts(): SchematicPort[] {
  return useSchematicStore((s) => {
    if (!s.schematic || s.currentPath.length === 0) return EMPTY_PORTS;
    const root = getRootSheet(s.schematic);

    // Walk to the parent sheet and find the module we're inside
    const parentPath = s.currentPath.slice(0, -1);
    const parentSheet = resolveSheet(root, parentPath);
    if (!parentSheet) return EMPTY_PORTS;

    const moduleId = s.currentPath[s.currentPath.length - 1];
    const mod = parentSheet.modules.find((m) => m.id === moduleId);
    if (!mod) return EMPTY_PORTS;

    return derivePortsFromModule(mod);
  });
}

/**
 * Get the parent module (the module we're "inside" when navigated).
 * Returns null at root level.
 */
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
