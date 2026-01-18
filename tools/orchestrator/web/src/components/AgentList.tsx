import { useEffect } from 'react';
import { RefreshCw, Plus } from 'lucide-react';
import { useAgentStore } from '@/stores';
import { AgentCard } from './AgentCard';

interface AgentListProps {
  onSpawnClick?: () => void;
}

export function AgentList({ onSpawnClick }: AgentListProps) {
  const {
    agents,
    selectedAgentId,
    loading,
    fetchAgents,
    selectAgent,
    terminateAgent,
    deleteAgent,
  } = useAgentStore();

  useEffect(() => {
    fetchAgents();

    // Poll for updates every 5 seconds
    const interval = setInterval(fetchAgents, 5000);
    return () => clearInterval(interval);
  }, [fetchAgents]);

  const sortedAgents = Array.from(agents.values()).sort((a, b) => {
    // Running agents first
    const aRunning = ['running', 'starting', 'pending'].includes(a.status);
    const bRunning = ['running', 'starting', 'pending'].includes(b.status);
    if (aRunning && !bRunning) return -1;
    if (!aRunning && bRunning) return 1;

    // Then by created_at descending
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
  });

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-700">
        <h2 className="text-lg font-semibold">Agents</h2>
        <div className="flex items-center gap-2">
          <button
            className="btn btn-icon btn-secondary btn-sm"
            onClick={() => fetchAgents()}
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
              selected={selectedAgentId === agent.id}
              onClick={() => selectAgent(agent.id)}
              onTerminate={() => terminateAgent(agent.id)}
              onDelete={() => deleteAgent(agent.id)}
            />
          ))
        )}
      </div>
    </div>
  );
}

export default AgentList;
