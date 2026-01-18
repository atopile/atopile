import { useEffect, useState } from 'react';
import { Clock, Cpu, Trash2, Square } from 'lucide-react';
import type { AgentState } from '@/api/types';
import { StatusBadge } from './StatusBadge';

interface AgentCardProps {
  agent: AgentState;
  selected?: boolean;
  onClick?: () => void;
  onTerminate?: () => void;
  onDelete?: () => void;
}

export function AgentCard({ agent, selected, onClick, onTerminate, onDelete }: AgentCardProps) {
  const [duration, setDuration] = useState<string>('');

  useEffect(() => {
    const updateDuration = () => {
      if (!agent.started_at) {
        setDuration('');
        return;
      }

      const start = new Date(agent.started_at).getTime();
      const end = agent.finished_at
        ? new Date(agent.finished_at).getTime()
        : Date.now();
      const seconds = Math.floor((end - start) / 1000);

      if (seconds < 60) {
        setDuration(`${seconds}s`);
      } else if (seconds < 3600) {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        setDuration(`${mins}m ${secs}s`);
      } else {
        const hours = Math.floor(seconds / 3600);
        const mins = Math.floor((seconds % 3600) / 60);
        setDuration(`${hours}h ${mins}m`);
      }
    };

    updateDuration();

    // Update every second for running agents
    if (agent.status === 'running' || agent.status === 'starting') {
      const interval = setInterval(updateDuration, 1000);
      return () => clearInterval(interval);
    }
  }, [agent.started_at, agent.finished_at, agent.status]);

  const isRunning = agent.status === 'running' || agent.status === 'starting' || agent.status === 'pending';

  return (
    <div
      className={`card p-3 cursor-pointer transition-all ${
        selected ? 'ring-2 ring-blue-500' : 'hover:border-gray-600'
      }`}
      onClick={onClick}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <code className="text-sm text-gray-400 font-mono">
          {agent.id.slice(0, 8)}
        </code>
        <StatusBadge status={agent.status} size="sm" />
      </div>

      {/* Backend */}
      <div className="flex items-center gap-1.5 text-sm text-gray-300 mb-2">
        <Cpu className="w-4 h-4 text-gray-500" />
        <span>{agent.config.backend}</span>
      </div>

      {/* Stats */}
      <div className="flex items-center justify-between text-xs text-gray-500">
        <div className="flex items-center gap-1">
          <Clock className="w-3.5 h-3.5" />
          <span>{duration || '-'}</span>
        </div>
        <div className="flex items-center gap-1">
          {isRunning && onTerminate && (
            <button
              className="p-1 hover:bg-gray-700 rounded transition-colors"
              onClick={(e) => {
                e.stopPropagation();
                onTerminate();
              }}
              title="Terminate"
            >
              <Square className="w-3.5 h-3.5 text-red-400" />
            </button>
          )}
          {!isRunning && onDelete && (
            <button
              className="p-1 hover:bg-gray-700 rounded transition-colors"
              onClick={(e) => {
                e.stopPropagation();
                onDelete();
              }}
              title="Delete"
            >
              <Trash2 className="w-3.5 h-3.5 text-gray-400 hover:text-red-400" />
            </button>
          )}
        </div>
      </div>

      {/* Prompt preview */}
      <div className="mt-2 pt-2 border-t border-gray-700">
        <p className="text-xs text-gray-500 truncate" title={agent.config.prompt}>
          {agent.config.prompt}
        </p>
      </div>
    </div>
  );
}

export default AgentCard;
