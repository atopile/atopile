/**
 * Status badge component showing build/stage status with appropriate styling.
 */
import type { BuildStatus, StageStatus } from '../types/build';

interface StatusBadgeProps {
  status: BuildStatus | StageStatus;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
}

const statusConfig: Record<BuildStatus | StageStatus, { icon: string; color: string; label: string }> = {
  queued: { icon: '○', color: 'text-text-muted', label: 'Queued' },
  building: { icon: '', color: 'text-accent', label: 'Building' }, // Uses spinner component
  success: { icon: '✓', color: 'text-success', label: 'Success' },
  warning: { icon: '⚠', color: 'text-warning', label: 'Warning' },
  failed: { icon: '✗', color: 'text-error', label: 'Failed' },
};

const sizeClasses = {
  sm: 'text-sm',
  md: 'text-base',
  lg: 'text-lg',
};

function Spinner({ className = '' }: { className?: string }) {
  return (
    <svg
      className={`animate-spin ${className}`}
      width="1em"
      height="1em"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.5"
    >
      <circle cx="12" cy="12" r="10" strokeOpacity="0.25" />
      <path d="M12 2a10 10 0 0 1 10 10" strokeLinecap="round" />
    </svg>
  );
}

export function StatusBadge({ status, size = 'md', showLabel = false }: StatusBadgeProps) {
  const config = statusConfig[status];

  return (
    <span className={`inline-flex items-center gap-1 ${config.color} ${sizeClasses[size]}`}>
      {status === 'building' ? <Spinner /> : <span>{config.icon}</span>}
      {showLabel && <span>{config.label}</span>}
    </span>
  );
}

export function StatusIcon({ status, className = '' }: { status: BuildStatus | StageStatus; className?: string }) {
  const config = statusConfig[status];

  if (status === 'building') {
    return <Spinner className={`${config.color} ${className}`} />;
  }

  return (
    <span className={`${config.color} ${className}`}>
      {config.icon}
    </span>
  );
}
