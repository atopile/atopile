import { memo } from 'react';
import type { AgentStatus, PipelineStatus, PipelineSessionStatus } from '@/logic/api/types';

interface StatusBadgeProps {
  status: AgentStatus | PipelineStatus | PipelineSessionStatus;
  size?: 'sm' | 'md';
  /** For agents, show 'idle' instead of 'completed' */
  isAgent?: boolean;
}

export const StatusBadge = memo(function StatusBadge({ status, size = 'md', isAgent = false }: StatusBadgeProps) {
  const sizeClasses = size === 'sm' ? 'px-1.5 py-0.5 text-xs' : 'px-2 py-0.5 text-xs';

  const statusConfig: Record<string, { bg: string; text: string; dot: string; label?: string }> = {
    running: { bg: 'bg-green-900/50', text: 'text-green-300', dot: 'bg-green-400' },
    starting: { bg: 'bg-green-900/50', text: 'text-green-300', dot: 'bg-green-400' },
    completed: { bg: 'bg-blue-900/50', text: 'text-blue-300', dot: 'bg-blue-400' },
    idle: { bg: 'bg-blue-900/50', text: 'text-blue-300', dot: 'bg-blue-400' },
    failed: { bg: 'bg-red-900/50', text: 'text-red-300', dot: 'bg-red-400' },
    terminated: { bg: 'bg-yellow-900/50', text: 'text-yellow-300', dot: 'bg-yellow-400' },
    pending: { bg: 'bg-gray-700/50', text: 'text-gray-300', dot: 'bg-gray-400' },
    draft: { bg: 'bg-gray-700/50', text: 'text-gray-300', dot: 'bg-gray-400' },
    ready: { bg: 'bg-blue-900/50', text: 'text-blue-300', dot: 'bg-blue-400' },
    paused: { bg: 'bg-yellow-900/50', text: 'text-yellow-300', dot: 'bg-yellow-400' },
    stopped: { bg: 'bg-orange-900/50', text: 'text-orange-300', dot: 'bg-orange-400' },
    active: { bg: 'bg-green-900/50', text: 'text-green-300', dot: 'bg-green-400' },
    abandoned: { bg: 'bg-gray-700/50', text: 'text-gray-300', dot: 'bg-gray-400' },
  };

  // For agents, display 'idle' instead of 'completed'
  const displayStatus = isAgent && status === 'completed' ? 'idle' : status;
  const config = statusConfig[displayStatus] || statusConfig.pending;

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded font-medium ${sizeClasses} ${config.bg} ${config.text}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${config.dot} ${status === 'running' ? 'animate-pulse' : ''}`} />
      {displayStatus}
    </span>
  );
});

export default StatusBadge;
