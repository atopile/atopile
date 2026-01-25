/**
 * Status icon component for build and stage status.
 */

import type { BuildStatus, StageStatus } from '../types/build';
import './StatusIcon.css';

interface StatusIconProps {
  status: BuildStatus | StageStatus;
  size?: number;
}

export function StatusIcon({ status, size = 16 }: StatusIconProps) {
  const isSpinning = status === 'building';

  return (
    <span className={`status-icon ${isSpinning ? 'spinning' : ''}`}>
      {renderIcon(status, size)}
    </span>
  );
}

function renderIcon(status: BuildStatus | StageStatus, size: number) {
  const style = { width: size, height: size };

  switch (status) {
    case 'queued':
      return (
        <svg style={style} viewBox="0 0 16 16" fill="none">
          <circle cx="8" cy="8" r="6" stroke="var(--text-muted)" strokeWidth="1.5" />
        </svg>
      );

    case 'building':
      return (
        <svg style={style} viewBox="0 0 16 16" fill="none">
          <circle cx="8" cy="8" r="6" stroke="var(--accent)" strokeWidth="1.5" strokeDasharray="20 10" />
        </svg>
      );

    case 'success':
      return (
        <svg style={style} viewBox="0 0 16 16" fill="none">
          <circle cx="8" cy="8" r="6" fill="var(--success)" fillOpacity="0.2" />
          <path d="M5 8l2 2 4-4" stroke="var(--success)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      );

    case 'warning':
      return (
        <svg style={style} viewBox="0 0 16 16" fill="none">
          <circle cx="8" cy="8" r="6" fill="var(--warning)" fillOpacity="0.2" />
          <path d="M8 5v3M8 10v1" stroke="var(--warning)" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      );

    case 'failed':
      return (
        <svg style={style} viewBox="0 0 16 16" fill="none">
          <circle cx="8" cy="8" r="6" fill="var(--error)" fillOpacity="0.2" />
          <path d="M6 6l4 4M10 6l-4 4" stroke="var(--error)" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      );

    default:
      return (
        <svg style={style} viewBox="0 0 16 16" fill="none">
          <circle cx="8" cy="8" r="6" stroke="var(--text-muted)" strokeWidth="1.5" />
        </svg>
      );
  }
}
