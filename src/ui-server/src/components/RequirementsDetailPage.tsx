import { useRef, useEffect, useState, useCallback } from 'react';
import type { RequirementData, RequirementsData } from './requirements/types';
import { formatEng, computeMargin, marginLevel, formatBuildTime } from './requirements/helpers';
import { renderRequirementPlot, rerenderWithLimits, purgePlot } from './requirements/charts';
import { EditableField, MEASUREMENT_OPTIONS, CAPTURE_OPTIONS } from './requirements/EditableField';
import { updateRequirement, rerunSimulation } from './requirements/api';
import { PlotToolbar } from './requirements/PlotToolbar';

interface RequirementsDetailPageProps {
  requirementId: string;
  injectedData?: RequirementData | null;
  injectedBuildTime?: string;
}

type WindowGlobals = Window & {
  __ATOPILE_API_URL__?: string;
  __ATOPILE_PROJECT_ROOT__?: string;
  __ATOPILE_TARGET__?: string;
};

/** Fields that only change pass/fail bounds — instant local re-eval, no rerun */
const LIMIT_FIELDS = new Set(['min_val', 'max_val', 'limit_expr']);

/** Fields that change plot rendering but don't need a new simulation */
const PLOT_FIELDS = new Set([
  'title', 'x', 'y', 'y_secondary', 'color', 'plot_limits', 'simulation',
  'required_plot', 'supplementary_plot',
]);

