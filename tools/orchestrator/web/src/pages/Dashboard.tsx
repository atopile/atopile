import { useState } from 'react';
import { Terminal } from 'lucide-react';
import { useAgentStore } from '@/stores';
import { AgentList, AgentDetail, SpawnAgentDialog } from '@/components';

export function Dashboard() {
  const { getSelectedAgent, selectAgent } = useAgentStore();
  const [spawnDialogOpen, setSpawnDialogOpen] = useState(false);

  const selectedAgent = getSelectedAgent();

  return (
    <div className="flex h-full">
      {/* Agent list sidebar */}
      <div className="w-80 border-r border-gray-700 flex-shrink-0">
        <AgentList onSpawnClick={() => setSpawnDialogOpen(true)} />
      </div>

      {/* Main content */}
      <div className="flex-1 overflow-hidden">
        {selectedAgent ? (
          <AgentDetail
            agent={selectedAgent}
            onClose={() => selectAgent(null)}
          />
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-gray-500">
            <Terminal className="w-16 h-16 mb-4 opacity-50" />
            <p className="text-lg">Select an agent to view details</p>
            <p className="text-sm mt-2">
              or{' '}
              <button
                className="text-blue-400 hover:text-blue-300"
                onClick={() => setSpawnDialogOpen(true)}
              >
                spawn a new agent
              </button>
            </p>
          </div>
        )}
      </div>

      {/* Spawn dialog */}
      <SpawnAgentDialog
        open={spawnDialogOpen}
        onClose={() => setSpawnDialogOpen(false)}
      />
    </div>
  );
}

export default Dashboard;
