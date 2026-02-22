import { useRef, useEffect, useState } from 'react';
import type { RequirementData, RequirementsData } from './requirements/types';
import { formatEng, computeMargin, marginLevel, formatBuildTime } from './requirements/helpers';
import { renderTransientPlot, renderDCPlot, renderBodePlot, purgePlot, resizePlot } from './requirements/charts';

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

export function RequirementsDetailPage({ requirementId, injectedData, injectedBuildTime }: RequirementsDetailPageProps) {
  const chartRef = useRef<HTMLDivElement>(null);
  const [req, setReq] = useState<RequirementData | null>(injectedData ?? null);
  const [buildTime, setBuildTime] = useState<string>(injectedBuildTime ?? '');
  const [loading, setLoading] = useState(!injectedData);
  const [error, setError] = useState<string | null>(null);

  // Only fetch from API if data wasn't injected
  useEffect(() => {
    if (injectedData) return;

    const w = window as WindowGlobals;
    const apiUrl = w.__ATOPILE_API_URL__ || '';
    const projectRoot = w.__ATOPILE_PROJECT_ROOT__ || '';
    const target = w.__ATOPILE_TARGET__ || 'default';

    if (!apiUrl || !projectRoot) {
      setError('Missing API URL or project root');
      setLoading(false);
      return;
    }

    const url = `${apiUrl}/api/requirements?project_root=${encodeURIComponent(projectRoot)}&target=${encodeURIComponent(target)}`;

    fetch(url)
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json() as Promise<RequirementsData>;
      })
      .then(data => {
        const found = data.requirements.find(r => r.id === requirementId) ?? null;
        setReq(found);
        setBuildTime(data.buildTime || '');
        setLoading(false);
      })
      .catch(err => {
        setError(err instanceof Error ? err.message : 'Failed to fetch requirements');
        setLoading(false);
      });
  }, [requirementId, injectedData]);

  // Render chart when req is loaded
  useEffect(() => {
    if (!chartRef.current || !req) return;
    const el = chartRef.current;

    if (req.frequencySeries) {
      renderBodePlot(el, req);
    } else if (req.timeSeries) {
      renderTransientPlot(el, req);
    } else {
      renderDCPlot(el, req);
    }

    const handleResize = () => { resizePlot(el); };
    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
      purgePlot(el);
    };
  }, [req?.id]);

  if (loading) {
    return (
      <div className="rdp-empty">
        <div className="rdp-empty-title">Loading requirement...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rdp-empty">
        <div className="rdp-empty-title">Error loading requirement</div>
        <div className="rdp-empty-desc">{error}</div>
      </div>
    );
  }

  if (!req) {
    return (
      <div className="rdp-empty">
        <div className="rdp-empty-title">Requirement not found</div>
        <div className="rdp-empty-desc">ID: {requirementId || '(none)'}</div>
      </div>
    );
  }

  const actualVal = req.actual ?? NaN;
  const margin = computeMargin(actualVal, req.minVal, req.maxVal);
  const level = marginLevel(margin);
  const measLabel = req.measurement.replace(/_/g, ' ');
  const captureLabel = req.capture === 'dcop' ? 'DC Operating Point' : req.capture === 'ac' ? 'AC Analysis' : 'Transient';
  const hasTransientConfig = req.capture === 'transient';

  return (
    <div className="rdp-root">
      {/* Info card */}
      <div className="rdp-info">
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
              <div className="ric-section-title">{hasTransientConfig ? 'Transient Config' : 'Info'}</div>
              {hasTransientConfig ? (
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

      {/* Chart — fills remaining space */}
      <div className="rdp-chart">
        <div ref={chartRef} />
      </div>
    </div>
  );
}
