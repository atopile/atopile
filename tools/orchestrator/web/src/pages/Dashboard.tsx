import { useState, useEffect } from 'react';
import { Terminal, ArrowLeft } from 'lucide-react';
import { useSelectedAgent, useDispatch, useMobile } from '@/hooks';
import { AgentList, AgentDetail, SpawnAgentDialog } from '@/components';

type MobileView = 'list' | 'detail';

export function Dashboard() {
  const dispatch = useDispatch();
  const selectedAgent = useSelectedAgent();
  const isMobile = useMobile();
  const [spawnDialogOpen, setSpawnDialogOpen] = useState(false);
  const [mobileView, setMobileView] = useState<MobileView>('list');

  // When agent is selected on mobile, switch to detail view
  useEffect(() => {
    if (isMobile && selectedAgent) {
      setMobileView('detail');
    }
  }, [isMobile, selectedAgent]);

  const handleClose = () => {
    dispatch({ type: 'agents.select', payload: { agentId: null } });
    if (isMobile) {
      setMobileView('list');
    }
  };

  const handleBackToList = () => {
    setMobileView('list');
    dispatch({ type: 'agents.select', payload: { agentId: null } });
  };

  // Mobile layout
  if (isMobile) {
    return (
      <div className="flex flex-col h-full">
        {mobileView === 'list' ? (
          <AgentList onSpawnClick={() => setSpawnDialogOpen(true)} />
        ) : (
          <div className="flex flex-col h-full">
            {/* Mobile back header */}
            <div className="mobile-back-header">
              <button
                className="mobile-back-button"
                onClick={handleBackToList}
              >
                <ArrowLeft className="w-5 h-5" />
                <span>Agents</span>
              </button>
            </div>
            {selectedAgent ? (
              <AgentDetail
                agent={selectedAgent}
                onClose={handleClose}
              />
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-gray-500 p-4">
                <Terminal className="w-12 h-12 mb-4 opacity-50" />
                <p>No agent selected</p>
              </div>
            )}
          </div>
        )}

        <SpawnAgentDialog
          open={spawnDialogOpen}
          onClose={() => setSpawnDialogOpen(false)}
        />
      </div>
    );
  }

  // Desktop layout
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
            onClose={handleClose}
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
