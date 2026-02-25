import { useRef, useEffect, useState, useMemo, useCallback } from 'react';
import type { RequirementData, FilterType, SimStatData } from './requirements/types';
import { formatEng, formatBuildTime, parseLimitExpr, reEvalPassFail, measureTran, parseValueWithUnit, goToSource } from './requirements/helpers';
import { renderSpecAtSize, renderTransientPlot, renderDCPlot, renderBodePlot, renderSweepPlot, purgePlot, injectLimitShapes, applyPlotFieldToSpec } from './requirements/charts';
import { EditableField, MEASUREMENT_OPTIONS, CAPTURE_OPTIONS } from './requirements/EditableField';
import { updateRequirement, rerunSimulation, rerunSingleSimulation } from './requirements/api';
import { PlotToolbar, GoToSourceIcon } from './requirements/PlotToolbar';

interface RequirementsAllPageProps {
  requirements: RequirementData[];
  buildTime: string;
  simStats?: SimStatData[];
}

const FILTER_LABELS: Record<FilterType, string> = {
  all: 'All',
  pass: 'Pass',
  fail: 'Fail',
  dc: 'DC',
  transient: 'Tran',
  ac: 'AC',
};

/* ------------------------------------------------------------------ */
/*  Simulation config rows — shared between detail and all pages       */
/* ------------------------------------------------------------------ */

