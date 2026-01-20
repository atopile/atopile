import { useState, useEffect, useCallback, useRef } from 'react';
import { Activity, GitBranch, ChevronLeft, ChevronRight, Plus, Terminal, RotateCcw } from 'lucide-react';
import { useMobile, useAgents, usePipelines, useSelectedAgent, useUIState, useDispatch, useLogic } from '@/hooks';
import { AgentList } from './AgentList';
import { AgentDetail } from './AgentDetail';
import { SpawnAgentDialog } from './SpawnAgentDialog';
import { PipelineEditor, PipelineToolbar } from '@/pipeline';
import { PipelineSessionsPanel } from './PipelineSessionsPanel';

type ViewMode = 'agents' | 'pipelines';

// Narrow viewport threshold (between mobile and full desktop)
const NARROW_BREAKPOINT = 1024;

export function Layout() {
  const dispatch = useDispatch();
  const logic = useLogic();
  const isMobile = useMobile();
  const agents = useAgents();
  const pipelines = usePipelines();
  const selectedAgent = useSelectedAgent();
  const state = useUIState();

  const [viewMode, setViewMode] = useState<ViewMode>('agents');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    // Start collapsed on narrow viewports
    if (typeof window !== 'undefined') {
      return window.innerWidth < NARROW_BREAKPOINT && window.innerWidth >= 768;
    }
    return false;
  });
  const [spawnDialogOpen, setSpawnDialogOpen] = useState(false);
  const [showSessions, setShowSessions] = useState(false);
  const [restarting, setRestarting] = useState(false);

  // Track if user manually toggled sidebar (to prevent auto-collapse from overriding)
  const userToggledRef = useRef(false);
  const prevWidthRef = useRef(typeof window !== 'undefined' ? window.innerWidth : 1200);

  // Auto-collapse sidebar only when resizing from wide to narrow (not on user toggle)
  useEffect(() => {
    const checkWidth = () => {
      const currentWidth = window.innerWidth;
      const wasWide = prevWidthRef.current >= NARROW_BREAKPOINT;
      const isNowNarrow = currentWidth < NARROW_BREAKPOINT && currentWidth >= 768;

      // Only auto-collapse when transitioning from wide to narrow, and user hasn't manually toggled
      if (wasWide && isNowNarrow && !userToggledRef.current) {
        setSidebarCollapsed(true);
      }

      // Reset user toggle flag when going back to wide viewport
      if (currentWidth >= NARROW_BREAKPOINT) {
        userToggledRef.current = false;
      }

      prevWidthRef.current = currentWidth;
    };

    window.addEventListener('resize', checkWidth);
    return () => window.removeEventListener('resize', checkWidth);
  }, []);

  // Wrapper to track manual toggle
  const handleSidebarToggle = useCallback((collapsed: boolean) => {
    userToggledRef.current = true;
    setSidebarCollapsed(collapsed);
  }, []);

  const handleRestart = useCallback(async () => {
    if (restarting) return;
    setRestarting(true);
    try {
      await logic.api.restartServers();
      // Show restarting state for a few seconds while servers restart
      setTimeout(() => {
        window.location.reload();
      }, 3000);
    } catch (e) {
      console.error('Failed to restart servers:', e);
      setRestarting(false);
    }
  }, [logic.api, restarting]);

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
    // When viewing an agent detail, hide the header/tabs for more space
    const showMobileNav = !(viewMode === 'agents' && selectedAgent);

    return (
      <div className="flex flex-col h-screen bg-gray-900">
        {/* Mobile header + tabs - hidden when viewing agent detail */}
        {showMobileNav && (
          <header className="flex items-center justify-between px-3 py-1.5 bg-gray-800 border-b border-gray-700">
            <div className="flex items-center gap-1.5">
              <img src="/atopile-logo.svg" alt="atopile" className="w-4 h-4" />
              <span className="text-sm font-medium">Orchestrator</span>
            </div>
            {/* Compact tabs inline */}
            <div className="flex items-center gap-1">
              <button
                className={`px-2 py-1 text-xs font-medium rounded flex items-center gap-1 ${viewMode === 'agents' ? 'bg-blue-600 text-white' : 'text-gray-400'}`}
                onClick={() => setViewMode('agents')}
              >
                <Activity className="w-3 h-3" />
                {runningAgentsCount > 0 && (
                  <span className="text-[10px] text-green-300">{runningAgentsCount}</span>
                )}
              </button>
              <button
                className={`px-2 py-1 text-xs font-medium rounded flex items-center gap-1 ${viewMode === 'pipelines' ? 'bg-blue-600 text-white' : 'text-gray-400'}`}
                onClick={() => setViewMode('pipelines')}
              >
                <GitBranch className="w-3 h-3" />
                {runningPipelinesCount > 0 && (
                  <span className="text-[10px] text-green-300">{runningPipelinesCount}</span>
                )}
              </button>
            </div>
          </header>
        )}

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
      <aside className={`flex flex-col border-r border-gray-700 bg-gray-900 transition-all duration-200 relative ${sidebarCollapsed ? 'w-14' : 'w-80'}`}>
        {/* Expand handle - visible edge when collapsed */}
        {sidebarCollapsed && (
          <button
            className="absolute right-0 top-1/2 -translate-y-1/2 translate-x-1/2 z-10 w-6 h-12 bg-gray-800 border border-gray-600 rounded-r-md flex items-center justify-center hover:bg-gray-700 hover:border-gray-500 transition-colors group"
            onClick={() => handleSidebarToggle(false)}
            title="Expand sidebar"
          >
            <ChevronRight className="w-4 h-4 text-gray-400 group-hover:text-gray-200" />
          </button>
        )}

        {/* Logo and collapse toggle */}
        <div className={`flex items-center border-b border-gray-700 ${sidebarCollapsed ? 'flex-col p-2 gap-2' : 'justify-between p-3'}`}>
          {!sidebarCollapsed && (
            <div className="flex items-center gap-2">
              <img src="/atopile-logo.svg" alt="atopile" className="w-5 h-5" />
              <span className="text-sm font-semibold">Orchestrator</span>
            </div>
          )}
          {sidebarCollapsed && (
            <img src="/atopile-logo.svg" alt="atopile" className="w-5 h-5" />
          )}
          <div className={`flex items-center ${sidebarCollapsed ? 'flex-col gap-2' : 'gap-1'}`}>
            <button
              className={`p-2 hover:bg-gray-700 rounded text-gray-400 hover:text-gray-200 ${restarting ? 'animate-spin' : ''}`}
              onClick={handleRestart}
              disabled={restarting}
              title="Restart servers"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
            {!sidebarCollapsed && (
              <button
                className="p-2 hover:bg-gray-700 rounded text-gray-400 hover:text-gray-200"
                onClick={() => handleSidebarToggle(true)}
                title="Collapse sidebar"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
            )}
          </div>
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
                onOpenPipelineList={() => handleSidebarToggle(false)}
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
