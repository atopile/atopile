import { useEffect, useMemo, memo, useCallback } from 'react';
import { RefreshCw, Plus } from 'lucide-react';
import { useAgents, useUIState, useDispatch, useLoading } from '@/hooks';
import { AgentCard } from './AgentCard';

interface AgentListProps {
  onSpawnClick?: () => void;
}

export const AgentList = memo(function AgentList({ onSpawnClick }: AgentListProps) {
  const dispatch = useDispatch();
  const agents = useAgents();
  const state = useUIState();
  const loading = useLoading('agents');

  useEffect(() => {
    // Initial fetch - updates will come via WebSocket
    dispatch({ type: 'agents.refresh' });
  }, [dispatch]);

  const sortedAgents = useMemo(() => {
    return [...agents].sort((a, b) => {
      // Running agents first
      if (a.isRunning && !b.isRunning) return -1;
      if (!a.isRunning && b.isRunning) return 1;

      // Then by created_at descending
      return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
    });
  }, [agents]);

  const handleRefresh = useCallback(() => {
    dispatch({ type: 'agents.refresh' });
  }, [dispatch]);

  const handleSelect = useCallback((agentId: string) => {
    dispatch({ type: 'agents.select', payload: { agentId } });
  }, [dispatch]);

  const handleTerminate = useCallback((agentId: string) => {
    dispatch({ type: 'agents.terminate', payload: { agentId } });
  }, [dispatch]);

  const handleDelete = useCallback((agentId: string) => {
    dispatch({ type: 'agents.delete', payload: { agentId } });
  }, [dispatch]);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-700">
        <h2 className="text-lg font-semibold">Agents</h2>
        <div className="flex items-center gap-2">
          <button
            className="btn btn-icon btn-secondary btn-sm"
            onClick={handleRefresh}
            disabled={loading}
            title="Refresh"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          {onSpawnClick && (
            <button
              className="btn btn-primary btn-sm"
              onClick={onSpawnClick}
            >
              <Plus className="w-4 h-4 mr-1" />
              Spawn
            </button>
          )}
        </div>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {sortedAgents.length === 0 ? (
          <div className="text-center text-gray-500 py-8">
            <p>No agents yet</p>
            {onSpawnClick && (
              <button
                className="btn btn-primary btn-sm mt-4"
                onClick={onSpawnClick}
              >
                <Plus className="w-4 h-4 mr-1" />
                Spawn your first agent
              </button>
            )}
          </div>
        ) : (
          sortedAgents.map((agent) => (
            <AgentCard
              key={agent.id}
              agent={agent}
              selected={state.selectedAgentId === agent.id}
              onClick={() => handleSelect(agent.id)}
              onTerminate={() => handleTerminate(agent.id)}
              onDelete={() => handleDelete(agent.id)}
            />
          ))
        )}
      </div>
    </div>
  );
});

export default AgentList;
