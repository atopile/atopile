import { useState, useCallback, useEffect, useRef } from 'react';
import type { PlotMeta, RequirementData } from './types';
import { updateRequirement, createPlot } from './api';

interface PlotToolbarProps {
  req: RequirementData;
  specIndex: number;
  onDirty: () => void;
  onPlotFieldChange?: (specIndex: number, field: string, value: string) => void;
}

type PlotFieldDef = { key: string; label: string; placeholder: string };

const LINE_CHART_FIELDS: PlotFieldDef[] = [
  { key: 'title', label: 'Title', placeholder: 'Chart Title' },
  { key: 'x', label: 'X Axis', placeholder: 'time, frequency, or dut.param' },
  { key: 'y', label: 'Y Axis', placeholder: 'dut.net or measurement(net)' },
  { key: 'y_secondary', label: 'Y Secondary', placeholder: 'Optional secondary signal' },
  { key: 'color', label: 'Color by', placeholder: 'Sweep param or dut' },
  { key: 'plot_limits', label: 'Show Limits', placeholder: 'true or false' },
];

const BAR_CHART_FIELDS: PlotFieldDef[] = [
  { key: 'title', label: 'Title', placeholder: 'Chart Title' },
  { key: 'x', label: 'X Axis', placeholder: 'Sweep param name (e.g. COUT)' },
  { key: 'y', label: 'Y Axis', placeholder: 'measurement(net)' },
  { key: 'plot_limits', label: 'Show Limits', placeholder: 'true or false' },
];

function fieldsForType(plotType: string | undefined): PlotFieldDef[] {
  if (plotType === 'BarChart') return BAR_CHART_FIELDS;
  return LINE_CHART_FIELDS;
}

const PLOT_TYPES = [
  { value: 'LineChart', label: 'Line Chart' },
  { value: 'BarChart', label: 'Bar Chart' },
];

/** Auto-populate sensible defaults based on requirement context */
function defaultsForType(req: RequirementData, plotType: string): Record<string, string> {
  const base: Record<string, string> = {
    title: req.name,
    y: req.net,
  };
  if (plotType === 'LineChart') {
    if (req.capture === 'ac') {
      base.x = 'frequency';
    } else {
      base.x = 'time';
    }
  }
  if (plotType === 'BarChart') {
    base.x = 'dut';
  }
  return base;
}

export function PlotToolbar({ req, specIndex, onDirty, onPlotFieldChange }: PlotToolbarProps) {
  const [gearOpen, setGearOpen] = useState(false);
  const [addOpen, setAddOpen] = useState(false);
  const toolbarRef = useRef<HTMLDivElement>(null);

  const spec = req.plotSpecs?.[specIndex];
  const meta = spec?.meta;
  const canEditPlot = !!(req.sourceFile && meta?.varName);
  const canAdd = !!(req.sourceFile && req.varName);

  const handlePlotFieldChange = useCallback(async (field: string, value: string) => {
    if (!req.sourceFile || !meta?.varName) return;
    await updateRequirement({
      source_file: req.sourceFile,
      var_name: meta.varName,
      updates: { [field]: value },
    });
    if (onPlotFieldChange) {
      onPlotFieldChange(specIndex, field, value);
    } else {
      onDirty();
    }
  }, [req.sourceFile, meta?.varName, onDirty, onPlotFieldChange, specIndex]);

  const handleCreated = useCallback(() => {
    setAddOpen(false);
    onDirty();
  }, [onDirty]);

  // Close popovers on Escape or click outside
  useEffect(() => {
    if (!gearOpen && !addOpen) return;
    const close = () => { setGearOpen(false); setAddOpen(false); };
    const handleKey = (e: KeyboardEvent) => { if (e.key === 'Escape') close(); };
    const handleClick = (e: MouseEvent) => {
      if (toolbarRef.current && !toolbarRef.current.contains(e.target as Node)) close();
    };
    document.addEventListener('keydown', handleKey);
    document.addEventListener('mousedown', handleClick);
    return () => {
      document.removeEventListener('keydown', handleKey);
      document.removeEventListener('mousedown', handleClick);
    };
  }, [gearOpen, addOpen]);

  return (
    <div className="plot-toolbar" ref={toolbarRef}>
      <div className="plot-toolbar-icons">
        <button
          className={`plot-toolbar-btn${!canEditPlot ? ' plot-toolbar-btn-disabled' : ''}`}
          onClick={() => { if (canEditPlot) { setGearOpen(!gearOpen); setAddOpen(false); } }}
          title={canEditPlot ? 'Plot settings' : 'No plot to configure'}
        >
          <GearIcon />
        </button>
        <button
          className={`plot-toolbar-btn${!canAdd ? ' plot-toolbar-btn-disabled' : ''}`}
          onClick={() => { if (canAdd) { setAddOpen(!addOpen); setGearOpen(false); } }}
          title="Add new plot"
        >
          <PlusIcon />
        </button>
      </div>

      {gearOpen && canEditPlot && (
        <PlotFieldsPopover
          meta={meta!}
          onFieldChange={handlePlotFieldChange}
          onClose={() => setGearOpen(false)}
        />
      )}

      {addOpen && canAdd && (
        <AddPlotPopover
          req={req}
          onClose={() => setAddOpen(false)}
          onCreated={handleCreated}
        />
      )}
    </div>
  );
}