function SimConfigFields({
  req, canEdit, onFieldChange, buildTime,
}: {
  req: RequirementData;
  canEdit: boolean;
  onFieldChange: (field: string, value: string) => Promise<void>;
  buildTime: string;
}) {
  const isTransient = req.capture === 'transient';
  const isAC = req.capture === 'ac';
  const hasSweep = !!(req.sweepPoints && req.sweepPoints.length > 0);

  return (
    <>
      {/* Sweep config */}
      {hasSweep && (
        <>
          {req.sweepParamName && (
            <div className="ric-row">
              <span className="ric-label">Parameter</span>
              <span className="ric-value">{req.sweepParamName}{req.sweepParamUnit ? ` (${req.sweepParamUnit})` : ''}</span>
            </div>
          )}
          <div className="ric-row">
            <span className="ric-label">Sweep values</span>
            <EditableField
              value={req.sweepParamValues ?? req.sweepPoints!.map(sp => sp.paramValue).join(',')}
              className="ric-value"
              enabled={canEdit}
              onSave={v => onFieldChange('param_values', v)}
            />
          </div>
        </>
      )}

      {/* Transient fields */}
      {isTransient && (
        <>
          {(req.tranStart != null && req.tranStart !== 0) && (
            <div className="ric-row">
              <span className="ric-label">Start</span>
              <EditableField
                value={String(req.tranStart)}
                displayValue={formatEng(req.tranStart, 's')}
                className="ric-value"
                enabled={canEdit}
                onSave={v => onFieldChange('tran_start', v)}
              />
            </div>
          )}
          {req.tranStop != null && (
            <div className="ric-row">
              <span className="ric-label">Stop</span>
              <EditableField
                value={String(req.tranStop)}
                displayValue={formatEng(req.tranStop, 's')}
                className="ric-value"
                enabled={canEdit}
                onSave={v => onFieldChange('tran_stop', v)}
              />
            </div>
          )}
          {req.tranStep != null && (
            <div className="ric-row">
              <span className="ric-label">Step</span>
              <EditableField
                value={String(req.tranStep)}
                displayValue={formatEng(req.tranStep, 's')}
                className="ric-value"
                enabled={canEdit}
                onSave={v => onFieldChange('tran_step', v)}
              />
            </div>
          )}
          {req.settlingTolerance != null && (
            <div className="ric-row">
              <span className="ric-label">Settling tol.</span>
              <EditableField
                value={String(req.settlingTolerance)}
                displayValue={`${(req.settlingTolerance * 100).toFixed(1)}%`}
                className="ric-value"
                enabled={canEdit}
                onSave={v => onFieldChange('settling_tolerance', v)}
              />
            </div>
          )}
        </>
      )}

      {/* AC fields */}
      {isAC && (
        <>
          {req.acStartFreq != null && (
            <div className="ric-row">
              <span className="ric-label">Start freq</span>
              <EditableField
                value={String(req.acStartFreq)}
                displayValue={formatEng(req.acStartFreq, 'Hz')}
                className="ric-value"
                enabled={canEdit}
                onSave={v => onFieldChange('ac_start_freq', v)}
              />
            </div>
          )}
          {req.acStopFreq != null && (
            <div className="ric-row">
              <span className="ric-label">Stop freq</span>
              <EditableField
                value={String(req.acStopFreq)}
                displayValue={formatEng(req.acStopFreq, 'Hz')}
                className="ric-value"
                enabled={canEdit}
                onSave={v => onFieldChange('ac_stop_freq', v)}
              />
            </div>
          )}
          {req.acPointsPerDec != null && (
            <div className="ric-row">
              <span className="ric-label">Pts/decade</span>
              <EditableField
                value={String(req.acPointsPerDec)}
                className="ric-value"
                enabled={canEdit}
                onSave={v => onFieldChange('ac_points_per_dec', v)}
              />
            </div>
          )}
          {req.acSourceName != null && (
            <div className="ric-row">
              <span className="ric-label">AC source</span>
              <EditableField
                value={req.acSourceName}
                className="ric-value"
                enabled={canEdit}
                onSave={v => onFieldChange('ac_source_name', v)}
              />
            </div>
          )}
          {req.acMeasureFreq != null && (
            <div className="ric-row">
              <span className="ric-label">Meas. freq</span>
              <EditableField
                value={String(req.acMeasureFreq)}
                displayValue={formatEng(req.acMeasureFreq, 'Hz')}
                className="ric-value"
                enabled={canEdit}
                onSave={v => onFieldChange('ac_measure_freq', v)}
              />
            </div>
          )}
          {req.acRefNet != null && (
            <div className="ric-row">
              <span className="ric-label">Ref net</span>
              <EditableField
                value={req.acRefNet}
                className="ric-value"
                enabled={canEdit}
                onSave={v => onFieldChange('ac_ref_net', v)}
              />
            </div>
          )}
        </>
      )}

      {/* SPICE source override */}
      {(req.sourceSpec || req.spice) && (
        <div className="ric-row ric-row-top">
          <span className="ric-label">Spice</span>
          <EditableField value={req.sourceSpec || req.spice || ''} className="ric-value" enabled={canEdit} multiline onSave={v => onFieldChange('spice', v)} />
        </div>
      )}
      {/* Extra SPICE */}
      {req.extraSpice && req.extraSpice.length > 0 && (
        <div className="ric-row">
          <span className="ric-label">Extra SPICE</span>
          <span className="ric-value mono-muted">{req.extraSpice.join(' | ')}</span>
        </div>
      )}
      {/* Common fields */}
      {req.contextNets && req.contextNets.length > 0 && (
        <div className="ric-row">
          <span className="ric-label">Context</span>
          <span className="ric-value">{req.contextNets.join(', ')}</span>
        </div>
      )}
      {req.simulationName && (
        <div className="ric-row">
          <span className="ric-label">Simulation</span>
          <span className="ric-value-with-action">
            <span className="ric-value">{req.simulationName}</span>
            {req.sourceFile && req.simulationLine && (
              <button className="ric-goto-btn" onClick={() => goToSource(req.sourceFile, req.simulationLine)} title="Go to simulation definition">
                <GoToSourceIcon />
              </button>
            )}
          </span>
        </div>
      )}
      {req.timeSeries && (
        <div className="ric-row">
          <span className="ric-label">Points</span>
          <span className="ric-value mono-muted">{req.timeSeries.time.length}</span>
        </div>
      )}
      {buildTime && (
        <div className="ric-row">
          <span className="ric-label">Built</span>
          <span className="ric-value mono-muted">{formatBuildTime(buildTime)}</span>
        </div>
      )}
    </>
  );
}

/* ------------------------------------------------------------------ */
/*  Single requirement row: card (left) + plot(s) (right)             */
/* ------------------------------------------------------------------ */

