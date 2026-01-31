/**
 * Status icon component for build and stage status.
 * Provides consistent status indicators across the UI.
 */

import { Loader2 } from 'lucide-react';
import type { BuildStatus, StageStatus } from '../types/build';
import type { BuildTarget, BuildStage } from './projectsTypes';
import './StatusIcon.css';

interface StatusIconProps {
  status: BuildStatus | StageStatus | BuildTarget['status'] | BuildStage['status'];
  size?: number;
  /** Queue position to display for queued status */
  queuePosition?: number;
  /** Render a dimmed version for "last build" status */
  dimmed?: boolean;
}

/**
 * Unified status icon component for build and stage status display.
 * Use this instead of inline icon rendering for consistency.
 */
export function StatusIcon({ status, size = 16, queuePosition, dimmed = false }: StatusIconProps) {
  return (
    <span className={`status-icon ${status} ${dimmed ? 'dimmed' : ''}`}>
      {renderIcon(status, size, queuePosition)}
    </span>
  );
}

function renderIcon(
  status: BuildStatus | StageStatus | BuildTarget['status'] | BuildStage['status'],
  size: number,
  queuePosition?: number
) {
  const style = { width: size, height: size };

  switch (status) {
    case 'queued':
      return (
        <>
          <svg style={style} viewBox="0 0 16 16" fill="none">
            <circle cx="8" cy="8" r="6" stroke="var(--text-muted)" strokeWidth="1.5" />
          </svg>
          {queuePosition && <span className="queue-position">{queuePosition}</span>}
        </>
      );

    case 'building':
    case 'running':
      // Use Loader2 from lucide-react with spin class - matches existing spinners in codebase
      return <Loader2 size={size} className="spin" />;

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
    case 'error':
      return (
        <svg style={style} viewBox="0 0 16 16" fill="none">
          <circle cx="8" cy="8" r="6" fill="var(--error)" fillOpacity="0.2" />
          <path d="M6 6l4 4M10 6l-4 4" stroke="var(--error)" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      );

    case 'skipped':
      return (
        <svg style={style} viewBox="0 0 16 16" fill="none">
          <circle cx="8" cy="8" r="6" stroke="var(--text-muted)" strokeWidth="1.5" strokeDasharray="2 2" />
        </svg>
      );

    case 'pending':
    case 'idle':
    default:
      return (
        <svg style={style} viewBox="0 0 16 16" fill="none">
          <circle cx="8" cy="8" r="6" stroke="var(--text-muted)" strokeWidth="1.5" />
        </svg>
      );
  }
}
