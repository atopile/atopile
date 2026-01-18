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
  building: { icon: '●', color: 'text-accent', label: 'Building' },
  success: { icon: '✓', color: 'text-success', label: 'Success' },
  warning: { icon: '⚠', color: 'text-warning', label: 'Warning' },
  failed: { icon: '✗', color: 'text-error', label: 'Failed' },
};

const sizeClasses = {
  sm: 'text-sm',
  md: 'text-base',
  lg: 'text-lg',
};

export function StatusBadge({ status, size = 'md', showLabel = false }: StatusBadgeProps) {
  const config = statusConfig[status];

  return (
    <span className={`inline-flex items-center gap-1 ${config.color} ${sizeClasses[size]}`}>
      <span className={status === 'building' ? 'animate-pulse' : ''}>{config.icon}</span>
      {showLabel && <span>{config.label}</span>}
    </span>
  );
}

export function StatusIcon({ status, className = '' }: { status: BuildStatus | StageStatus; className?: string }) {
  const config = statusConfig[status];
  return (
    <span className={`${config.color} ${className} ${status === 'building' ? 'animate-pulse' : ''}`}>
      {config.icon}
    </span>
  );
}
