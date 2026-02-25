import type { RequirementData } from './types';
import { formatEng } from './helpers';

interface ReqTooltipProps {
  req: RequirementData | null;
  rect: DOMRect | null;
}

export function ReqTooltip({ req, rect }: ReqTooltipProps) {
  if (!req || !rect) return null;
  const hasResult = req.actual !== null && isFinite(req.actual);
  const captureLabel = req.capture === 'transient' ? 'Transient' : req.capture === 'ac' ? 'AC' : 'DC Operating Point';
  const measLabel = req.measurement.replace(/_/g, ' ');

  // Position below the hovered item (sidebar is narrow)
  const top = rect.bottom + 4;
  const left = rect.left;

  return (
    <div className="req-tooltip" style={{ top, left }}>
      <div className="req-tooltip-row">
        <span className="tt-label">Status</span>
        <span className="tt-value" style={{ color: hasResult ? (req.passed ? 'var(--success)' : 'var(--error)') : 'var(--text-muted)' }}>
          {hasResult ? (req.passed ? 'PASS' : 'FAIL') : 'Pending'}
        </span>
      </div>
      <div className="req-tooltip-row">
        <span className="tt-label">Limit</span>
        <span className="tt-value">{req.limitExpr || `${formatEng(req.minVal, req.unit)} to ${formatEng(req.maxVal, req.unit)}`}</span>
      </div>
      {hasResult && (
        <div className="req-tooltip-row">
          <span className="tt-label">Actual</span>
          <span className="tt-value">{formatEng(req.actual!, req.unit)}</span>
        </div>
      )}
      <div className="req-tooltip-divider" />
      <div className="req-tooltip-row">
        <span className="tt-label">Net</span>
        <span className="tt-value">{req.displayNet || req.net}</span>
      </div>
      <div className="req-tooltip-row">
        <span className="tt-label">Capture</span>
        <span className="tt-value">{captureLabel}</span>
      </div>
      <div className="req-tooltip-row">
        <span className="tt-label">Measurement</span>
        <span className="tt-value">{measLabel}</span>
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
