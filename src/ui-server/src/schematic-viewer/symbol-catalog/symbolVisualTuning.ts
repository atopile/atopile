import type {
  SchematicComponent,
  SchematicSymbolFamily,
} from '../types/schematic';
import {
  COMPONENT_SYMBOL_FAMILIES,
  getSymbolRenderTuning,
  type ComponentSymbolFamily,
} from './symbolTuning';

export interface SymbolLabelVisualTuning {
  offsetX: number;
  offsetY: number;
  fontSize: number;
  rotationDeg: number;
}

export interface SymbolPackageLabelVisualTuning extends SymbolLabelVisualTuning {
  followInstanceRotation: boolean;
}

export interface SymbolVisualTuning {
  symbolStrokeWidth: number;
  leadStrokeWidth: number;
  connectionDotRadius: number;
  designator: SymbolLabelVisualTuning;
  value: SymbolLabelVisualTuning;
  package: SymbolPackageLabelVisualTuning;
}

type SymbolVisualTuningOverride = Partial<
  Omit<SymbolVisualTuning, 'designator' | 'value' | 'package'>
> & {
  designator?: Partial<SymbolLabelVisualTuning>;
  value?: Partial<SymbolLabelVisualTuning>;
  package?: Partial<SymbolPackageLabelVisualTuning>;
};

const VISUAL_TUNING_STORAGE_KEY = 'atopile.symbol_tuner.visual.v1';
const SYMBOL_BODY_BASE_Y = 0.05;

let cachedStorageRaw: string | null | undefined;
let cachedStorageOverrides: Partial<Record<ComponentSymbolFamily, SymbolVisualTuningOverride>> = {};
let runtimeOverrides: Partial<Record<ComponentSymbolFamily, SymbolVisualTuningOverride>> = {};
let changeRevision = 0;
const changeListeners = new Set<() => void>();

function notifyChange(): void {
  changeRevision += 1;
  for (const listener of changeListeners) listener();
}

