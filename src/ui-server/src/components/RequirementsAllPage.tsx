import { useRef, useEffect, useState, useMemo, useCallback } from 'react';
import type { RequirementData, FilterType, SimStatData } from './requirements/types';
import { formatEng, computeMargin, marginLevel, formatBuildTime } from './requirements/helpers';
import { renderRequirementPlot, rerenderWithLimits, purgePlot } from './requirements/charts';
import { EditableField, MEASUREMENT_OPTIONS, CAPTURE_OPTIONS } from './requirements/EditableField';
import { updateRequirement, rerunSimulation } from './requirements/api';
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
          <div className="ric-row">
            <span className="ric-label">Start</span>
            <EditableField
              value={String(req.tranStart ?? 0)}
              displayValue={formatEng(req.tranStart ?? 0, 's')}
              className="ric-value"
              enabled={canEdit}
              onSave={v => onFieldChange('tran_start', v)}
            />
          </div>
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

      {/* Common fields */}
      {req.contextNets && req.contextNets.length > 0 && (
        <div className="ric-row">
          <span className="ric-label">Context</span>
          <span className="ric-value">{req.contextNets.join(', ')}</span>
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

const LIMIT_FIELDS = new Set(['min_val', 'max_val']);

function RequirementRow({ req: initialReq, buildTime }: { req: RequirementData; buildTime: string }) {
  const plotsRef = useRef<HTMLDivElement>(null);
  const [req, setReq] = useState(initialReq);
  const [stale, setStale] = useState(false);
  const [rerunning, setRerunning] = useState(false);
  const [plotDim, setPlotDim] = useState<{ width: number; height: number } | null>(null);
  const canEdit = !!(req.sourceFile && req.varName);

  const handleFieldChange = useCallback(async (field: string, value: string) => {
    if (!req.sourceFile || !req.varName) return;
    await updateRequirement({
      source_file: req.sourceFile,
      var_name: req.varName,
      updates: { [field]: value },
    });

    if (LIMIT_FIELDS.has(field)) {
      const numVal = parseFloat(value);
      if (!isNaN(numVal)) {
        const newMin = field === 'min_val' ? numVal : req.minVal;
        const newMax = field === 'max_val' ? numVal : req.maxVal;
        const newPassed = req.actual !== null && isFinite(req.actual) && newMin <= req.actual && req.actual <= newMax;
        const updated = { ...req, minVal: newMin, maxVal: newMax, passed: newPassed };
        setReq(updated);
        const container = plotsRef.current;
        if (container && plotDim) {
          await rerenderWithLimits(container, updated, newMin, newMax, plotDim);
        }
      }
    } else {
      setStale(true);
    }
  }, [req, plotDim]);

  const handleRerun = useCallback(async () => {
    setRerunning(true);
    try { await rerunSimulation(); setStale(false); } catch { /* */ }
    finally { setRerunning(false); }
  }, []);

  const handlePlotDirty = useCallback(() => { setStale(true); }, []);

  // Render plots — container is stretched by CSS grid to match card row height
  useEffect(() => {
    const container = plotsRef.current;
    if (!container) return;

    // Reset layout from any previous render
    container.style.display = '';
    container.style.gridTemplateColumns = '';
    container.style.gap = '';

    // Container dimensions are set by the CSS grid row (= card height)
    const w = container.clientWidth;
    const h = container.clientHeight;
    if (!w || !h) return;

    const plotCount = req.plotSpecs?.length || 1;
    const gap = plotCount > 1 ? 8 : 0;

    // Each plot is full container height, 16:9 wide — overflow for >2 plots
    const plotH = h;
    const plotW = Math.round(plotH * 16 / 9);
    const dim = { width: plotW, height: plotH };
    setPlotDim(dim);

    if (plotCount > 1) {
      container.style.display = 'grid';
      container.style.gridTemplateColumns = 'repeat(2, auto)';
      container.style.gap = `${gap}px`;
    }

    renderRequirementPlot(container, req, dim);

    return () => {
      const children = Array.from(container.children) as HTMLDivElement[];
      for (const child of children) {
        try { purgePlot(child); } catch { /* ignore */ }
      }
    };
  }, [req.id]);

  const actualVal = req.actual ?? NaN;
  const margin = computeMargin(actualVal, req.minVal, req.maxVal);
  const level = marginLevel(margin);

  return (
    <div className="rall-row">
      {/* Card */}
      <div className="rall-card">
        <div className="req-info-card-outer">
          <div className="ric-header">
            <div className="ric-name">{req.name}</div>
            <div className={`ric-badge ${req.passed ? 'pass' : 'fail'}`}>
              {req.passed ? 'PASS' : 'FAIL'}
            </div>
          </div>
          <div className="ric-body">
            {/* Result */}
            <div className="ric-section">
              <div className="ric-section-title">Result</div>
              <div className="ric-actual-row">
                <span className="ric-label">Actual</span>
                <span className={`ric-actual-value ${req.passed ? 'pass' : 'fail'}`}>
                  {req.actual !== null ? formatEng(req.actual, req.unit) : 'N/A'}
                </span>
              </div>
              <div className="ric-row">
                <span className="ric-label">Margin</span>
                <span className={`ric-value ${level === 'high' ? 'pass' : level === 'low' ? 'fail' : 'warn'}`}>
                  {margin.toFixed(1)}%
                </span>
              </div>
              <div className="ric-margin-bar">
                <div className="ric-margin-track">
                  <div className={`ric-margin-fill ${level}`} style={{ width: `${Math.min(100, margin)}%` }} />
                </div>
              </div>
            </div>

            {/* Bounds */}
            <div className="ric-section ric-right">
              <div className="ric-section-title">Bounds</div>
              <div className="ric-row">
                <span className="ric-label">Min</span>
                <EditableField
                  value={String(req.minVal ?? '')}
                  displayValue={formatEng(req.minVal, req.unit)}
                  className="ric-value"
                  enabled={canEdit}
                  onSave={v => handleFieldChange('min_val', v)}
                />
              </div>
              <div className="ric-row">
                <span className="ric-label">Max</span>
                <EditableField
                  value={String(req.maxVal ?? '')}
                  displayValue={formatEng(req.maxVal, req.unit)}
                  className="ric-value"
                  enabled={canEdit}
                  onSave={v => handleFieldChange('max_val', v)}
                />
              </div>
            </div>

            {/* Configuration */}
            <div className="ric-section">
              <div className="ric-section-title">Configuration</div>
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

            {/* Simulation Config */}
            <div className="ric-section ric-right">
              <div className="ric-section-title">Simulation</div>
              <SimConfigFields req={req} canEdit={canEdit} onFieldChange={handleFieldChange} buildTime={buildTime} />
            </div>

            {req.justification && (
              <div className="ric-section ric-full">
                <div className="ric-section-title">Justification</div>
                <div className="ric-justification-text">{req.justification}</div>
              </div>
            )}

            {/* Stale / Rerun bar */}
            {stale && (
              <div className="ric-section ric-full ric-rerun-bar">
                <span className="ric-dirty">Simulation config changed — rerun to see new results</span>
                <button className={`ric-rerun-btn ${rerunning ? 'ric-saving' : ''}`} onClick={handleRerun} disabled={rerunning}>
                  {rerunning ? 'Running...' : 'Rerun Simulation'}
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Plots with toolbar */}
      <div className="rall-plots plot-container">
        <div ref={plotsRef} />
        {req.plotSpecs && req.plotSpecs.length > 0 && req.plotSpecs[0].meta && (
          <PlotToolbar req={req} specIndex={0} onDirty={handlePlotDirty} />
        )}
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

  const filtered = useMemo(() => {
    let reqs = sorted;
    if (filter === 'pass') reqs = reqs.filter(r => r.passed);
    else if (filter === 'fail') reqs = reqs.filter(r => !r.passed);
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

  const passCount = useMemo(() => sorted.filter(r => r.passed).length, [sorted]);
  const failCount = useMemo(() => sorted.filter(r => !r.passed).length, [sorted]);

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
