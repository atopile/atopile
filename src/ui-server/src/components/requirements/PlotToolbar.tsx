import { useState, useCallback, useEffect, useRef } from 'react';
import { ExternalLink } from 'lucide-react';
import type { PlotMeta, RequirementData } from './types';
import { updateRequirement } from './api';
import { goToSource } from './helpers';

interface PlotToolbarProps {
  req: RequirementData;
  specIndex: number;
  onDirty: () => void;
  onPlotFieldChange?: (specIndex: number, field: string, value: string) => void;
  /** Ref to the plot container element for fullscreen toggling */
  containerRef?: { current: HTMLDivElement | null };
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

/** Relayout the Plotly chart inside a container to an explicit width/height */
function relayoutPlotly(container: HTMLElement, width: number, height: number): void {
  requestAnimationFrame(() => {
    const plotEl = container.querySelector('.js-plotly-plot') as HTMLElement | null;
    if (plotEl && (window as unknown as Record<string, unknown>).Plotly) {
      const Plotly = (window as unknown as Record<string, unknown>).Plotly as {
        relayout: (el: HTMLElement, update: { width: number; height: number }) => void;
      };
      Plotly.relayout(plotEl, { width, height });
    }
  });
}

/** Compute the largest 16:9 box that fits within the given bounds (with padding) */
function fitAspectRatio(viewW: number, viewH: number, padding: number): { width: number; height: number } {
  const maxW = viewW - padding * 2;
  const maxH = viewH - padding * 2;
  let w = maxW;
  let h = Math.round(w * 9 / 16);
  if (h > maxH) {
    h = maxH;
    w = Math.round(h * 16 / 9);
  }
  return { width: w, height: h };
}

export function PlotToolbar({ req, specIndex, onDirty, onPlotFieldChange, containerRef }: PlotToolbarProps) {
  const [gearOpen, setGearOpen] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const toolbarRef = useRef<HTMLDivElement>(null);
  // Remember original plot size so we can restore on exit
  const origSize = useRef<{ width: number; height: number } | null>(null);

  const spec = req.plotSpecs?.[specIndex];
  const meta = spec?.meta;
  const canEditPlot = !!(req.sourceFile && meta?.varName);

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

  /** Enter fullscreen: scale plot to fill viewport at 16:9 */
  const enterFullscreen = useCallback(() => {
    const el = containerRef?.current;
    if (!el) return;
    // Capture current plot size for restore
    const plotEl = el.querySelector('.js-plotly-plot') as HTMLElement | null;
    if (plotEl) {
      origSize.current = { width: plotEl.clientWidth, height: plotEl.clientHeight };
    }
    setIsFullscreen(true);
    el.classList.add('plot-fullscreen');
    const dim = fitAspectRatio(window.innerWidth, window.innerHeight, 32);
    relayoutPlotly(el, dim.width, dim.height);
  }, [containerRef]);

  /** Exit fullscreen: restore original plot size */
  const exitFullscreen = useCallback(() => {
    const el = containerRef?.current;
    if (!el) return;
    setIsFullscreen(false);
    el.classList.remove('plot-fullscreen');
    if (origSize.current) {
      relayoutPlotly(el, origSize.current.width, origSize.current.height);
    }
  }, [containerRef]);

  const toggleFullscreen = useCallback(() => {
    if (isFullscreen) exitFullscreen();
    else enterFullscreen();
  }, [isFullscreen, enterFullscreen, exitFullscreen]);

  // Close fullscreen on Escape
  useEffect(() => {
    if (!isFullscreen) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') exitFullscreen();
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [isFullscreen, exitFullscreen]);

  // Close popovers on Escape or click outside
  useEffect(() => {
    if (!gearOpen) return;
    const close = () => { setGearOpen(false); };
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
  }, [gearOpen]);

  return (
    <div className="plot-toolbar" ref={toolbarRef}>
      <div className="plot-toolbar-icons">
        {meta?.sourceLine && req.sourceFile && (
          <button
            className="plot-toolbar-btn"
            onClick={() => goToSource(req.sourceFile, meta!.sourceLine)}
            title="Go to plot definition"
          >
            <GoToSourceIcon />
          </button>
        )}
        <button
          className={`plot-toolbar-btn${!canEditPlot ? ' plot-toolbar-btn-disabled' : ''}`}
          onClick={() => { if (canEditPlot) { setGearOpen(!gearOpen); } }}
          title={canEditPlot ? 'Plot settings' : 'No plot to configure'}
        >
          <GearIcon />
        </button>
        {containerRef && (
          <button
            className="plot-toolbar-btn"
            onClick={toggleFullscreen}
            title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}
          >
            {isFullscreen ? <ExitFullscreenIcon /> : <FullscreenIcon />}
          </button>
        )}
      </div>

      {gearOpen && canEditPlot && (
        <PlotFieldsPopover
          meta={meta!}
          onFieldChange={handlePlotFieldChange}
          onClose={() => setGearOpen(false)}
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

/* ---- SVG Icons ---- */

function GearIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  );
}

function FullscreenIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="15 3 21 3 21 9" />
      <polyline points="9 21 3 21 3 15" />
      <line x1="21" y1="3" x2="14" y2="10" />
      <line x1="3" y1="21" x2="10" y2="14" />
    </svg>
  );
}

function ExitFullscreenIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="4 14 10 14 10 20" />
      <polyline points="20 10 14 10 14 4" />
      <line x1="14" y1="10" x2="21" y2="3" />
      <line x1="3" y1="21" x2="10" y2="14" />
    </svg>
  );
}

/** Re-export lucide ExternalLink as GoToSourceIcon for consistency */
export function GoToSourceIcon() {
  return <ExternalLink size={12} />;
}
