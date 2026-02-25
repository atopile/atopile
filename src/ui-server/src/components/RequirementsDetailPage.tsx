import { useRef, useEffect, useState, useCallback } from 'react';
import type { RequirementData, RequirementsData } from './requirements/types';
import { formatEng, formatBuildTime, parseLimitExpr, reEvalPassFail, measureTran, parseValueWithUnit, goToSource } from './requirements/helpers';
import { renderSpecAtSize, renderTransientPlot, renderDCPlot, renderBodePlot, renderSweepPlot, purgePlot, injectLimitShapes, applyPlotFieldToSpec } from './requirements/charts';
import { EditableField, MEASUREMENT_OPTIONS, CAPTURE_OPTIONS } from './requirements/EditableField';
import { updateRequirement, rerunSimulation, rerunSingleSimulation } from './requirements/api';
import { PlotToolbar, GoToSourceIcon } from './requirements/PlotToolbar';

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

/** Fields that change plot rendering but don't need a new simulation */
const PLOT_FIELDS = new Set([
  'title', 'x', 'y', 'y_secondary', 'color', 'plot_limits', 'simulation',
  'required_plot', 'supplementary_plot',
]);

/** Find signal data in timeSeries by trying various key formats */
function _findSignal(signals: Record<string, number[]>, netKey: string, rawNet: string): number[] | null {
  if (signals[netKey]) return signals[netKey];
  const underscored = netKey.replace(/\./g, '_');
  if (signals[underscored]) return signals[underscored];
  const vRaw = `v(${rawNet.replace(/\./g, '_')})`;
  if (signals[vRaw]) return signals[vRaw];
  const needle = rawNet.replace(/\./g, '_').toLowerCase();
  for (const [k, v] of Object.entries(signals)) {
    if (k.toLowerCase().includes(needle)) return v;
  }
  return null;
}

