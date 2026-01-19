import { useState, useEffect, useCallback } from 'react';
import { Activity, GitBranch, ChevronLeft, ChevronRight, Plus, Terminal } from 'lucide-react';
import { useMobile, useAgents, usePipelines, useSelectedAgent, useUIState, useDispatch } from '@/hooks';
import { AgentList } from './AgentList';
import { AgentDetail } from './AgentDetail';
import { SpawnAgentDialog } from './SpawnAgentDialog';
import { PipelineEditor, PipelineToolbar } from '@/pipeline';
import { PipelineSessionsPanel } from './PipelineSessionsPanel';

type ViewMode = 'agents' | 'pipelines';

export function Layout() {
  const dispatch = useDispatch();
  const isMobile = useMobile();
  const agents = useAgents();
  const pipelines = usePipelines();
  const selectedAgent = useSelectedAgent();
  const state = useUIState();

  const [viewMode, setViewMode] = useState<ViewMode>('agents');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [spawnDialogOpen, setSpawnDialogOpen] = useState(false);
  const [showSessions, setShowSessions] = useState(false);

  // Load initial data
  useEffect(() => {
    dispatch({ type: 'agents.refresh' });
    dispatch({ type: 'pipelines.refresh' });
  }, [dispatch]);

  const handleClose = useCallback(() => {
    if (viewMode === 'agents') {
      dispatch({ type: 'agents.select', payload: { agentId: null } });
    } else {
      dispatch({ type: 'pipelines.select', payload: { pipelineId: null } });
    }
  }, [dispatch, viewMode]);

  const runningAgentsCount = agents.filter(a => a.isRunning).length;
  const runningPipelinesCount = pipelines.filter(p => p.isRunning).length;

  // Mobile layout
  if (isMobile) {
    return (
      <div className="flex flex-col h-screen bg-gray-900">
        {/* Mobile header */}
        <header className="mobile-header">
          <div className="flex items-center gap-2">
            <img src="/atopile-logo.svg" alt="atopile" className="w-5 h-5" />
            <span className="font-semibold">Orchestrator</span>
          </div>
        </header>

        {/* View selector tabs */}
        <div className="flex border-b border-gray-700 bg-gray-800">
          <button
            className={`flex-1 py-2 px-4 text-sm font-medium flex items-center justify-center gap-2 ${viewMode === 'agents' ? 'text-blue-400 border-b-2 border-blue-400' : 'text-gray-400'}`}
            onClick={() => setViewMode('agents')}
          >
            <Activity className="w-4 h-4" />
            Agents
            {runningAgentsCount > 0 && (
              <span className="px-1.5 py-0.5 text-xs rounded-full bg-green-900/50 text-green-300">
                {runningAgentsCount}
              </span>
            )}
          </button>
          <button
            className={`flex-1 py-2 px-4 text-sm font-medium flex items-center justify-center gap-2 ${viewMode === 'pipelines' ? 'text-blue-400 border-b-2 border-blue-400' : 'text-gray-400'}`}
            onClick={() => setViewMode('pipelines')}
          >
            <GitBranch className="w-4 h-4" />
            Pipelines
            {runningPipelinesCount > 0 && (
              <span className="px-1.5 py-0.5 text-xs rounded-full bg-green-900/50 text-green-300">
                {runningPipelinesCount}
              </span>
            )}
          </button>
        </div>

        {/* Main content */}
        <main className="flex-1 overflow-hidden">
          {viewMode === 'agents' ? (
            selectedAgent ? (
              <AgentDetail agent={selectedAgent} onClose={handleClose} />
            ) : (
              <AgentList onSpawnClick={() => setSpawnDialogOpen(true)} />
            )
          ) : (
            <div className="flex flex-col h-full">
              <PipelineToolbar
                onOpenPipelineList={() => {}}
                onToggleSessions={() => setShowSessions(!showSessions)}
                showSessions={showSessions}
                isMobile={true}
              />
              <PipelineEditor />
            </div>
          )}
        </main>

        <SpawnAgentDialog open={spawnDialogOpen} onClose={() => setSpawnDialogOpen(false)} />
      </div>
    );
  }

  // Desktop layout
  return (
    <div className="flex h-screen bg-gray-900">
      {/* Sidebar */}
      <aside className={`flex flex-col border-r border-gray-700 bg-gray-900 transition-all duration-200 ${sidebarCollapsed ? 'w-12' : 'w-80'}`}>
        {/* Logo and collapse toggle */}
        <div className="flex items-center justify-between p-3 border-b border-gray-700">
          {!sidebarCollapsed && (
            <div className="flex items-center gap-2">
              <img src="/atopile-logo.svg" alt="atopile" className="w-5 h-5" />
              <span className="text-sm font-semibold">Orchestrator</span>
            </div>
          )}
          <button
            className="p-1 hover:bg-gray-700 rounded text-gray-400 hover:text-gray-200"
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            title={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {sidebarCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
        </div>

        {/* View mode selector */}
        <div className={`flex ${sidebarCollapsed ? 'flex-col p-1 gap-1' : 'p-2 gap-1'} border-b border-gray-700`}>
          <button
            className={`${sidebarCollapsed ? 'p-2' : 'flex-1 py-1.5 px-3'} rounded text-xs font-medium flex items-center ${sidebarCollapsed ? 'justify-center' : 'justify-center gap-2'} transition-colors ${viewMode === 'agents' ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'}`}
            onClick={() => setViewMode('agents')}
            title="Agents"
          >
            <Activity className="w-4 h-4" />
            {!sidebarCollapsed && 'Agents'}
            {runningAgentsCount > 0 && !sidebarCollapsed && (
              <span className="px-1.5 py-0.5 text-[10px] rounded-full bg-green-900/50 text-green-300">
                {runningAgentsCount}
              </span>
            )}
          </button>
          <button
            className={`${sidebarCollapsed ? 'p-2' : 'flex-1 py-1.5 px-3'} rounded text-xs font-medium flex items-center ${sidebarCollapsed ? 'justify-center' : 'justify-center gap-2'} transition-colors ${viewMode === 'pipelines' ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'}`}
            onClick={() => setViewMode('pipelines')}
            title="Pipelines"
          >
            <GitBranch className="w-4 h-4" />
            {!sidebarCollapsed && 'Pipelines'}
            {runningPipelinesCount > 0 && !sidebarCollapsed && (
              <span className="px-1.5 py-0.5 text-[10px] rounded-full bg-green-900/50 text-green-300">
                {runningPipelinesCount}
              </span>
            )}
          </button>
        </div>

        {/* List content */}
        {!sidebarCollapsed && (
          <div className="flex-1 overflow-hidden">
            {viewMode === 'agents' ? (
              <AgentList onSpawnClick={() => setSpawnDialogOpen(true)} />
            ) : (
              <PipelineList />
            )}
          </div>
        )}

      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-hidden flex">
        <div className="flex-1 overflow-hidden">
          {viewMode === 'agents' ? (
            selectedAgent ? (
              <AgentDetail agent={selectedAgent} onClose={handleClose} />
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
            )
          ) : (
            <div className="flex flex-col h-full">
              <PipelineToolbar
                onOpenPipelineList={() => setSidebarCollapsed(false)}
                onToggleSessions={() => setShowSessions(!showSessions)}
                showSessions={showSessions}
              />
              <PipelineEditor />
            </div>
          )}
        </div>

        {/* Sessions panel for pipelines */}
        {viewMode === 'pipelines' && showSessions && state.selectedPipelineId && (
          <div className="w-80 border-l border-gray-700 bg-gray-900">
            <PipelineSessionsPanel
              pipelineId={state.selectedPipelineId}
              onClose={() => setShowSessions(false)}
            />
          </div>
        )}
      </main>

      <SpawnAgentDialog open={spawnDialogOpen} onClose={() => setSpawnDialogOpen(false)} />
    </div>
  );
}

// Pipeline list component (extracted from Pipelines.tsx)
function PipelineList() {
  const dispatch = useDispatch();
  const pipelines = usePipelines();
  const state = useUIState();
  const selectedPipelineId = state.selectedPipelineId;

  const sortedPipelines = [...pipelines].sort((a, b) => {
    if (a.isRunning && !b.isRunning) return -1;
    if (!a.isRunning && b.isRunning) return 1;
    return new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime();
  });

  const handleNewPipeline = () => {
    dispatch({ type: 'editor.reset' });
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between p-3 border-b border-gray-700">
        <span className="text-sm text-gray-400">{pipelines.length} pipelines</span>
        <button
          className="btn btn-primary btn-sm"
          onClick={handleNewPipeline}
          title="New pipeline"
        >
          <Plus className="w-4 h-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {sortedPipelines.length === 0 ? (
          <div className="text-center text-gray-500 py-8 text-sm">
            <p>No pipelines yet</p>
            <button
              className="btn btn-primary btn-sm mt-4"
              onClick={handleNewPipeline}
            >
              Create your first pipeline
            </button>
          </div>
        ) : (
          sortedPipelines.map((pipeline) => (
            <div
              key={pipeline.id}
              className={`p-2 rounded cursor-pointer transition-colors ${
                selectedPipelineId === pipeline.id
                  ? 'bg-blue-600/20 border border-blue-500/50'
                  : 'hover:bg-gray-800 border border-transparent'
              }`}
              onClick={() => dispatch({ type: 'pipelines.select', payload: { pipelineId: pipeline.id } })}
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium truncate">{pipeline.name}</span>
                {pipeline.isRunning && (
                  <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
                )}
              </div>
              <div className="text-xs text-gray-500 mt-0.5">
                {pipeline.nodeCount} nodes
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export default Layout;