/* ---- Gear popover — type-aware plot fields ---- */

function PlotFieldsPopover({ meta, onFieldChange, onClose }: {
  meta: PlotMeta;
  onFieldChange: (field: string, value: string) => Promise<void>;
  onClose: () => void;
}) {
  const [currentType, setCurrentType] = useState(meta.plotType || 'LineChart');
  const [saving, setSaving] = useState<string | null>(null);
  const [saved, setSaved] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fields = fieldsForType(currentType);

  const [drafts, setDrafts] = useState<Record<string, string>>(() => {
    const d: Record<string, string> = {};
    // Initialize from all possible fields
    for (const f of [...LINE_CHART_FIELDS, ...BAR_CHART_FIELDS]) {
      d[f.key] = (meta as Record<string, string | undefined>)[f.key] ?? '';
    }
    return d;
  });

  const save = async (key: string) => {
    const orig = (meta as Record<string, string | undefined>)[key] ?? '';
    if (drafts[key] === orig) return;
    setSaving(key);
    setError(null);
    try {
      await onFieldChange(key, drafts[key]);
      setSaved(key);
      setTimeout(() => setSaved(prev => prev === key ? null : prev), 1500);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Save failed');
    }
    setSaving(null);
  };

  const handleTypeChange = async (newType: string) => {
    if (newType === currentType) return;
    setSaving('plot_type');
    setError(null);
    try {
      await onFieldChange('plot_type', newType);
      setCurrentType(newType);
      setSaved('plot_type');
      setTimeout(() => setSaved(prev => prev === 'plot_type' ? null : prev), 1500);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to change type');
    }
    setSaving(null);
  };

  return (
    <div className="plot-popover" onClick={e => e.stopPropagation()}>
      <div className="plot-popover-header">
        <span>Plot Settings</span>
        <span className="plot-popover-varname">{meta.varName}</span>
        <button className="plot-popover-close" onClick={onClose}>&times;</button>
      </div>
      <div className="plot-popover-body">
        {/* Plot type selector */}
        <div className="plot-popover-row">
          <label className="plot-popover-label">Type</label>
          <div className="plot-popover-input-wrap">
            <select
              className="ric-edit-control ric-edit-select"
              value={currentType}
              onChange={e => handleTypeChange(e.target.value)}
              disabled={saving === 'plot_type'}
            >
              {PLOT_TYPES.map(pt => (
                <option key={pt.value} value={pt.value}>{pt.label}</option>
              ))}
            </select>
            {saving === 'plot_type' && <span className="plot-popover-status saving">...</span>}
            {saved === 'plot_type' && <span className="plot-popover-status saved">ok</span>}
          </div>
        </div>
        {/* Type-specific fields */}
        {fields.map(f => (
          <div className="plot-popover-row" key={f.key}>
            <label className="plot-popover-label">{f.label}</label>
            <div className="plot-popover-input-wrap">
              <input
                className="ric-edit-control ric-edit-input"
                value={drafts[f.key]}
                placeholder={f.placeholder}
                onChange={e => setDrafts(d => ({ ...d, [f.key]: e.target.value }))}
                onBlur={() => save(f.key)}
                onKeyDown={e => { if (e.key === 'Enter') save(f.key); }}
                disabled={saving === f.key}
              />
              {saving === f.key && <span className="plot-popover-status saving">...</span>}
              {saved === f.key && <span className="plot-popover-status saved">ok</span>}
            </div>
          </div>
        ))}
        {error && <div className="plot-popover-error">{error}</div>}
      </div>
    </div>
  );
}

/* ---- Add plot popover — type selection first, then auto-populated fields ---- */

function AddPlotPopover({ req, onClose, onCreated }: {
  req: RequirementData;
  onClose: () => void;
  onCreated: () => void;
}) {
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSelectType = async (plotType: string) => {
    if (!req.sourceFile || !req.varName) return;
    setCreating(true);
    setError(null);
    const defaults = defaultsForType(req, plotType);
    const plotVarName = `plot_${req.varName || 'new'}`;
    try {
      await createPlot({
        source_file: req.sourceFile,
        req_var_name: req.varName,
        plot_var_name: plotVarName,
        plot_type: plotType,
        fields: defaults,
      });
      onCreated();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Create failed');
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="plot-popover" onClick={e => e.stopPropagation()}>
      <div className="plot-popover-header">
        <span>New Plot</span>
        <button className="plot-popover-close" onClick={onClose}>&times;</button>
      </div>
      <div className="plot-popover-body">
        {PLOT_TYPES.map(pt => (
          <button
            key={pt.value}
            className="plot-type-btn"
            onClick={() => handleSelectType(pt.value)}
            disabled={creating}
          >
            {pt.value === 'LineChart' ? <LineChartIcon /> : <BarChartIcon />}
            <span>{pt.label}</span>
          </button>
        ))}
        {error && <div className="plot-popover-error">{error}</div>}
      </div>
    </div>
  );
}

/* ---- SVG Icons ---- */

function GearIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  );
}

function PlusIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  );
}

function LineChartIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
    </svg>
  );
}

function BarChartIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="20" x2="18" y2="10" />
      <line x1="12" y1="20" x2="12" y2="4" />
      <line x1="6" y1="20" x2="6" y2="14" />
    </svg>
  );
}
