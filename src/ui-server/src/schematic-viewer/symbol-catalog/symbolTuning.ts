import type { SchematicSymbolFamily } from '../types/schematic';

export type ComponentSymbolFamily = Exclude<SchematicSymbolFamily, 'connector'>;

export interface SymbolRenderTuning {
  bodyOffsetX: number;
  bodyOffsetY: number;
  bodyRotationDeg: number;
  bodyScaleX?: number;
  bodyScaleY?: number;
  leadDelta: number;
}

type SymbolRenderTuningOverride = Partial<SymbolRenderTuning>;

const TUNING_STORAGE_KEY = 'atopile.symbol_tuner.v2';

const DEFAULT_TUNING: SymbolRenderTuning = {
  bodyOffsetX: 0,
  bodyOffsetY: 0,
  bodyRotationDeg: 0,
  bodyScaleX: 1,
  bodyScaleY: 1,
  leadDelta: 0,
};

export const COMPONENT_SYMBOL_FAMILIES: ComponentSymbolFamily[] = [
  'resistor',
  'capacitor',
  'capacitor_polarized',
  'inductor',
  'diode',
  'led',
  'transistor_npn',
  'transistor_pnp',
  'mosfet_n',
  'mosfet_p',
  'testpoint',
];

export const SYMBOL_RENDER_TUNING: Record<
  ComponentSymbolFamily,
  SymbolRenderTuning
> = {
  resistor: {
    bodyOffsetX: 0,
    bodyOffsetY: -0.05,
    bodyRotationDeg: 0,
    bodyScaleX: 2,
    bodyScaleY: 2,
    leadDelta: 0,
  },
  capacitor: {
    bodyOffsetX: 0,
    bodyOffsetY: -0.05,
    bodyRotationDeg: 90,
    bodyScaleX: 2.01,
    bodyScaleY: 2.08,
    leadDelta: 0.05,
  },
  capacitor_polarized: {
    bodyOffsetX: -0.9,
    bodyOffsetY: -0.05,
    bodyRotationDeg: 90,
    bodyScaleX: 2,
    bodyScaleY: 2,
    leadDelta: -0.1,
  },
  inductor: {
    bodyOffsetX: 0,
    bodyOffsetY: 0.25,
    bodyRotationDeg: 0,
    bodyScaleX: 2,
    bodyScaleY: 2,
    leadDelta: -0.05,
  },
  diode: {
    bodyOffsetX: 0,
    bodyOffsetY: -0.05,
    bodyRotationDeg: 0,
    bodyScaleX: 1,
    bodyScaleY: 1,
    leadDelta: 0,
  },
  led: {
    bodyOffsetX: -1.55,
    bodyOffsetY: -0.45,
    bodyRotationDeg: 0,
    bodyScaleX: 2,
    bodyScaleY: 2,
    leadDelta: 0,
  },
  transistor_npn: {
    bodyOffsetX: 1.2,
    bodyOffsetY: -0.05,
    bodyRotationDeg: 0,
    bodyScaleX: 1,
    bodyScaleY: 1,
    leadDelta: 0,
  },
  transistor_pnp: {
    bodyOffsetX: 1.2,
    bodyOffsetY: -0.05,
    bodyRotationDeg: 0,
    bodyScaleX: 1,
    bodyScaleY: 1,
    leadDelta: 0,
  },
  mosfet_n: {
    bodyOffsetX: 1.4,
    bodyOffsetY: -0.05,
    bodyRotationDeg: 0,
    bodyScaleX: 1,
    bodyScaleY: 1,
    leadDelta: 0,
  },
  mosfet_p: {
    bodyOffsetX: 1.4,
    bodyOffsetY: -0.05,
    bodyRotationDeg: 0,
    bodyScaleX: 1,
    bodyScaleY: 1,
    leadDelta: 0,
  },
  testpoint: {
    bodyOffsetX: 0,
    bodyOffsetY: -0.04,
    bodyRotationDeg: 0,
    bodyScaleX: 1,
    bodyScaleY: 1,
    leadDelta: -1.15,
  },
};

let runtimeOverrides: Partial<Record<ComponentSymbolFamily, SymbolRenderTuningOverride>> = {};
let changeRevision = 0;
const changeListeners = new Set<() => void>();

let cachedStorageRaw: string | null | undefined;
let cachedStorageOverrides: Partial<Record<ComponentSymbolFamily, SymbolRenderTuningOverride>> = {};

function notifyChange(): void {
  changeRevision += 1;
  for (const listener of changeListeners) listener();
}

function shouldUseStoredRenderOverrides(): boolean {
  if (typeof window === 'undefined') return false;
  try {
    const params = new URLSearchParams(window.location.search);
    return (
      import.meta.env.DEV
      || params.get('restore') === '1'
      || params.get('symbolTuning') === '1'
      || params.get('symbolDev') === '1'
    );
  } catch {
    return false;
  }
}