export function RequirementsDetailPage({ requirementId, injectedData, injectedBuildTime }: RequirementsDetailPageProps) {
  const chartRef = useRef<HTMLDivElement>(null);
  const cardRef = useRef<HTMLDivElement>(null);
  const [req, setReq] = useState<RequirementData | null>(injectedData ?? null);
  const [buildTime, setBuildTime] = useState<string>(injectedBuildTime ?? '');
  const [loading, setLoading] = useState(!injectedData);
  const [error, setError] = useState<string | null>(null);
  const [stale, setStale] = useState(false);
  const [rerunning, setRerunning] = useState(false);
  const [chartDim, setChartDim] = useState<{ width: number; height: number } | null>(null);

  const canEdit = !!(req?.sourceFile && req?.varName);

  const handleFieldChange = useCallback(async (field: string, value: string) => {
    if (!req?.sourceFile || !req?.varName) return;
    await updateRequirement({
      source_file: req.sourceFile,
      var_name: req.varName,
      updates: { [field]: value },
    });

    if (LIMIT_FIELDS.has(field)) {
      // Instant local re-evaluation: update pass/fail + re-render chart
      const numVal = parseFloat(value);
      if (!isNaN(numVal)) {
        const newMin = field === 'min_val' ? numVal : req.minVal;
        const newMax = field === 'max_val' ? numVal : req.maxVal;
        const newPassed = req.actual !== null && isFinite(req.actual) && newMin <= req.actual && req.actual <= newMax;
        const updated = { ...req, minVal: newMin, maxVal: newMax, passed: newPassed };
        setReq(updated);

        // Re-render plot with new limits
        const chartEl = chartRef.current;
        if (chartEl && chartDim) {
          await rerenderWithLimits(chartEl, updated, newMin, newMax, chartDim);
        }
      }
    } else if (!PLOT_FIELDS.has(field)) {
      // Simulation field changed — mark stale
      setStale(true);
    }
    // Plot fields: saved to .ato but don't mark stale (no new simulation needed)
  }, [req, chartDim]);

  const handleRerun = useCallback(async () => {
    setRerunning(true);
    try {
      await rerunSimulation();
      setStale(false);
    } catch { /* */ }
    finally { setRerunning(false); }
  }, []);

  const handlePlotDirty = useCallback(() => {
    // Plot config changes don't need a new simulation — no stale marker
  }, []);

  // Fetch from API if data wasn't injected
  useEffect(() => {
    if (injectedData) return;
    const w = window as WindowGlobals;
    const apiUrl = w.__ATOPILE_API_URL__ || '';
    const projectRoot = w.__ATOPILE_PROJECT_ROOT__ || '';
    const target = w.__ATOPILE_TARGET__ || 'default';
    if (!apiUrl || !projectRoot) { setError('Missing API URL or project root'); setLoading(false); return; }

    const url = `${apiUrl}/api/requirements?project_root=${encodeURIComponent(projectRoot)}&target=${encodeURIComponent(target)}`;
    fetch(url)
      .then(res => { if (!res.ok) throw new Error(`HTTP ${res.status}`); return res.json() as Promise<RequirementsData>; })
      .then(data => { setReq(data.requirements.find(r => r.id === requirementId) ?? null); setBuildTime(data.buildTime || ''); setLoading(false); })
      .catch(err => { setError(err instanceof Error ? err.message : 'Failed to fetch requirements'); setLoading(false); });
  }, [requirementId, injectedData]);

  // Render chart
  useEffect(() => {
    const chartEl = chartRef.current;
    const cardEl = cardRef.current;
    if (!chartEl || !cardEl || !req) return;
    chartEl.style.display = '';
    chartEl.style.gridTemplateColumns = '';
    chartEl.style.gap = '';

    const cardH = cardEl.offsetHeight;
    if (!cardH || !chartEl.clientWidth) return;

    const plotCount = req.plotSpecs?.length || 1;
    const plotH = cardH;
    const plotW = Math.round(plotH * 16 / 9);
    const dim = { width: plotW, height: plotH };
    setChartDim(dim);

    if (plotCount > 1) {
      chartEl.style.display = 'grid';
      chartEl.style.gridTemplateColumns = 'repeat(2, auto)';
      chartEl.style.gap = '8px';
    }

    renderRequirementPlot(chartEl, req, dim);
    return () => { for (const c of Array.from(chartEl.children) as HTMLDivElement[]) { try { purgePlot(c); } catch { /* */ } } };
  }, [req?.id]);

  if (loading) return <div className="rdp-empty"><div className="rdp-empty-title">Loading requirement...</div></div>;
  if (error) return <div className="rdp-empty"><div className="rdp-empty-title">Error loading requirement</div><div className="rdp-empty-desc">{error}</div></div>;
  if (!req) return <div className="rdp-empty"><div className="rdp-empty-title">Requirement not found</div><div className="rdp-empty-desc">ID: {requirementId || '(none)'}</div></div>;

  const actualVal = req.actual ?? NaN;
  const margin = computeMargin(actualVal, req.minVal, req.maxVal);
  const level = marginLevel(margin);

  return (
    <div className="rdp-root">
      <div className="rdp-info">
        <div className="req-info-card-outer" ref={cardRef}>
          <div className="ric-header">
            <div className="ric-name">{req.name}</div>
            <div className={`ric-badge ${req.passed ? 'pass' : 'fail'}`}>{req.passed ? 'PASS' : 'FAIL'}</div>
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
                <span className="ric-label">Limit</span>
                <EditableField
                  value={req.limitExpr ?? `${formatEng(req.minVal, req.unit)} to ${formatEng(req.maxVal, req.unit)}`}
                  className="ric-value"
                  enabled={canEdit}
                  onSave={v => handleFieldChange('limit_expr', v)}
                />
              </div>
              <div className="ric-row">
                <span className="ric-label">Margin</span>
                <span className={`ric-value ${level === 'high' ? 'pass' : level === 'low' ? 'fail' : 'warn'}`}>{margin.toFixed(1)}%</span>
              </div>
              <div className="ric-margin-bar">
                <div className="ric-margin-track">
                  <div className={`ric-margin-fill ${level}`} style={{ width: `${Math.min(100, margin)}%` }} />
                </div>
              </div>
            </div>

            {/* Configuration */}
            <div className="ric-section">
              <div className="ric-section-title">Configuration</div>
              <div className="ric-row">
                <span className="ric-label">Net</span>
                <EditableField value={req.net} displayValue={req.displayNet || req.net} className="ric-value" enabled={canEdit} onSave={v => handleFieldChange('net', v)} />
              </div>
              <div className="ric-row">
                <span className="ric-label">Capture</span>
                <EditableField value={req.capture} className="ric-value" enabled={canEdit} options={CAPTURE_OPTIONS} onSave={v => handleFieldChange('capture', v)} />
              </div>
              <div className="ric-row">
                <span className="ric-label">Measurement</span>
                <EditableField value={req.measurement} className="ric-value" enabled={canEdit} options={MEASUREMENT_OPTIONS} onSave={v => handleFieldChange('measurement', v)} />
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

      {/* Chart area with plot toolbar */}
      <div className="rdp-chart">
        <div className="plot-container">
          <div ref={chartRef} />
          <PlotToolbar req={req} specIndex={0} onDirty={handlePlotDirty} />
        </div>
      </div>
    </div>
  );
}

