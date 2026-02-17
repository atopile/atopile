import { memo } from 'react';
import type { RequirementData } from './types';
import { formatEng } from './helpers';

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
  return (
    <div
      className={`req-item ${selected ? 'selected' : ''}`}
      onClick={onClick}
      onMouseEnter={(e) => onHover(req, e.currentTarget.getBoundingClientRect())}
      onMouseLeave={onLeave}
    >
      <div className={`req-status-dot ${req.passed ? 'pass' : 'fail'}`} />
      <div className="req-item-info">
        <div className="req-item-name">{req.name}</div>
        <div className="req-item-bounds">
          <span className="lsl">{formatEng(req.minVal, req.unit)}</span>
          <span className={`actual ${req.passed ? 'pass' : 'fail'}`}>
            {formatEng(req.actual, req.unit)}
          </span>
          <span className="usl">{formatEng(req.maxVal, req.unit)}</span>
        </div>
      </div>
      <div className="req-item-tag">{req.capture === 'dcop' ? 'DC' : 'AC'}</div>
    </div>
  );
});
