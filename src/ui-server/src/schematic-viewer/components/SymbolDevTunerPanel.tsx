import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type CSSProperties,
} from 'react';
import type { ThemeColors } from '../utils/theme';
import { useCurrentSheet, useSchematicStore } from '../stores/schematicStore';
import type { SchematicComponent } from '../types/schematic';
import { inferSymbolFamily } from '../symbol-catalog/symbolFamilyInference';
import {
  COMPONENT_SYMBOL_FAMILIES,
  getSymbolRenderTuning,
  setRuntimeSymbolRenderTuningOverride,
  type ComponentSymbolFamily,
  type SymbolRenderTuning,
} from '../symbol-catalog/symbolTuning';
import {
  getSymbolVisualTuning,
  setRuntimeSymbolVisualTuningOverride,
  type SymbolVisualTuning,
} from '../symbol-catalog/symbolVisualTuning';

const GEOMETRY_STORAGE_KEY = 'atopile.symbol_tuner.v2';
const VISUAL_STORAGE_KEY = 'atopile.symbol_tuner.visual.v1';

interface Props {
  theme: ThemeColors;
  onTuningChanged: () => void;
}

function readJsonObject(key: string): Record<string, unknown> {
  if (typeof window === 'undefined') return {};
  try {
    const raw = window.localStorage.getItem(key);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === 'object' ? parsed as Record<string, unknown> : {};
  } catch {
    return {};
  }
}

function writeJsonObject(key: string, value: Record<string, unknown>): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Ignore storage write errors in dev tooling.
  }
}

function updateStoredFamilyTuning(
  key: string,
  family: ComponentSymbolFamily,
  value: unknown | null,
): void {
  const next = readJsonObject(key);
  if (value == null) {
    delete next[family];
  } else {
    next[family] = value;
  }
  writeJsonObject(key, next);
}

function numberFieldStyle(theme: ThemeColors): CSSProperties {
  return {
    width: 78,
    borderRadius: 4,
    border: `1px solid ${theme.borderColor}`,
    background: theme.bgTertiary,
    color: theme.textPrimary,
    padding: '2px 6px',
    fontSize: 12,
    fontFamily: 'monospace',
  };
}

function controlLabelStyle(theme: ThemeColors): CSSProperties {
  return {
    fontSize: 11,
    color: theme.textMuted,
  };
}

function NumberControl({
  label,
  value,
  step,
  onChange,
  theme,
}: {
  label: string;
  value: number;
  step?: number;
  onChange: (value: number) => void;
  theme: ThemeColors;
}) {
  return (
    <label style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: 6, alignItems: 'center' }}>
      <span style={controlLabelStyle(theme)}>{label}</span>
      <input
        type="number"
        step={step ?? 0.01}
        value={Number.isFinite(value) ? value : 0}
        onChange={(event) => {
          const next = Number(event.target.value);
          if (Number.isFinite(next)) onChange(next);
        }}
        style={numberFieldStyle(theme)}
      />
    </label>
  );
}

function FamilyBlockTitle({
  title,
  theme,
}: {
  title: string;
  theme: ThemeColors;
}) {
  return (
    <div
      style={{
        marginTop: 10,
        marginBottom: 4,
        fontSize: 11,
        fontWeight: 600,
        color: theme.textSecondary,
        letterSpacing: 0.2,
        textTransform: 'uppercase',
      }}
    >
      {title}
    </div>
  );
}

function cloneRenderTuning(tuning: SymbolRenderTuning): SymbolRenderTuning {
  return {
    bodyOffsetX: tuning.bodyOffsetX,
    bodyOffsetY: tuning.bodyOffsetY,
    bodyRotationDeg: tuning.bodyRotationDeg,
    bodyScaleX: tuning.bodyScaleX ?? 1,
    bodyScaleY: tuning.bodyScaleY ?? 1,
    leadDelta: tuning.leadDelta,
  };
}

function cloneVisualTuning(tuning: SymbolVisualTuning): SymbolVisualTuning {
  return {
    symbolStrokeWidth: tuning.symbolStrokeWidth,
    leadStrokeWidth: tuning.leadStrokeWidth,
    connectionDotRadius: tuning.connectionDotRadius,
    designator: { ...tuning.designator },
    value: { ...tuning.value },
    package: { ...tuning.package },
  };
}

function resolveSelectedComponent(
  sheet: ReturnType<typeof useCurrentSheet>,
  selectedId: string | null,
): SchematicComponent | null {
  if (!sheet || !selectedId) return null;
  return sheet.components.find((component) => component.id === selectedId) ?? null;
}

