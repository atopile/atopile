import type { RequirementData } from './types';
import { formatEng, computeMargin, marginLevel } from './helpers';

interface ReqTooltipProps {
  req: RequirementData | null;
  rect: DOMRect | null;
}

export function ReqTooltip({ req, rect }: ReqTooltipProps) {
  if (!req || !rect) return null;
  const margin = computeMargin(req.actual, req.minVal, req.maxVal);
  const level = marginLevel(margin);
  const captureLabel = req.capture === 'dcop' ? 'DC Operating Point' : 'Transient';
  const measLabel = req.measurement.replace(/_/g, ' ');

  // Position below the hovered item (sidebar is narrow)
  const top = rect.bottom + 4;
  const left = rect.left;

  return (
    <div className="req-tooltip" style={{ top, left }}>
      <div className="req-tooltip-row">
        <span className="tt-label">Status</span>
        <span className="tt-value" style={{ color: req.passed ? 'var(--success)' : 'var(--error)' }}>
          {req.passed ? 'PASS' : 'FAIL'}
        </span>
      </div>
      <div className="req-tooltip-row">
        <span className="tt-label">Actual</span>
        <span className="tt-value">{formatEng(req.actual, req.unit)}</span>
      </div>
      <div className="req-tooltip-row">
        <span className="tt-label">Margin</span>
        <span
          className="tt-value"
          style={{
            color: level === 'high' ? 'var(--success)' : level === 'low' ? 'var(--error)' : 'var(--warning)',
          }}
        >
          {margin.toFixed(1)}%
        </span>
      </div>
      <div className="req-tooltip-divider" />
      <div className="req-tooltip-row">
        <span className="tt-label">Net</span>
        <span className="tt-value">{req.net}</span>
      </div>
      <div className="req-tooltip-row">
        <span className="tt-label">Capture</span>
        <span className="tt-value">{captureLabel}</span>
      </div>
      <div className="req-tooltip-row">
        <span className="tt-label">Measurement</span>
        <span className="tt-value">{measLabel}</span>
      </div>
      <div className="req-tooltip-divider" />
      <div className="req-tooltip-row">
        <span className="tt-label">Min</span>
        <span className="tt-value">{formatEng(req.minVal, req.unit)}</span>
      </div>
      <div className="req-tooltip-row">
        <span className="tt-label">Typical</span>
        <span className="tt-value">{formatEng(req.typical, req.unit)}</span>
      </div>
      <div className="req-tooltip-row">
        <span className="tt-label">Max</span>
        <span className="tt-value">{formatEng(req.maxVal, req.unit)}</span>
      </div>
      {req.justification && (
        <>
          <div className="req-tooltip-divider" />
          <div className="req-tooltip-justification">{req.justification}</div>
        </>
      )}
    </div>
  );
}
