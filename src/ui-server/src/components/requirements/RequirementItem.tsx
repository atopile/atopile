import { memo } from 'react';
import type { RequirementData } from './types';

interface RequirementItemProps {
  req: RequirementData;
  selected: boolean;
  onClick: () => void;
  onHover: (req: RequirementData, rect: DOMRect) => void;
  onLeave: () => void;
}

export const RequirementItem = memo(function RequirementItem({
  req,
  selected,
  onClick,
  onHover,
  onLeave,
}: RequirementItemProps) {
  const hasResult = req.actual !== null && isFinite(req.actual);
  return (
    <div
      className={`req-item ${selected ? 'selected' : ''}`}
      onClick={onClick}
      onMouseEnter={(e) => onHover(req, e.currentTarget.getBoundingClientRect())}
      onMouseLeave={onLeave}
    >
      <div className={`req-status-dot ${hasResult ? (req.passed ? 'pass' : 'fail') : 'pending'}`} />
      <div className="req-item-info">
        <div className="req-item-name">{req.name}</div>
        <div className="req-item-limit">
          {req.limitExpr || `${req.measurement}`}
        </div>
      </div>
      <div className="req-item-tag">{req.capture === 'transient' ? 'Tran' : req.capture === 'ac' ? 'AC' : 'DC'}</div>
    </div>
  );
});
