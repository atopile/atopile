import { useRef, useEffect, useState, useMemo, useCallback } from 'react';
import type { RequirementData, FilterType, SimStatData } from './requirements/types';
import { formatEng, formatBuildTime, parseLimitExpr, reEvalPassFail } from './requirements/helpers';
import { renderSpecAtSize, renderTransientPlot, renderDCPlot, renderBodePlot, renderSweepPlot, purgePlot, injectLimitShapes, applyPlotFieldToSpec } from './requirements/charts';
import { EditableField, MEASUREMENT_OPTIONS, CAPTURE_OPTIONS } from './requirements/EditableField';
import { updateRequirement, rerunSimulation, rerunSingleSimulation } from './requirements/api';
import { PlotToolbar } from './requirements/PlotToolbar';

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
      {/* Sweep config (read-only) */}
      {hasSweep && (
        <>
          {req.sweepParamName && (
            <div className="ric-row">
              <span className="ric-label">Parameter</span>
              <span className="ric-value">{req.sweepParamName}{req.sweepParamUnit ? ` (${req.sweepParamUnit})` : ''}</span>
            </div>
          )}
          <div className="ric-row">
            <span className="ric-label">Sweep points</span>
            <span className="ric-value">{req.sweepPoints!.length}</span>
          </div>
          <div className="ric-row">
            <span className="ric-label">Range</span>
            <span className="ric-value mono-muted">
              {req.sweepPoints![0].paramValue} — {req.sweepPoints![req.sweepPoints!.length - 1].paramValue}
            </span>
          </div>
        </>
      )}

      {/* Transient fields */}
      {isTransient && !hasSweep && (
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
      {req.simulationName && <div className="ric-row"><span className="ric-label">Simulation</span><span className="ric-value">{req.simulationName}</span></div>}
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

function RequirementRow({ req: initialReq, buildTime }: { req: RequirementData; buildTime: string }) {
  const outerRef = useRef<HTMLDivElement>(null);
  const plotRefs = useRef<(HTMLDivElement | null)[]>([]);
  const [req, setReq] = useState(initialReq);
  const [stale, setStale] = useState(false);
  const [rerunning, setRerunning] = useState(false);
  const [, setPlotDim] = useState<{ width: number; height: number } | null>(null);
  // Track limit version to trigger plot re-renders on limit changes
  const [limitVersion, setLimitVersion] = useState(0);
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

  const handleFieldChange = useCallback(async (field: string, value: string) => {
    if (!req.sourceFile || !req.varName) return;
    await updateRequirement({
      source_file: req.sourceFile,
      var_name: req.varName,
      updates: { [field]: value },
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
    } else if (!PLOT_FIELDS.has(field)) {
      setStale(true);
    }
  }, [req.sourceFile, req.varName]);

  const handleRerun = useCallback(async () => {
    setRerunning(true);
    try {
      if (req.netlistPath && req.capture === 'transient') {
        const result = await rerunSingleSimulation({
          netlist_path: req.netlistPath,
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
    } catch { /* */ }
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

  // Render plots — outerRef gets height from CSS grid stretch
  // Re-render when limitVersion changes (limit edits)
  useEffect(() => {
    const outer = outerRef.current;
    if (!outer) return;

    const h = outer.clientHeight;
    const w = outer.clientWidth;
    if (!h || !w) return;

    // All plots same size: 2-column layout width regardless of plot count
    const gap = 8;
    const plotW = Math.floor((w - gap) / 2);
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
  }, [req.id, plotCount, limitVersion, renderSinglePlot]);

  return (
    <div className="rall-row">
      {/* Card */}
      <div className="rall-card">
        <div className="req-info-card-outer">
          <div className="ric-header">
            <div className="ric-name">
              <EditableField value={req.name} className="ric-name-edit" enabled={canEdit} onSave={v => handleFieldChange('req_name', v)} />
            </div>
            <div className={`ric-badge ${hasResult ? (req.passed ? 'pass' : 'fail') : 'pending'}`}>
              {hasResult ? (req.passed ? 'PASS' : 'FAIL') : '---'}
            </div>
          </div>
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
      </div>

      {/* Plots — one toolbar per plot */}
      <div className="rall-plots" ref={outerRef}>
        {Array.from({ length: plotCount }, (_, i) => (
          <div key={i} className="plot-container">
            <div ref={el => { plotRefs.current[i] = el; }} />
            <PlotToolbar req={req} specIndex={i} onDirty={handlePlotDirty} onPlotFieldChange={handlePlotFieldChange} />
          </div>
        ))}
      </div>
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

export function RequirementsAllPage({ requirements, buildTime, simStats }: RequirementsAllPageProps) {
  const [filter, setFilter] = useState<FilterType>('all');
  const [search, setSearch] = useState('');

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
      </div>

      {/* Simulation timing */}
      {simStats && simStats.length > 0 && <SimTimingChart stats={simStats} />}

      {/* Requirement rows */}
      <div className="rall-body">
        {filtered.map(req => (
          <RequirementRow key={req.id} req={req} buildTime={buildTime} />
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