/** Simulation config rows */
function SimConfigFields({ req, canEdit, onFieldChange, buildTime }: {
  req: RequirementData; canEdit: boolean;
  onFieldChange: (field: string, value: string) => Promise<void>;
  buildTime: string;
}) {
  const isTransient = req.capture === 'transient';
  const isAC = req.capture === 'ac';

  return (
    <>
      {isTransient && (
        <>
          <div className="ric-row">
            <span className="ric-label">Start</span>
            <EditableField value={String(req.tranStart ?? 0)} displayValue={formatEng(req.tranStart ?? 0, 's')} className="ric-value" enabled={canEdit} onSave={v => onFieldChange('tran_start', v)} />
          </div>
          {req.tranStop != null && (
            <div className="ric-row">
              <span className="ric-label">Stop</span>
              <EditableField value={String(req.tranStop)} displayValue={formatEng(req.tranStop, 's')} className="ric-value" enabled={canEdit} onSave={v => onFieldChange('tran_stop', v)} />
            </div>
          )}
          {req.tranStep != null && (
            <div className="ric-row">
              <span className="ric-label">Step</span>
              <EditableField value={String(req.tranStep)} displayValue={formatEng(req.tranStep, 's')} className="ric-value" enabled={canEdit} onSave={v => onFieldChange('tran_step', v)} />
            </div>
          )}
          {req.settlingTolerance != null && (
            <div className="ric-row">
              <span className="ric-label">Settling tol.</span>
              <EditableField value={String(req.settlingTolerance)} displayValue={`${(req.settlingTolerance * 100).toFixed(1)}%`} className="ric-value" enabled={canEdit} onSave={v => onFieldChange('settling_tolerance', v)} />
            </div>
          )}
        </>
      )}
      {isAC && (
        <>
          {req.acStartFreq != null && <div className="ric-row"><span className="ric-label">Start freq</span><EditableField value={String(req.acStartFreq)} displayValue={formatEng(req.acStartFreq, 'Hz')} className="ric-value" enabled={canEdit} onSave={v => onFieldChange('ac_start_freq', v)} /></div>}
          {req.acStopFreq != null && <div className="ric-row"><span className="ric-label">Stop freq</span><EditableField value={String(req.acStopFreq)} displayValue={formatEng(req.acStopFreq, 'Hz')} className="ric-value" enabled={canEdit} onSave={v => onFieldChange('ac_stop_freq', v)} /></div>}
          {req.acPointsPerDec != null && <div className="ric-row"><span className="ric-label">Pts/decade</span><EditableField value={String(req.acPointsPerDec)} className="ric-value" enabled={canEdit} onSave={v => onFieldChange('ac_points_per_dec', v)} /></div>}
          {req.acSourceName != null && <div className="ric-row"><span className="ric-label">AC source</span><EditableField value={req.acSourceName} className="ric-value" enabled={canEdit} onSave={v => onFieldChange('ac_source_name', v)} /></div>}
          {req.acMeasureFreq != null && <div className="ric-row"><span className="ric-label">Meas. freq</span><EditableField value={String(req.acMeasureFreq)} displayValue={formatEng(req.acMeasureFreq, 'Hz')} className="ric-value" enabled={canEdit} onSave={v => onFieldChange('ac_measure_freq', v)} /></div>}
          {req.acRefNet != null && <div className="ric-row"><span className="ric-label">Ref net</span><EditableField value={req.acRefNet} className="ric-value" enabled={canEdit} onSave={v => onFieldChange('ac_ref_net', v)} /></div>}
        </>
      )}
      {/* SPICE source override */}
      {req.sourceSpec && (
        <div className="ric-row">
          <span className="ric-label">Source</span>
          <EditableField value={req.sourceSpec} className="ric-value" enabled={canEdit} onSave={v => onFieldChange('spice', v)} />
        </div>
      )}
      {/* Extra SPICE */}
      {req.extraSpice && req.extraSpice.length > 0 && (
        <div className="ric-row">
          <span className="ric-label">Extra SPICE</span>
          <span className="ric-value mono-muted">{req.extraSpice.join(' | ')}</span>
        </div>
      )}
      {req.contextNets && req.contextNets.length > 0 && <div className="ric-row"><span className="ric-label">Context</span><span className="ric-value">{req.contextNets.join(', ')}</span></div>}
      {req.simulationName && <div className="ric-row"><span className="ric-label">Simulation</span><span className="ric-value">{req.simulationName}</span></div>}
      {req.timeSeries && <div className="ric-row"><span className="ric-label">Points</span><span className="ric-value mono-muted">{req.timeSeries.time.length}</span></div>}
      {buildTime && <div className="ric-row"><span className="ric-label">Built</span><span className="ric-value mono-muted">{formatBuildTime(buildTime)}</span></div>}
    </>
  );
}