const PLOT_FIELDS = new Set([
  'title', 'x', 'y', 'y_secondary', 'color', 'plot_limits', 'simulation',
  'required_plot', 'supplementary_plot',
]);

/** Find signal data in timeSeries by trying various key formats */
function _findSignal(signals: Record<string, number[]>, netKey: string, rawNet: string): number[] | null {
  if (signals[netKey]) return signals[netKey];
  // Try with underscores instead of dots
  const underscored = netKey.replace(/\./g, '_');
  if (signals[underscored]) return signals[underscored];
  // Try just the raw net name with v() wrapper
  const vRaw = `v(${rawNet.replace(/\./g, '_')})`;
  if (signals[vRaw]) return signals[vRaw];
  // Search for a key containing the net name
  const needle = rawNet.replace(/\./g, '_').toLowerCase();
  for (const [k, v] of Object.entries(signals)) {
    if (k.toLowerCase().includes(needle)) return v;
  }
  return null;
}

function RequirementRow({ req: initialReq, buildTime, layout }: { req: RequirementData; buildTime: string; layout: LayoutMode }) {
  const outerRef = useRef<HTMLDivElement>(null);
  const plotRefs = useRef<(HTMLDivElement | null)[]>([]);
  const containerRefs = useRef<({ current: HTMLDivElement | null })[]>([]);
  const [req, setReq] = useState(initialReq);
  const [stale, setStale] = useState(false);
  const [rerunning, setRerunning] = useState(false);
  const [, setPlotDim] = useState<{ width: number; height: number } | null>(null);
  const [collapsed, setCollapsed] = useState(false);
  // Track limit version to trigger plot re-renders on limit changes
  const [limitVersion, setLimitVersion] = useState(0);

  // Sync from fresh server data when build time changes (e.g. after WebSocket refresh)
  const prevBuildTime = useRef(buildTime);
  useEffect(() => {
    if (buildTime !== prevBuildTime.current) {
      prevBuildTime.current = buildTime;
      setReq(initialReq);
      setStale(false);
      setLimitVersion(v => v + 1);
    }
  }, [buildTime, initialReq]);
  const canEdit = !!(req.sourceFile && req.varName);
  const hasResult = req.actual !== null && isFinite(req.actual);
  const plotCount = req.plotSpecs?.length || 1;

  /** Render a single requirement into one of the per-plot ref divs */
  const renderSinglePlot = useCallback((el: HTMLDivElement, r: RequirementData, dim: { width: number; height: number }, specIndex: number) => {
    if (r.plotSpecs && r.plotSpecs[specIndex]) {
      const specWithLimits = injectLimitShapes(r.plotSpecs[specIndex], r);
      renderSpecAtSize(el, specWithLimits, dim.width, dim.height);
    } else if (specIndex === 0) {
      if (r.sweepPoints && r.sweepPoints.length > 0) renderSweepPlot(el, r, dim);
      else if (r.frequencySeries) renderBodePlot(el, r, dim);
      else if (r.timeSeries) renderTransientPlot(el, r, dim);
      else renderDCPlot(el, r, dim);
    }
  }, []);

  // Map timing fields from requirement names to simulation names
  const SIM_FIELD_MAP: Record<string, string> = {
    tran_start: 'time_start', tran_stop: 'time_stop', tran_step: 'time_step',
  };
  const SIM_FIELDS = new Set(['tran_start', 'tran_stop', 'tran_step', 'param_values']);

  const handleFieldChange = useCallback(async (field: string, value: string) => {
    if (!req.sourceFile || !req.varName) return;
    // Timing + sweep fields target the simulation node, not the requirement
    const isSimField = SIM_FIELDS.has(field);
    const varName = isSimField && req.simulationName
      ? req.simulationName : req.varName;
    const writeField = SIM_FIELD_MAP[field] || field;
    await updateRequirement({
      source_file: req.sourceFile,
      var_name: varName,
      updates: { [writeField]: value },
    });

    if (field === 'limit_expr') {
      const parsed = parseLimitExpr(value);
      if (parsed) {
        setReq(prev => {
          const pf = reEvalPassFail(prev.actual, parsed.min, parsed.max, prev.sweepPoints);
          return { ...prev, minVal: parsed.min, maxVal: parsed.max, limitExpr: value, ...pf };
        });
        setLimitVersion(v => v + 1);
      }
    } else if (field === 'min_val') {
      const num = parseFloat(value);
      if (isFinite(num)) {
        setReq(prev => {
          const pf = reEvalPassFail(prev.actual, num, prev.maxVal, prev.sweepPoints);
          return { ...prev, minVal: num, ...pf };
        });
        setLimitVersion(v => v + 1);
      }
    } else if (field === 'max_val') {
      const num = parseFloat(value);
      if (isFinite(num)) {
        setReq(prev => {
          const pf = reEvalPassFail(prev.actual, prev.minVal, num, prev.sweepPoints);
          return { ...prev, maxVal: num, ...pf };
        });
        setLimitVersion(v => v + 1);
      }
    } else if (field === 'measurement') {
      // Client-side re-measurement from existing timeSeries data
      setReq(prev => {
        const updated = { ...prev, measurement: value };
        if (prev.timeSeries) {
          const netKey = prev.net.startsWith('v(') || prev.net.startsWith('i(') ? prev.net : `v(${prev.net})`;
          const sigData = _findSignal(prev.timeSeries.signals, netKey, prev.net);
          if (sigData) {
            const newActual = measureTran(value, sigData, prev.timeSeries.time, {
              settlingTolerance: prev.settlingTolerance,
              minVal: prev.minVal, maxVal: prev.maxVal,
            });
            updated.actual = isFinite(newActual) ? newActual : null;
            const pf = reEvalPassFail(updated.actual, prev.minVal, prev.maxVal, prev.sweepPoints);
            Object.assign(updated, pf);
          }
        }
        return updated;
      });
      setLimitVersion(v => v + 1);
    } else if (field === 'tran_start' || field === 'tran_stop' || field === 'tran_step') {
      // Parse timing value and update local state so single rerun uses new values
      const parsed = parseValueWithUnit(value);
      if (parsed !== null) {
        const key = field === 'tran_start' ? 'tranStart' : field === 'tran_stop' ? 'tranStop' : 'tranStep';
        setReq(prev => ({ ...prev, [key]: parsed }));
      }
      setStale(true);
    } else if (field === 'param_values') {
      setReq(prev => ({ ...prev, sweepParamValues: value }));
      setStale(true);
    } else if (!PLOT_FIELDS.has(field)) {
      setStale(true);
    }
  }, [req.sourceFile, req.varName]);

  const handleRerun = useCallback(async () => {
    setRerunning(true);
    try {
      const isSweep = req.sweepPoints && req.sweepPoints.length > 0;
      const canSingleRerun = !isSweep && req.netlistPath && req.capture === 'transient'
        && (req.spice || req.sourceSpec);
      if (canSingleRerun) {
        const result = await rerunSingleSimulation({
          netlist_path: req.netlistPath!,
          spice_sources: req.spice || req.sourceSpec || '',
          sim_type: 'transient',
          net: req.net,
          measurement: req.measurement,
          tran_start: req.tranStart ?? 0,
          tran_stop: req.tranStop ?? 100e-6,
          tran_step: req.tranStep ?? 1e-9,
          settling_tolerance: req.settlingTolerance ?? null,
          context_nets: req.contextNets || [],
          min_val: req.minVal,
          max_val: req.maxVal,
          dut_name: req.dutName ?? null,
          dut_params: req.dutParams ?? null,
          remove_elements: req.removeElements ?? null,
        });
        setReq(prev => ({
          ...prev,
          actual: result.actual,
          passed: result.passed,
          timeSeries: result.timeSeries,
        }));
        setLimitVersion(v => v + 1);
      } else {
        await rerunSimulation();
      }
      setStale(false);
    } catch (err) {
      console.error('Rerun failed:', err);
      // Fall back to full build on single-sim failure
      try {
        await rerunSimulation();
        setStale(false);
      } catch {
        // Both failed — user should rebuild manually
      }
    }
    finally { setRerunning(false); }
  }, [req]);

  const handlePlotFieldChange = useCallback((specIdx: number, field: string, value: string) => {
    setReq(prev => {
      if (!prev.plotSpecs || !prev.plotSpecs[specIdx]) return prev;
      const newSpecs = [...prev.plotSpecs];
      newSpecs[specIdx] = applyPlotFieldToSpec(newSpecs[specIdx], field, value, prev.timeSeries);
      return { ...prev, plotSpecs: newSpecs };
    });
    setLimitVersion(v => v + 1);
  }, []);

  const handlePlotDirty = useCallback(() => {
    setStale(true);
  }, []);

  // Render plots with fixed dimensions matching CSS grid column widths
  // Grid: 400px cells, List: 800px cells — padding 12px each side = 24px
  useEffect(() => {
    const plotW = layout === 'list' ? 776 : 376;
    const plotH = Math.round(plotW * 9 / 16);
    const dim = { width: plotW, height: plotH };
    setPlotDim(dim);

    for (let i = 0; i < plotCount; i++) {
      const el = plotRefs.current[i];
      if (el) renderSinglePlot(el, req, dim, i);
    }

    return () => {
      for (const ref of plotRefs.current) {
        if (ref) purgePlot(ref).catch(() => {});
      }
    };
  }, [req.id, plotCount, limitVersion, renderSinglePlot, layout, collapsed]);

  return (
    <div className="rall-row">
      {/* Full-width header */}
      <div className="ric-header rall-row-header">
        <button className="rall-collapse-btn" onClick={() => setCollapsed(c => !c)} title={collapsed ? 'Expand' : 'Collapse'}>
          <svg width="10" height="10" viewBox="0 0 10 10" className={`chevron ${collapsed ? '' : 'open'}`}>
            <path d="M2 3.5L5 6.5L8 3.5" stroke="currentColor" strokeWidth="1.5" fill="none" />
          </svg>
        </button>
        <div className="ric-name">
          <EditableField value={req.name} className="ric-name-edit" enabled={canEdit} onSave={v => handleFieldChange('req_name', v)} />
        </div>
        {req.sourceFile && req.sourceLine && (
          <button className="ric-goto-btn" onClick={() => goToSource(req.sourceFile, req.sourceLine)} title="Go to requirement definition">
            <GoToSourceIcon />
          </button>
        )}
        <div className={`ric-badge ${hasResult ? (req.passed ? 'pass' : 'fail') : 'pending'}`}>
          {hasResult ? (req.passed ? 'PASS' : 'FAIL') : '---'}
        </div>
      </div>

      {/* Collapsible body: card details + plots side by side */}
      {!collapsed && (
        <div className="rall-row-content">
          {/* Card details */}
          <div className="rall-card">
            <div className="ric-body">
              {/* Configuration (includes limit) */}
              <div className="ric-section">
                <div className="ric-section-title">Configuration</div>
                <div className="ric-row">
                  <span className="ric-label">Limit</span>
                  <EditableField
                    value={req.limitExpr ?? `${formatEng(req.minVal, req.unit)} to ${formatEng(req.maxVal, req.unit)}`}
                    className="ric-value"
                    enabled={canEdit}
                    onSave={v => handleFieldChange('limit_expr', v)}
                  />
                </div>
                <div className="ric-row">
                  <span className="ric-label">Net</span>
                  <EditableField
                    value={req.net}
                    displayValue={req.displayNet || req.net}
                    className="ric-value"
                    enabled={canEdit}
                    onSave={v => handleFieldChange('net', v)}
                  />
                </div>
                <div className="ric-row">
                  <span className="ric-label">Capture</span>
                  <EditableField
                    value={req.capture}
                    className="ric-value"
                    enabled={canEdit}
                    options={CAPTURE_OPTIONS}
                    onSave={v => handleFieldChange('capture', v)}
                  />
                </div>
                <div className="ric-row">
                  <span className="ric-label">Measurement</span>
                  <EditableField
                    value={req.measurement}
                    className="ric-value"
                    enabled={canEdit}
                    options={MEASUREMENT_OPTIONS}
                    onSave={v => handleFieldChange('measurement', v)}
                  />
                </div>
              </div>

              {/* Simulation */}
              <div className="ric-section">
                <div className="ric-section-title">Simulation</div>
                <SimConfigFields req={req} canEdit={canEdit} onFieldChange={handleFieldChange} buildTime={buildTime} />
              </div>

              {req.justification && (
                <div className="ric-section">
                  <div className="ric-section-title">Justification</div>
                  <div className="ric-justification-text">{req.justification}</div>
                </div>
              )}

              {/* Stale / Rerun bar */}
              {stale && (
                <div className="ric-section ric-rerun-bar">
                  <span className="ric-dirty">Simulation config changed — rerun to see new results</span>
                  <button className={`ric-rerun-btn ${rerunning ? 'ric-saving' : ''}`} onClick={handleRerun} disabled={rerunning}>
                    {rerunning ? 'Running...' : 'Rerun Simulation'}
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Plots — one toolbar per plot */}
          <div className={`rall-plots${layout === 'list' ? ' rall-plots-list' : ''}`} ref={outerRef}>
            {Array.from({ length: plotCount }, (_, i) => {
              // Ensure a stable ref object exists for each plot container
              if (!containerRefs.current[i]) {
                containerRefs.current[i] = { current: null };
              }
              const cRef = containerRefs.current[i];
              return (
                <div key={i} className="plot-container" ref={el => { cRef.current = el; }}>
                  <div ref={el => { plotRefs.current[i] = el; }} />
                  <PlotToolbar req={req} specIndex={i} onDirty={handlePlotDirty} onPlotFieldChange={handlePlotFieldChange} containerRef={cRef} />
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Collapsible simulation timing bar chart                           */
/* ------------------------------------------------------------------ */

function SimTimingChart({ stats }: { stats: SimStatData[] }) {
  const [open, setOpen] = useState(false);

  if (!stats.length) return null;

  const totalTime = stats.reduce((sum, s) => sum + s.elapsedS, 0);
  const maxTime = stats[0]?.elapsedS ?? 1;

  return (
    <div className="sim-timing">
      <button className="sim-timing-toggle" onClick={() => setOpen(!open)}>
        <svg width="10" height="10" viewBox="0 0 10 10" className={`chevron ${open ? 'open' : ''}`}>
          <path d="M2 3.5L5 6.5L8 3.5" stroke="currentColor" strokeWidth="1.5" fill="none" />
        </svg>
        <span>Simulation Timing</span>
        <span className="sim-timing-total">{totalTime.toFixed(1)}s total</span>
        <span className="sim-timing-count">{stats.length} sim{stats.length !== 1 ? 's' : ''}</span>
      </button>
      {open && (
        <div className="sim-timing-body">
          {stats.map((s, i) => {
            const pct = maxTime > 0 ? (s.elapsedS / maxTime) * 100 : 0;
            const pts = s.dataPoints >= 1e6 ? `${(s.dataPoints / 1e6).toFixed(1)}M` : s.dataPoints >= 1000 ? `${(s.dataPoints / 1000).toFixed(1)}k` : String(s.dataPoints);
            return (
              <div className="sim-timing-row" key={i}>
                <span className="sim-timing-name" title={s.name}>{s.name}</span>
                <div className="sim-timing-bar-track">
                  <div
                    className="sim-timing-bar-fill"
                    style={{ width: `${Math.max(pct, 2)}%` }}
                  />
                </div>
                <span className="sim-timing-value">{s.elapsedS.toFixed(1)}s</span>
                <span className="sim-timing-pts">{pts} pts</span>
                <span className="sim-timing-type">{s.simType.replace(/_/g, ' ')}</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main all-requirements page                                        */
/* ------------------------------------------------------------------ */

type LayoutMode = 'grid' | 'list';

export function RequirementsAllPage({ requirements, buildTime, simStats }: RequirementsAllPageProps) {
  const [filter, setFilter] = useState<FilterType>('all');
  const [search, setSearch] = useState('');
  const [layout, setLayout] = useState<LayoutMode>('grid');

  const sorted = useMemo(
    () => [...requirements].sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true })),
    [requirements],
  );

  const hasResult = (r: RequirementData) => r.actual !== null && isFinite(r.actual);

  const filtered = useMemo(() => {
    let reqs = sorted;
    if (filter === 'pass') reqs = reqs.filter(r => hasResult(r) && r.passed);
    else if (filter === 'fail') reqs = reqs.filter(r => hasResult(r) && !r.passed);
    else if (filter === 'dc') reqs = reqs.filter(r => r.capture === 'dcop');
    else if (filter === 'transient') reqs = reqs.filter(r => r.capture === 'transient');
    else if (filter === 'ac') reqs = reqs.filter(r => r.capture === 'ac');
    if (search.trim()) {
      const q = search.toLowerCase();
      reqs = reqs.filter(r =>
        r.name.toLowerCase().includes(q) ||
        r.net.toLowerCase().includes(q) ||
        r.measurement.toLowerCase().includes(q) ||
        r.id.toLowerCase().includes(q),
      );
    }
    return reqs;
  }, [sorted, filter, search]);

  const passCount = useMemo(() => sorted.filter(r => hasResult(r) && r.passed).length, [sorted]);
  const failCount = useMemo(() => sorted.filter(r => hasResult(r) && !r.passed).length, [sorted]);
  const pendingCount = useMemo(() => sorted.filter(r => !hasResult(r)).length, [sorted]);

  return (
    <div className="rall-root">
      {/* Header */}
      <div className="rall-header">
        <div className="rall-title">
          All Requirements
          <span className="req-sidebar-badge">{sorted.length}</span>
        </div>
        <div className="rall-summary">
          <span className="dot pass" />
          <span>{passCount} passed</span>
          <span className="dot fail" />
          <span>{failCount} failed</span>
          {pendingCount > 0 && (<>
            <span className="dot pending" />
            <span>{pendingCount} pending</span>
          </>)}
        </div>
      </div>

      {/* Filter + search */}
      <div className="rall-toolbar">
        <div className="req-filter-bar" style={{ borderBottom: 'none', padding: 0 }}>
          {(Object.keys(FILTER_LABELS) as FilterType[]).map(f => (
            <button
              key={f}
              className={`req-filter-btn ${filter === f ? 'active' : ''}`}
              onClick={() => setFilter(f)}
            >
              {FILTER_LABELS[f]}
            </button>
          ))}
        </div>
        <div className="rall-search">
          <input
            className="req-search-input"
            type="text"
            placeholder="Search requirements..."
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
          {search && (
            <button className="req-search-clear" onClick={() => setSearch('')} aria-label="Clear search">
              &times;
            </button>
          )}
        </div>
        <div className="rall-layout-toggle">
          <button
            className={`rall-layout-btn${layout === 'grid' ? ' active' : ''}`}
            onClick={() => setLayout('grid')}
            title="Grid layout (2 columns)"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="3" width="7" height="7" />
              <rect x="14" y="3" width="7" height="7" />
              <rect x="3" y="14" width="7" height="7" />
              <rect x="14" y="14" width="7" height="7" />
            </svg>
          </button>
          <button
            className={`rall-layout-btn${layout === 'list' ? ' active' : ''}`}
            onClick={() => setLayout('list')}
            title="List layout (1 column)"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="3" y1="6" x2="21" y2="6" />
              <line x1="3" y1="12" x2="21" y2="12" />
              <line x1="3" y1="18" x2="21" y2="18" />
            </svg>
          </button>
        </div>
      </div>

      {/* Simulation timing */}
      {simStats && simStats.length > 0 && <SimTimingChart stats={simStats} />}

      {/* Requirement rows */}
      <div className="rall-body">
        {filtered.map(req => (
          <RequirementRow key={req.id} req={req} buildTime={buildTime} layout={layout} />
        ))}
        {filtered.length === 0 && (
          <div className="req-empty-state" style={{ padding: '40px' }}>
            <div className="req-empty-state-desc">No requirements match this filter</div>
          </div>
        )}
      </div>
    </div>
  );
}