function shouldUseStoredVisualOverrides(): boolean {
  if (typeof window === 'undefined') return false;
  try {
    const params = new URLSearchParams(window.location.search);
    // Keep persisted tuner overrides opt-in only so runtime schematic and
    // tuner defaults stay deterministic unless explicitly requested.
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

function defaultLabelFontSize(component: SchematicComponent): number {
  const isSmall = component.bodyWidth * component.bodyHeight < 40;
  const maxDim = Math.min(component.bodyWidth, component.bodyHeight);
  const base = isSmall
    ? Math.min(1.35, Math.max(0.62, maxDim * 0.34))
    : Math.min(1.35, Math.max(0.78, maxDim * 0.18));
  return base * 0.85;
}

export function getDefaultSymbolVisualTuning(
  family: SchematicSymbolFamily | null,
  component: SchematicComponent,
): SymbolVisualTuning {
  const geometryTuning = getSymbolRenderTuning(family);
  const bodyAnchorX = geometryTuning.bodyOffsetX;
  const bodyAnchorY = geometryTuning.bodyOffsetY + SYMBOL_BODY_BASE_Y;
  const designatorFontSize = defaultLabelFontSize(component);
  return {
    symbolStrokeWidth: 0.26,
    leadStrokeWidth: 0.28,
    connectionDotRadius: 0.17,
    designator: {
      offsetX: bodyAnchorX,
      offsetY: bodyAnchorY - Math.min(component.bodyHeight * 0.36, 0.96),
      fontSize: designatorFontSize,
      rotationDeg: 0,
    },
    value: {
      offsetX: bodyAnchorX,
      offsetY: bodyAnchorY + Math.max(component.bodyHeight * 0.42, 1.2),
      fontSize: Math.max(0.5, designatorFontSize * 0.8),
      rotationDeg: 0,
    },
    package: {
      offsetX: bodyAnchorX,
      offsetY: bodyAnchorY - Math.max(component.bodyHeight * 0.5 + 0.82, 1.4),
      fontSize: 0.52,
      rotationDeg: 0,
      followInstanceRotation: true,
    },
  };
}

function mergeLabel<T extends SymbolLabelVisualTuning>(
  base: T,
  override?: Partial<T>,
): T {
  if (!override) return base;
  return {
    ...base,
    ...override,
  };
}

export const SYMBOL_VISUAL_TUNING_OVERRIDES: Partial<
  Record<ComponentSymbolFamily, SymbolVisualTuningOverride>
> = {};

function applyVisualOverride(
  base: SymbolVisualTuning,
  override?: SymbolVisualTuningOverride,
): SymbolVisualTuning {
  if (!override) return base;
  return {
    symbolStrokeWidth: override.symbolStrokeWidth ?? base.symbolStrokeWidth,
    leadStrokeWidth: override.leadStrokeWidth ?? base.leadStrokeWidth,
    connectionDotRadius: override.connectionDotRadius ?? base.connectionDotRadius,
    designator: mergeLabel(base.designator, override.designator),
    value: mergeLabel(base.value, override.value),
    package: mergeLabel(base.package, override.package),
  };
}

function sanitizeVisualOverride(
  value: unknown,
): SymbolVisualTuningOverride | undefined {
  if (!value || typeof value !== 'object') return undefined;
  const candidate = value as Partial<SymbolVisualTuning>;
  const override: SymbolVisualTuningOverride = {};
  const symbolStrokeWidth = numberOrUndefined(candidate.symbolStrokeWidth);
  const leadStrokeWidth = numberOrUndefined(candidate.leadStrokeWidth);
  const connectionDotRadius = numberOrUndefined(candidate.connectionDotRadius);
  if (symbolStrokeWidth != null) override.symbolStrokeWidth = symbolStrokeWidth;
  if (leadStrokeWidth != null) override.leadStrokeWidth = leadStrokeWidth;
  if (connectionDotRadius != null) override.connectionDotRadius = connectionDotRadius;
  const designator = sanitizeLabelOverride(candidate.designator);
  const valueTuning = sanitizeLabelOverride(candidate.value);
  const packageTuning = sanitizePackageOverride(candidate.package);
  if (designator) override.designator = designator;
  if (valueTuning) override.value = valueTuning;
  if (packageTuning) override.package = packageTuning;
  return Object.keys(override).length > 0 ? override : undefined;
}

function numberOrUndefined(value: unknown): number | undefined {
  return typeof value === 'number' && Number.isFinite(value) ? value : undefined;
}

function sanitizeLabelOverride(
  value: unknown,
): Partial<SymbolLabelVisualTuning> | undefined {
  if (!value || typeof value !== 'object') return undefined;
  const candidate = value as Partial<SymbolLabelVisualTuning>;
  const out: Partial<SymbolLabelVisualTuning> = {};
  const offsetX = numberOrUndefined(candidate.offsetX);
  const offsetY = numberOrUndefined(candidate.offsetY);
  const fontSize = numberOrUndefined(candidate.fontSize);
  const rotationDeg = numberOrUndefined(candidate.rotationDeg);
  if (offsetX != null) out.offsetX = offsetX;
  if (offsetY != null) out.offsetY = offsetY;
  if (fontSize != null) out.fontSize = fontSize;
  if (rotationDeg != null) out.rotationDeg = rotationDeg;
  return Object.keys(out).length > 0 ? out : undefined;
}

function sanitizePackageOverride(
  value: unknown,
): Partial<SymbolPackageLabelVisualTuning> | undefined {
  if (!value || typeof value !== 'object') return undefined;
  const candidate = value as Partial<SymbolPackageLabelVisualTuning>;
  const base = sanitizeLabelOverride(value) as Partial<SymbolPackageLabelVisualTuning>;
  if (typeof candidate.followInstanceRotation === 'boolean') {
    base.followInstanceRotation = candidate.followInstanceRotation;
  }
  return Object.keys(base).length > 0 ? base : undefined;
}

function parseStoredVisualOverrides(
  raw: string,
): Partial<Record<ComponentSymbolFamily, SymbolVisualTuningOverride>> {
  try {
    const parsed = JSON.parse(raw) as Record<string, unknown>;
    const out: Partial<Record<ComponentSymbolFamily, SymbolVisualTuningOverride>> = {};
    for (const family of COMPONENT_SYMBOL_FAMILIES) {
      const override = sanitizeVisualOverride(parsed[family]);
      if (override) out[family] = override;
    }
    return out;
  } catch {
    return {};
  }
}

function getStoredVisualOverride(
  family: ComponentSymbolFamily,
): SymbolVisualTuningOverride | undefined {
  if (typeof window === 'undefined') return undefined;
  if (!shouldUseStoredVisualOverrides()) return undefined;
  let raw: string | null;
  try {
    raw = window.localStorage.getItem(VISUAL_TUNING_STORAGE_KEY);
  } catch {
    return undefined;
  }
  if (raw !== cachedStorageRaw) {
    cachedStorageRaw = raw;
    cachedStorageOverrides = raw ? parseStoredVisualOverrides(raw) : {};
  }
  return cachedStorageOverrides[family];
}

export function getSymbolVisualTuningRevision(): number {
  return changeRevision;
}

export function subscribeSymbolVisualTuningChanges(listener: () => void): () => void {
  changeListeners.add(listener);
  return () => {
    changeListeners.delete(listener);
  };
}

export function setRuntimeSymbolVisualTuningOverride(
  family: ComponentSymbolFamily,
  override: SymbolVisualTuningOverride | null | undefined,
): void {
  const next = { ...runtimeOverrides };
  const sanitized = sanitizeVisualOverride(override);
  if (!sanitized) {
    delete next[family];
  } else {
    next[family] = sanitized;
  }
  runtimeOverrides = next;
  notifyChange();
}

export function clearRuntimeSymbolVisualTuningOverrides(): void {
  runtimeOverrides = {};
  notifyChange();
}

export function getSymbolVisualTuning(
  family: SchematicSymbolFamily | null,
  component: SchematicComponent,
): SymbolVisualTuning {
  const base = getDefaultSymbolVisualTuning(family, component);
  if (!family || family === 'connector') return base;

  const staticOverride = SYMBOL_VISUAL_TUNING_OVERRIDES[family];
  const withStatic = applyVisualOverride(base, staticOverride);
  const withStored = applyVisualOverride(withStatic, getStoredVisualOverride(family));
  return applyVisualOverride(withStored, runtimeOverrides[family]);
}