export function SymbolDevTunerPanel({
  theme,
  onTuningChanged,
}: Props) {
  const selectedId = useSchematicStore((state) => state.selectedComponentId);
  const sheet = useCurrentSheet();
  const selectedComponent = useMemo(
    () => resolveSelectedComponent(sheet, selectedId),
    [sheet, selectedId],
  );
  const selectedFamily = useMemo(
    () => (selectedComponent ? inferSymbolFamily(selectedComponent) : null),
    [selectedComponent],
  );

  const [activeFamily, setActiveFamily] = useState<ComponentSymbolFamily | null>(null);
  const [geometryDraft, setGeometryDraft] = useState<SymbolRenderTuning | null>(null);
  const [visualDraft, setVisualDraft] = useState<SymbolVisualTuning | null>(null);
  const [statusText, setStatusText] = useState<string>('');

  useEffect(() => {
    if (!selectedComponent || !selectedFamily || selectedFamily === 'connector') {
      setActiveFamily(null);
      setGeometryDraft(null);
      setVisualDraft(null);
      return;
    }

    const nextFamily = selectedFamily;
    setActiveFamily((prev) => {
      if (prev === nextFamily) return prev;
      return nextFamily;
    });
    setGeometryDraft(cloneRenderTuning(getSymbolRenderTuning(nextFamily)));
    setVisualDraft(cloneVisualTuning(getSymbolVisualTuning(nextFamily, selectedComponent)));
  }, [selectedComponent?.id, selectedFamily]);

  const applyDrafts = useCallback((
    family: ComponentSymbolFamily,
    geometry: SymbolRenderTuning,
    visual: SymbolVisualTuning,
    persist = true,
  ) => {
    setRuntimeSymbolRenderTuningOverride(family, geometry);
    setRuntimeSymbolVisualTuningOverride(family, visual);
    if (persist) {
      updateStoredFamilyTuning(GEOMETRY_STORAGE_KEY, family, geometry);
      updateStoredFamilyTuning(VISUAL_STORAGE_KEY, family, visual);
    }
    onTuningChanged();
  }, [onTuningChanged]);

  const patchGeometry = useCallback((
    patch: Partial<SymbolRenderTuning>,
  ) => {
    if (!activeFamily || !geometryDraft || !visualDraft) return;
    const nextGeometry = cloneRenderTuning({ ...geometryDraft, ...patch });
    setGeometryDraft(nextGeometry);
    applyDrafts(activeFamily, nextGeometry, visualDraft);
  }, [activeFamily, geometryDraft, visualDraft, applyDrafts]);

  const patchVisual = useCallback((
    patch: Partial<SymbolVisualTuning>,
  ) => {
    if (!activeFamily || !geometryDraft || !visualDraft) return;
    const nextVisual = cloneVisualTuning({ ...visualDraft, ...patch });
    setVisualDraft(nextVisual);
    applyDrafts(activeFamily, geometryDraft, nextVisual);
  }, [activeFamily, geometryDraft, visualDraft, applyDrafts]);

  const patchVisualLabel = useCallback((
    target: 'designator' | 'value' | 'package',
    patch: Partial<SymbolVisualTuning['designator']> & { followInstanceRotation?: boolean },
  ) => {
    if (!activeFamily || !geometryDraft || !visualDraft) return;
    const nextVisual: SymbolVisualTuning = cloneVisualTuning({
      ...visualDraft,
      [target]: {
        ...visualDraft[target],
        ...patch,
      },
    });
    setVisualDraft(nextVisual);
    applyDrafts(activeFamily, geometryDraft, nextVisual);
  }, [activeFamily, geometryDraft, visualDraft, applyDrafts]);

  const resetFamily = useCallback(() => {
    if (!activeFamily || !selectedComponent) return;
    setRuntimeSymbolRenderTuningOverride(activeFamily, null);
    setRuntimeSymbolVisualTuningOverride(activeFamily, null);
    updateStoredFamilyTuning(GEOMETRY_STORAGE_KEY, activeFamily, null);
    updateStoredFamilyTuning(VISUAL_STORAGE_KEY, activeFamily, null);
    setGeometryDraft(cloneRenderTuning(getSymbolRenderTuning(activeFamily)));
    setVisualDraft(cloneVisualTuning(getSymbolVisualTuning(activeFamily, selectedComponent)));
    onTuningChanged();
    setStatusText(`Reset ${activeFamily}`);
  }, [activeFamily, selectedComponent, onTuningChanged]);

  const applyStrokeToAll = useCallback(() => {
    if (!visualDraft) return;
    const strokeOverride = {
      symbolStrokeWidth: visualDraft.symbolStrokeWidth,
      leadStrokeWidth: visualDraft.leadStrokeWidth,
      connectionDotRadius: visualDraft.connectionDotRadius,
    };
    const stored = readJsonObject(VISUAL_STORAGE_KEY);
    for (const family of COMPONENT_SYMBOL_FAMILIES) {
      setRuntimeSymbolVisualTuningOverride(family, strokeOverride);
      const existing = stored[family];
      if (existing && typeof existing === 'object') {
        stored[family] = { ...(existing as Record<string, unknown>), ...strokeOverride };
      } else {
        stored[family] = strokeOverride;
      }
    }
    writeJsonObject(VISUAL_STORAGE_KEY, stored);
    onTuningChanged();
    setStatusText('Applied thickness/dot to all families');
  }, [visualDraft, onTuningChanged]);

  const copyFamilyJson = useCallback(async () => {
    if (!activeFamily || !geometryDraft || !visualDraft) return;
    const payload = {
      [activeFamily]: {
        ...geometryDraft,
        visual: visualDraft,
      },
    };
    const text = JSON.stringify(payload, null, 2);
    try {
      await navigator.clipboard.writeText(text);
      setStatusText(`Copied ${activeFamily} tuning JSON`);
    } catch {
      setStatusText('Clipboard unavailable');
    }
  }, [activeFamily, geometryDraft, visualDraft]);

  const clearStatus = useCallback(() => setStatusText(''), []);
  useEffect(() => {
    if (!statusText) return;
    const timeout = window.setTimeout(clearStatus, 2200);
    return () => window.clearTimeout(timeout);
  }, [statusText, clearStatus]);

  return (
    <div
      style={{
        position: 'absolute',
        right: 12,
        top: 12,
        zIndex: 230,
        width: 320,
        maxHeight: 'calc(100% - 24px)',
        overflowY: 'auto',
        borderRadius: 8,
        border: `1px solid ${theme.borderColor}`,
        background: `${theme.bgSecondary}f2`,
        boxShadow: '0 4px 14px rgba(0,0,0,0.24)',
        padding: 10,
        fontFamily: 'system-ui, -apple-system, sans-serif',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
        <strong style={{ fontSize: 13 }}>Runtime Symbol Tuner</strong>
        <span style={{ fontSize: 11, color: theme.textMuted }}>
          {activeFamily ?? 'no symbol'}
        </span>
      </div>

      {selectedComponent ? (
        <div style={{ marginTop: 4, fontSize: 11, color: theme.textMuted }}>
          {selectedComponent.designator} · {selectedComponent.packageCode ?? '-'}
        </div>
      ) : (
        <div style={{ marginTop: 4, fontSize: 11, color: theme.textMuted }}>
          Select a component to tune.
        </div>
      )}

      {activeFamily && geometryDraft && visualDraft ? (
        <>
          <FamilyBlockTitle title="Geometry" theme={theme} />
          <NumberControl
            label="Body Offset X"
            value={geometryDraft.bodyOffsetX}
            onChange={(value) => patchGeometry({ bodyOffsetX: value })}
            theme={theme}
          />
          <NumberControl
            label="Body Offset Y"
            value={geometryDraft.bodyOffsetY}
            onChange={(value) => patchGeometry({ bodyOffsetY: value })}
            theme={theme}
          />
          <NumberControl
            label="Body Rotation (deg)"
            value={geometryDraft.bodyRotationDeg}
            step={0.5}
            onChange={(value) => patchGeometry({ bodyRotationDeg: value })}
            theme={theme}
          />
          <NumberControl
            label="Body Scale X"
            value={geometryDraft.bodyScaleX ?? 1}
            onChange={(value) => patchGeometry({ bodyScaleX: value })}
            theme={theme}
          />
          <NumberControl
            label="Body Scale Y"
            value={geometryDraft.bodyScaleY ?? 1}
            onChange={(value) => patchGeometry({ bodyScaleY: value })}
            theme={theme}
          />
          <NumberControl
            label="Lead Delta"
            value={geometryDraft.leadDelta}
            onChange={(value) => patchGeometry({ leadDelta: value })}
            theme={theme}
          />

          <FamilyBlockTitle title="Stroke" theme={theme} />
          <NumberControl
            label="Body Stroke"
            value={visualDraft.symbolStrokeWidth}
            onChange={(value) => patchVisual({ symbolStrokeWidth: value })}
            theme={theme}
          />
          <NumberControl
            label="Lead Stroke"
            value={visualDraft.leadStrokeWidth}
            onChange={(value) => patchVisual({ leadStrokeWidth: value })}
            theme={theme}
          />
          <NumberControl
            label="Connection Dot"
            value={visualDraft.connectionDotRadius}
            onChange={(value) => patchVisual({ connectionDotRadius: value })}
            theme={theme}
          />

          <FamilyBlockTitle title="Designator" theme={theme} />
          <NumberControl
            label="Ref X"
            value={visualDraft.designator.offsetX}
            onChange={(value) => patchVisualLabel('designator', { offsetX: value })}
            theme={theme}
          />
          <NumberControl
            label="Ref Y"
            value={visualDraft.designator.offsetY}
            onChange={(value) => patchVisualLabel('designator', { offsetY: value })}
            theme={theme}
          />
          <NumberControl
            label="Ref Size"
            value={visualDraft.designator.fontSize}
            onChange={(value) => patchVisualLabel('designator', { fontSize: value })}
            theme={theme}
          />
          <NumberControl
            label="Ref Rotation"
            value={visualDraft.designator.rotationDeg}
            onChange={(value) => patchVisualLabel('designator', { rotationDeg: value })}
            theme={theme}
          />

          <FamilyBlockTitle title="Package" theme={theme} />
          <NumberControl
            label="Pkg X"
            value={visualDraft.package.offsetX}
            onChange={(value) => patchVisualLabel('package', { offsetX: value })}
            theme={theme}
          />
          <NumberControl
            label="Pkg Y"
            value={visualDraft.package.offsetY}
            onChange={(value) => patchVisualLabel('package', { offsetY: value })}
            theme={theme}
          />
          <NumberControl
            label="Pkg Size"
            value={visualDraft.package.fontSize}
            onChange={(value) => patchVisualLabel('package', { fontSize: value })}
            theme={theme}
          />
          <NumberControl
            label="Pkg Rotation"
            value={visualDraft.package.rotationDeg}
            onChange={(value) => patchVisualLabel('package', { rotationDeg: value })}
            theme={theme}
          />
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4 }}>
            <input
              type="checkbox"
              checked={visualDraft.package.followInstanceRotation}
              onChange={(event) => {
                patchVisualLabel('package', { followInstanceRotation: event.target.checked });
              }}
            />
            <span style={controlLabelStyle(theme)}>Package follows component rotation</span>
          </label>

          <FamilyBlockTitle title="Value" theme={theme} />
          <NumberControl
            label="Value X"
            value={visualDraft.value.offsetX}
            onChange={(value) => patchVisualLabel('value', { offsetX: value })}
            theme={theme}
          />
          <NumberControl
            label="Value Y"
            value={visualDraft.value.offsetY}
            onChange={(value) => patchVisualLabel('value', { offsetY: value })}
            theme={theme}
          />
          <NumberControl
            label="Value Size"
            value={visualDraft.value.fontSize}
            onChange={(value) => patchVisualLabel('value', { fontSize: value })}
            theme={theme}
          />
          <NumberControl
            label="Value Rotation"
            value={visualDraft.value.rotationDeg}
            onChange={(value) => patchVisualLabel('value', { rotationDeg: value })}
            theme={theme}
          />

          <div style={{ display: 'flex', gap: 6, marginTop: 12, flexWrap: 'wrap' }}>
            <button
              type="button"
              onClick={resetFamily}
              style={{
                borderRadius: 5,
                border: `1px solid ${theme.borderColor}`,
                background: theme.bgTertiary,
                color: theme.textPrimary,
                padding: '4px 8px',
                fontSize: 11,
                cursor: 'pointer',
              }}
            >
              Reset Family
            </button>
            <button
              type="button"
              onClick={applyStrokeToAll}
              style={{
                borderRadius: 5,
                border: `1px solid ${theme.borderColor}`,
                background: theme.bgTertiary,
                color: theme.textPrimary,
                padding: '4px 8px',
                fontSize: 11,
                cursor: 'pointer',
              }}
            >
              Set Stroke All
            </button>
            <button
              type="button"
              onClick={copyFamilyJson}
              style={{
                borderRadius: 5,
                border: `1px solid ${theme.borderColor}`,
                background: theme.bgTertiary,
                color: theme.textPrimary,
                padding: '4px 8px',
                fontSize: 11,
                cursor: 'pointer',
              }}
            >
              Copy JSON
            </button>
          </div>
        </>
      ) : (
        <div style={{ marginTop: 8, fontSize: 11, color: theme.textMuted }}>
          Selected item is not using a custom symbol family.
        </div>
      )}

      {statusText && (
        <div style={{ marginTop: 8, fontSize: 11, color: theme.textSecondary }}>
          {statusText}
        </div>
      )}
    </div>
  );
}

export function useSymbolDevModeEnabled(): boolean {
  return useMemo(() => {
    if (typeof window === 'undefined') return false;
    try {
      const params = new URLSearchParams(window.location.search);
      return (
        import.meta.env.DEV
        || params.get('symbolDev') === '1'
        || params.get('symbolTuning') === '1'
      );
    } catch {
      return import.meta.env.DEV;
    }
  }, []);
}