export function RequirementsDetailPage({ requirementId, injectedData, injectedBuildTime }: RequirementsDetailPageProps) {
  const plotContainerRef = useRef<HTMLDivElement>(null);
  const plotRefs = useRef<(HTMLDivElement | null)[]>([]);
  const containerRefs = useRef<({ current: HTMLDivElement | null })[]>([]);
  const [req, setReq] = useState<RequirementData | null>(injectedData ?? null);
  const [buildTime, setBuildTime] = useState<string>(injectedBuildTime ?? '');
  const [loading, setLoading] = useState(!injectedData);
  const [error, setError] = useState<string | null>(null);
  const [stale, setStale] = useState(false);
  const [rerunning, setRerunning] = useState(false);
  const [, setChartDim] = useState<{ width: number; height: number } | null>(null);
  const [limitVersion, setLimitVersion] = useState(0);

  // Sync from fresh server data when build time changes (WebSocket refresh)
  const prevBuildTime = useRef(injectedBuildTime);
  useEffect(() => {
    if (injectedBuildTime && injectedBuildTime !== prevBuildTime.current) {
      prevBuildTime.current = injectedBuildTime;
      if (injectedData) {
        setReq(injectedData);
        setStale(false);
        setLimitVersion(v => v + 1);
        setLoading(false);
      }
      setBuildTime(injectedBuildTime);
    }
  }, [injectedBuildTime, injectedData]);

  const canEdit = !!(req?.sourceFile && req?.varName);
  const hasResult = req?.actual !== null && req?.actual !== undefined && isFinite(req.actual);
  const plotCount = req?.plotSpecs?.length || 1;

  /** Render a single plot into a ref div */
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
    if (!req?.sourceFile || !req?.varName) return;
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
          if (!prev) return prev;
          const pf = reEvalPassFail(prev.actual, parsed.min, parsed.max, prev.sweepPoints);
          return { ...prev, minVal: parsed.min, maxVal: parsed.max, limitExpr: value, ...pf };
        });
        setLimitVersion(v => v + 1);
      }
    } else if (field === 'min_val') {
      const num = parseFloat(value);
      if (isFinite(num)) {
        setReq(prev => {
          if (!prev) return prev;
          const pf = reEvalPassFail(prev.actual, num, prev.maxVal, prev.sweepPoints);
          return { ...prev, minVal: num, ...pf };
        });
        setLimitVersion(v => v + 1);
      }
    } else if (field === 'max_val') {
      const num = parseFloat(value);
      if (isFinite(num)) {
        setReq(prev => {
          if (!prev) return prev;
          const pf = reEvalPassFail(prev.actual, prev.minVal, num, prev.sweepPoints);
          return { ...prev, maxVal: num, ...pf };
        });
        setLimitVersion(v => v + 1);
      }
    } else if (field === 'measurement') {
      // Client-side re-measurement from existing timeSeries data
      setReq(prev => {
        if (!prev) return prev;
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
      const parsed = parseValueWithUnit(value);
      if (parsed !== null) {
        const key = field === 'tran_start' ? 'tranStart' : field === 'tran_stop' ? 'tranStop' : 'tranStep';
        setReq(prev => prev ? { ...prev, [key]: parsed } : prev);
      }
      setStale(true);
    } else if (field === 'param_values') {
      setReq(prev => prev ? { ...prev, sweepParamValues: value } : prev);
      setStale(true);
    } else if (!PLOT_FIELDS.has(field)) {
      setStale(true);
    }
  }, [req?.sourceFile, req?.varName]);

  const handleRerun = useCallback(async () => {
    if (!req) return;
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
        setReq(prev => prev ? {
          ...prev,
          actual: result.actual,
          passed: result.passed,
          timeSeries: result.timeSeries,
        } : prev);
        setLimitVersion(v => v + 1);
      } else {
        await rerunSimulation();
      }
      setStale(false);
    } catch (err) {
      console.error('Rerun failed:', err);
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
      if (!prev || !prev.plotSpecs || !prev.plotSpecs[specIdx]) return prev;
      const newSpecs = [...prev.plotSpecs];
      newSpecs[specIdx] = applyPlotFieldToSpec(newSpecs[specIdx], field, value, prev.timeSeries);
      return { ...prev, plotSpecs: newSpecs };
    });
    setLimitVersion(v => v + 1);
  }, []);

  const handlePlotDirty = useCallback(() => {
    setStale(true);
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

  // Render charts — one per plotSpec (or one fallback)
  useEffect(() => {
    const outer = plotContainerRef.current;
    if (!outer || !req) return;

    const w = outer.clientWidth;
    if (!w) return;

    // All plots same size: 2-column layout width regardless of plot count
    const gap = 8;
    const plotW = Math.floor((w - gap) / 2);
    const plotH = Math.round(plotW * 9 / 16);
    const dim = { width: plotW, height: plotH };
    setChartDim(dim);

    const count = req.plotSpecs?.length || 1;
    for (let i = 0; i < count; i++) {
      const el = plotRefs.current[i];
      if (el) renderSinglePlot(el, req, dim, i);
    }

    return () => {
      for (const ref of plotRefs.current) {
        if (ref) purgePlot(ref).catch(() => {});
      }
    };
  }, [req?.id, plotCount, limitVersion, renderSinglePlot]);

  if (loading) return <div className="rdp-empty"><div className="rdp-empty-title">Loading requirement...</div></div>;
  if (error) return <div className="rdp-empty"><div className="rdp-empty-title">Error loading requirement</div><div className="rdp-empty-desc">{error}</div></div>;
  if (!req) return <div className="rdp-empty"><div className="rdp-empty-title">Requirement not found</div><div className="rdp-empty-desc">ID: {requirementId || '(none)'}</div></div>;

  return (
    <div className="rdp-root">
      <div className="rall-row">
        {/* Card */}
        <div className="rall-card">
          <div className="req-info-card-outer">
            <div className="ric-header">
              <div className="ric-name">
                <EditableField value={req.name} className="ric-name-edit" enabled={canEdit} onSave={v => handleFieldChange('req_name', v)} />
              </div>
              {req.sourceFile && req.sourceLine && (
                <button className="ric-goto-btn" onClick={() => goToSource(req.sourceFile, req.sourceLine)} title="Go to requirement definition">
                  <GoToSourceIcon />
                </button>
              )}
              <div className={`ric-badge ${hasResult ? (req.passed ? 'pass' : 'fail') : 'pending'}`}>{hasResult ? (req.passed ? 'PASS' : 'FAIL') : '---'}</div>
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

        {/* Plots — one toolbar per plot */}
        <div className="rall-plots" ref={plotContainerRef}>
          {Array.from({ length: plotCount }, (_, i) => {
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
    </div>
  );
}

/** Simulation config rows */
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
