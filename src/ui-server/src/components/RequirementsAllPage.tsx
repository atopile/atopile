import { useRef, useEffect, useState, useMemo } from 'react';
import type { RequirementData, FilterType } from './requirements/types';
import { formatEng, computeMargin, marginLevel, formatBuildTime } from './requirements/helpers';
import {
  renderSpecAtSize,
  renderTransientPlot,
  renderDCPlot,
  renderBodePlot,
  renderSweepPlot,
  purgePlot,
} from './requirements/charts';

interface RequirementsAllPageProps {
  requirements: RequirementData[];
  buildTime: string;
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
/*  Single requirement row: card (left) + plot(s) (right)             */
/* ------------------------------------------------------------------ */

function RequirementRow({ req, buildTime }: { req: RequirementData; buildTime: string }) {
  const cardRef = useRef<HTMLDivElement>(null);
  const plotsRef = useRef<HTMLDivElement>(null);
  const [cardH, setCardH] = useState(0);
  const [plotsW, setPlotsW] = useState(0);

  // Measure card height + plots container width
  useEffect(() => {
    const card = cardRef.current;
    const plots = plotsRef.current;
    if (!card || !plots) return;
    const ro = new ResizeObserver(() => {
      const ch = Math.round(card.getBoundingClientRect().height);
      const pw = Math.round(plots.getBoundingClientRect().width);
      if (ch > 0) setCardH(ch);
      if (pw > 0) setPlotsW(pw);
    });
    ro.observe(card);
    ro.observe(plots);
    return () => ro.disconnect();
  }, []);

  // Render plots once sizes are known
  useEffect(() => {
    const container = plotsRef.current;
    if (!container || plotsW === 0 || cardH === 0) return;

    // Clear previous plots
    const oldChildren = Array.from(container.children) as HTMLDivElement[];
    for (const child of oldChildren) {
      try { purgePlot(child); } catch { /* ignore */ }
    }
    container.innerHTML = '';

    const plotW = plotsW;
    const plotH = cardH;

    if (req.plotSpecs && req.plotSpecs.length > 0) {
      for (const spec of req.plotSpecs) {
        const wrapper = document.createElement('div');
        wrapper.style.width = `${plotW}px`;
        wrapper.style.height = `${plotH}px`;
        container.appendChild(wrapper);
        renderSpecAtSize(wrapper as HTMLDivElement, spec, plotW, plotH);
      }
    } else {
      const wrapper = document.createElement('div');
      wrapper.style.width = `${plotW}px`;
      wrapper.style.height = `${plotH}px`;
      wrapper.style.padding = '0';
      container.appendChild(wrapper);

      const chartEl = document.createElement('div');
      wrapper.appendChild(chartEl);

      if (req.sweepPoints && req.sweepPoints.length > 0) {
        renderSweepPlot(chartEl as HTMLDivElement, req);
      } else if (req.frequencySeries) {
        renderBodePlot(chartEl as HTMLDivElement, req);
      } else if (req.timeSeries) {
        renderTransientPlot(chartEl as HTMLDivElement, req);
      } else {
        renderDCPlot(chartEl as HTMLDivElement, req);
      }
    }

    return () => {
      const children = Array.from(container.children) as HTMLDivElement[];
      for (const child of children) {
        try { purgePlot(child); } catch { /* ignore */ }
      }
    };
  }, [req.id, plotsW, cardH]);

  const actualVal = req.actual ?? NaN;
  const margin = computeMargin(actualVal, req.minVal, req.maxVal);
  const level = marginLevel(margin);
  const measLabel = req.measurement.replace(/_/g, ' ');
  const captureLabel = req.capture === 'dcop' ? 'DC Operating Point' : req.capture === 'ac' ? 'AC Analysis' : 'Transient';
  const hasSweep = !!(req.sweepPoints && req.sweepPoints.length > 0);
  const hasTransientConfig = req.capture === 'transient' && !hasSweep;

  return (
    <div className="rall-row">
      {/* Card */}
      <div className="rall-card" ref={cardRef}>
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

            {/* Configuration */}
            <div className="ric-section ric-right">
              <div className="ric-section-title">Configuration</div>
              <div className="ric-row">
                <span className="ric-label">Net</span>
                <span className="ric-value">{req.displayNet || req.net}</span>
              </div>
              <div className="ric-row">
                <span className="ric-label">Capture</span>
                <span className="ric-value">{captureLabel}</span>
              </div>
              <div className="ric-row">
                <span className="ric-label">Measurement</span>
                <span className="ric-value">{measLabel}</span>
              </div>
            </div>

            {/* Bounds */}
            <div className="ric-section">
              <div className="ric-section-title">Bounds</div>
              <div className="ric-row">
                <span className="ric-label">Min</span>
                <span className="ric-value">{formatEng(req.minVal, req.unit)}</span>
              </div>
              <div className="ric-row">
                <span className="ric-label">Typical</span>
                <span className="ric-value">{formatEng(req.typical, req.unit)}</span>
              </div>
              <div className="ric-row">
                <span className="ric-label">Max</span>
                <span className="ric-value">{formatEng(req.maxVal, req.unit)}</span>
              </div>
            </div>

            {/* Sim params */}
            <div className="ric-section ric-right">
              <div className="ric-section-title">{hasSweep ? 'Sweep Config' : hasTransientConfig ? 'Transient Config' : 'Info'}</div>
              {hasSweep ? (
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
                  {req.contextNets && req.contextNets.length > 0 && (
                    <div className="ric-row">
                      <span className="ric-label">Context</span>
                      <span className="ric-value">{req.contextNets.join(', ')}</span>
                    </div>
                  )}
                  {buildTime && (
                    <div className="ric-row">
                      <span className="ric-label">Built</span>
                      <span className="ric-value mono-muted">{formatBuildTime(buildTime)}</span>
                    </div>
                  )}
                </>
              ) : hasTransientConfig ? (
                <>
                  {req.tranStart != null && (
                    <div className="ric-row">
                      <span className="ric-label">Start</span>
                      <span className="ric-value">{formatEng(req.tranStart, 's')}</span>
                    </div>
                  )}
                  {req.tranStop != null && (
                    <div className="ric-row">
                      <span className="ric-label">Stop</span>
                      <span className="ric-value">{formatEng(req.tranStop, 's')}</span>
                    </div>
                  )}
                  {req.timeSeries && (
                    <div className="ric-row">
                      <span className="ric-label">Points</span>
                      <span className="ric-value mono-muted">{req.timeSeries.time.length}</span>
                    </div>
                  )}
                  {req.settlingTolerance != null && (
                    <div className="ric-row">
                      <span className="ric-label">Settling tol.</span>
                      <span className="ric-value">{(req.settlingTolerance * 100).toFixed(1)}%</span>
                    </div>
                  )}
                  {req.contextNets && req.contextNets.length > 0 && (
                    <div className="ric-row">
                      <span className="ric-label">Context</span>
                      <span className="ric-value">{req.contextNets.join(', ')}</span>
                    </div>
                  )}
                  {buildTime && (
                    <div className="ric-row">
                      <span className="ric-label">Built</span>
                      <span className="ric-value mono-muted">{formatBuildTime(buildTime)}</span>
                    </div>
                  )}
                </>
              ) : (
                <>
                  <div className="ric-row">
                    <span className="ric-label">Unit</span>
                    <span className="ric-value">{req.unit}</span>
                  </div>
                  <div className="ric-row">
                    <span className="ric-label">Type</span>
                    <span className="ric-value">Static</span>
                  </div>
                  {buildTime && (
                    <div className="ric-row">
                      <span className="ric-label">Built</span>
                      <span className="ric-value mono-muted">{formatBuildTime(buildTime)}</span>
                    </div>
                  )}
                </>
              )}
            </div>

            {req.justification && (
              <div className="ric-section ric-full">
                <div className="ric-section-title">Justification</div>
                <div className="ric-justification-text">{req.justification}</div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Plots — stacked vertically, each same size as card */}
      <div className="rall-plots" ref={plotsRef} />
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main all-requirements page                                        */
/* ------------------------------------------------------------------ */

export function RequirementsAllPage({ requirements, buildTime }: RequirementsAllPageProps) {
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
