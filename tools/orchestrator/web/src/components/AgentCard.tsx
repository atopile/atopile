import { useEffect, useState } from 'react';
import { Clock, Cpu, Trash2, Square } from 'lucide-react';
import type { AgentViewModel } from '@/logic/viewmodels';
import { StatusBadge } from './StatusBadge';

interface AgentCardProps {
  agent: AgentViewModel;
  selected?: boolean;
  onClick?: () => void;
  onTerminate?: () => void;
  onDelete?: () => void;
}

export function AgentCard({ agent, selected, onClick, onTerminate, onDelete }: AgentCardProps) {
  const [duration, setDuration] = useState<string>('');

  const isActivelyRunning = agent.status === 'running' || agent.status === 'starting';

  useEffect(() => {
    const updateDuration = () => {
      if (!agent.startedAt) {
        setDuration('—');
        return;
      }

      const start = new Date(agent.startedAt).getTime();
      if (isNaN(start)) {
        setDuration('—');
        return;
      }

      let end: number;
      if (agent.finishedAt) {
        end = new Date(agent.finishedAt).getTime();
        if (isNaN(end)) {
          setDuration('—');
          return;
        }
      } else if (isActivelyRunning) {
        end = Date.now();
      } else {
        setDuration('—'); // Finished but no end time
        return;
      }

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
    if (isActivelyRunning) {
      const interval = setInterval(updateDuration, 1000);
      return () => clearInterval(interval);
    }
  }, [agent.startedAt, agent.finishedAt, agent.status, isActivelyRunning]);

  return (
    <div
      className={`card p-3 cursor-pointer transition-all ${
        selected ? 'ring-2 ring-blue-500' : 'hover:border-gray-600'
      }`}
      onClick={onClick}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex flex-col min-w-0">
          {agent.name && (
            <span className="text-sm font-medium text-gray-200 truncate" title={agent.name}>
              {agent.name}
            </span>
          )}
          <code className="text-xs text-gray-500 font-mono">
            {agent.id.slice(0, 8)}
          </code>
        </div>
        <StatusBadge status={agent.status} size="sm" isAgent />
      </div>

      {/* Backend */}
      <div className="flex items-center gap-1.5 text-sm text-gray-300 mb-2">
        <Cpu className="w-4 h-4 text-gray-500" />
        <span>{agent.backend}</span>
      </div>

      {/* Stats */}
      <div className="flex items-center justify-between text-xs text-gray-500">
        <div className="flex items-center gap-1">
          <Clock className="w-3.5 h-3.5" />
          <span>{duration || '-'}</span>
        </div>
        <div className="flex items-center gap-1">
          {agent.canTerminate && onTerminate && (
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
          {agent.canDelete && onDelete && (
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
        <p className="text-xs text-gray-500 truncate" title={agent.prompt}>
          {agent.prompt}
        </p>
      </div>
    </div>
  );
}

export default AgentCard;