function numberOrUndefined(value: unknown): number | undefined {
  return typeof value === 'number' && Number.isFinite(value) ? value : undefined;
}

function sanitizeRenderOverride(value: unknown): SymbolRenderTuningOverride | undefined {
  if (!value || typeof value !== 'object') return undefined;
  const candidate = value as Partial<SymbolRenderTuning>;
  const out: SymbolRenderTuningOverride = {};
  const bodyOffsetX = numberOrUndefined(candidate.bodyOffsetX);
  const bodyOffsetY = numberOrUndefined(candidate.bodyOffsetY);
  const bodyRotationDeg = numberOrUndefined(candidate.bodyRotationDeg);
  const bodyScaleX = numberOrUndefined(candidate.bodyScaleX);
  const bodyScaleY = numberOrUndefined(candidate.bodyScaleY);
  const leadDelta = numberOrUndefined(candidate.leadDelta);
  if (bodyOffsetX != null) out.bodyOffsetX = bodyOffsetX;
  if (bodyOffsetY != null) out.bodyOffsetY = bodyOffsetY;
  if (bodyRotationDeg != null) out.bodyRotationDeg = bodyRotationDeg;
  if (bodyScaleX != null) out.bodyScaleX = bodyScaleX;
  if (bodyScaleY != null) out.bodyScaleY = bodyScaleY;
  if (leadDelta != null) out.leadDelta = leadDelta;
  return Object.keys(out).length > 0 ? out : undefined;
}

function parseStoredRenderOverrides(
  raw: string,
): Partial<Record<ComponentSymbolFamily, SymbolRenderTuningOverride>> {
  try {
    const parsed = JSON.parse(raw) as Record<string, unknown>;
    const out: Partial<Record<ComponentSymbolFamily, SymbolRenderTuningOverride>> = {};
    for (const family of COMPONENT_SYMBOL_FAMILIES) {
      const override = sanitizeRenderOverride(parsed[family]);
      if (override) out[family] = override;
    }
    return out;
  } catch {
    return {};
  }
}

function getStoredRenderOverride(
  family: ComponentSymbolFamily,
): SymbolRenderTuningOverride | undefined {
  if (typeof window === 'undefined') return undefined;
  if (!shouldUseStoredRenderOverrides()) return undefined;

  let raw: string | null;
  try {
    raw = window.localStorage.getItem(TUNING_STORAGE_KEY);
  } catch {
    return undefined;
  }

  if (raw !== cachedStorageRaw) {
    cachedStorageRaw = raw;
    cachedStorageOverrides = raw ? parseStoredRenderOverrides(raw) : {};
  }
  return cachedStorageOverrides[family];
}

function applyRenderOverride(
  base: SymbolRenderTuning,
  override?: SymbolRenderTuningOverride,
): SymbolRenderTuning {
  if (!override) return base;
  return {
    bodyOffsetX: override.bodyOffsetX ?? base.bodyOffsetX,
    bodyOffsetY: override.bodyOffsetY ?? base.bodyOffsetY,
    bodyRotationDeg: override.bodyRotationDeg ?? base.bodyRotationDeg,
    bodyScaleX: override.bodyScaleX ?? base.bodyScaleX,
    bodyScaleY: override.bodyScaleY ?? base.bodyScaleY,
    leadDelta: override.leadDelta ?? base.leadDelta,
  };
}

export function getSymbolRenderTuningRevision(): number {
  return changeRevision;
}

export function subscribeSymbolRenderTuningChanges(listener: () => void): () => void {
  changeListeners.add(listener);
  return () => {
    changeListeners.delete(listener);
  };
}

export function setRuntimeSymbolRenderTuningOverride(
  family: ComponentSymbolFamily,
  override: SymbolRenderTuningOverride | null | undefined,
): void {
  const next = { ...runtimeOverrides };
  if (!override || Object.keys(override).length === 0) {
    delete next[family];
  } else {
    next[family] = sanitizeRenderOverride(override);
  }
  runtimeOverrides = next;
  notifyChange();
}

export function clearRuntimeSymbolRenderTuningOverrides(): void {
  runtimeOverrides = {};
  notifyChange();
}

export function getSymbolRenderTuning(
  family: SchematicSymbolFamily | null,
): SymbolRenderTuning {
  if (!family || family === 'connector') return DEFAULT_TUNING;

  const base = SYMBOL_RENDER_TUNING[family];
  const withStored = applyRenderOverride(base, getStoredRenderOverride(family));
  return applyRenderOverride(withStored, runtimeOverrides[family]);
}
