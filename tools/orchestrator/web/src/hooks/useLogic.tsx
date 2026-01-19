/**
 * React bindings for the UILogic layer
 *
 * These hooks provide React components with access to the logic layer
 * while keeping the logic itself pure and testable.
 */

import {
  createContext,
  useContext,
  useEffect,
  useCallback,
  useMemo,
  useReducer,
  useRef,
  type ReactNode,
} from 'react';
import { UILogic, type UIState, type UIEvent, type AgentState } from '../logic';
import { getAgentOutput } from '../logic/state';
import type {
  AgentViewModel,
  AgentDetailViewModel,
  OutputViewModel,
  PipelineViewModel,
  PipelineSessionViewModel,
  PipelineEditorViewModel,
} from '../logic/viewmodels';

// Context for the logic instance
const LogicContext = createContext<UILogic | null>(null);

// Props for the provider
interface LogicProviderProps {
  children: ReactNode;
  logic: UILogic;
}

/**
 * Provider component that makes the logic instance available to all children
 */
export function LogicProvider({ children, logic }: LogicProviderProps) {
  return <LogicContext.Provider value={logic}>{children}</LogicContext.Provider>;
}

/**
 * Get the logic instance directly (for advanced use cases)
 */
export function useLogic(): UILogic {
  const logic = useContext(LogicContext);
  if (!logic) {
    throw new Error('useLogic must be used within a LogicProvider');
  }
  return logic;
}

/**
 * Subscribe to the full UI state
 * Uses forceUpdate pattern to ensure React re-renders on external state changes
 */
export function useUIState(): UIState {
  const logic = useLogic();
  const [, forceUpdate] = useReducer((x) => x + 1, 0);
  const stateRef = useRef(logic.getState());

  useEffect(() => {
    const unsubscribe = logic.subscribe((newState) => {
      stateRef.current = newState;
      forceUpdate();
    });
    return unsubscribe;
  }, [logic]);

  return stateRef.current;
}

/**
 * Get a dispatch function for sending events
 */
export function useDispatch(): (event: UIEvent) => Promise<void> {
  const logic = useLogic();
  return useCallback((event: UIEvent) => logic.dispatch(event), [logic]);
}

/**
 * Combined hook for state and dispatch
 */
export function useLogicState(): [UIState, (event: UIEvent) => Promise<void>] {
  const state = useUIState();
  const dispatch = useDispatch();
  return [state, dispatch];
}

// Selector hooks for specific parts of state

/**
 * Get the list of agents as view models
 */
export function useAgents(): AgentViewModel[] {
  const state = useUIState();

  return useMemo(() => {
    return Array.from(state.agents.values()).map(agentToViewModel);
  }, [state.agents]);
}

/**
 * Get a specific agent by ID
 */
export function useAgent(agentId: string | null): AgentViewModel | null {
  const state = useUIState();

  return useMemo(() => {
    if (!agentId) return null;
    const agent = state.agents.get(agentId);
    return agent ? agentToViewModel(agent) : null;
  }, [state.agents, agentId]);
}

/**
 * Get the selected agent
 */
export function useSelectedAgent(): AgentViewModel | null {
  const state = useUIState();
  return useAgent(state.selectedAgentId);
}

/**
 * Get the selected agent with detail information
 */
export function useSelectedAgentDetail(): AgentDetailViewModel | null {
  const state = useUIState();

  return useMemo(() => {
    if (!state.selectedAgentId) return null;
    const agent = state.agents.get(state.selectedAgentId);
    return agent ? agentToDetailViewModel(agent) : null;
  }, [state.agents, state.selectedAgentId]);
}

/**
 * Get running agents
 */
export function useRunningAgents(): AgentViewModel[] {
  const agents = useAgents();

  return useMemo(() => {
    return agents.filter((a) => a.isRunning);
  }, [agents]);
}

/**
 * Get output for a specific agent
 */
export function useAgentOutput(agentId: string | null): OutputViewModel {
  const state = useUIState();

  return useMemo(() => {
    if (!agentId) {
      return {
        chunks: [],
        prompts: [],
        currentRunNumber: 0,
        isConnected: false,
        hasHistory: false,
      };
    }

    const output = getAgentOutput(state, agentId);
    return {
      chunks: output.chunks,
      prompts: output.prompts,
      currentRunNumber: output.currentRunNumber,
      isConnected: output.isConnected,
      hasHistory: output.hasHistory,
    };
  }, [state.agentOutputs, agentId]);
}

/**
 * Get the list of pipelines as view models
 */
export function usePipelines(): PipelineViewModel[] {
  const state = useUIState();

  return useMemo(() => {
    return Array.from(state.pipelines.values()).map(pipelineToViewModel);
  }, [state.pipelines]);
}

/**
 * Get the selected pipeline
 */
export function useSelectedPipeline(): PipelineViewModel | null {
  const state = useUIState();

  return useMemo(() => {
    if (!state.selectedPipelineId) return null;
    const pipeline = state.pipelines.get(state.selectedPipelineId);
    return pipeline ? pipelineToViewModel(pipeline) : null;
  }, [state.pipelines, state.selectedPipelineId]);
}

/**
 * Get sessions for a pipeline
 */
export function usePipelineSessions(pipelineId: string | null): PipelineSessionViewModel[] {
  const state = useUIState();

  return useMemo(() => {
    if (!pipelineId) return [];
    const sessions = state.pipelineSessions.get(pipelineId) || [];
    return sessions.map(sessionToViewModel);
  }, [state.pipelineSessions, pipelineId]);
}

/**
 * Get the selected session
 */
export function useSelectedSession(): PipelineSessionViewModel | null {
  const state = useUIState();

  return useMemo(() => {
    if (!state.selectedSessionId || !state.selectedPipelineId) return null;
    const sessions = state.pipelineSessions.get(state.selectedPipelineId) || [];
    const session = sessions.find((s) => s.id === state.selectedSessionId);
    return session ? sessionToViewModel(session) : null;
  }, [state.pipelineSessions, state.selectedPipelineId, state.selectedSessionId]);
}

/**
 * Get the pipeline editor state
 */
export function useEditor(): PipelineEditorViewModel {
  const state = useUIState();

  return useMemo(() => ({
    nodes: state.editor.nodes,
    edges: state.editor.edges,
    name: state.editor.name,
    description: state.editor.description,
    config: state.editor.config,
    hasUnsavedChanges: state.editor.hasUnsavedChanges,
    selectedPipelineId: state.selectedPipelineId,
  }), [state.editor, state.selectedPipelineId]);
}

/**
 * Get loading state for an operation
 */
export function useLoading(key: string): boolean {
  const state = useUIState();
  return state.loading[key] ?? false;
}

/**
 * Get dialog state
 */
export function useDialog(dialog: string): { open: boolean; data?: unknown } {
  const state = useUIState();
  return state.dialogs[dialog] ?? { open: false };
}

/**
 * Get verbose mode setting
 */
export function useVerbose(): boolean {
  const state = useUIState();
  return state.verbose;
}

/**
 * Get current page
 */
export function useCurrentPage(): 'dashboard' | 'pipelines' {
  const state = useUIState();
  return state.currentPage;
}

/**
 * Get errors
 */
export function useErrors() {
  const state = useUIState();
  return state.errors;
}

// Helper functions to convert domain models to view models

function agentToViewModel(agent: AgentState): AgentViewModel {
  const isRunning =
    agent.status === 'running' ||
    agent.status === 'starting' ||
    agent.status === 'pending';

  const isFinished =
    agent.status === 'completed' ||
    agent.status === 'failed' ||
    agent.status === 'terminated';

  return {
    id: agent.id,
    name: agent.name ?? null,
    status: agent.status,
    backend: agent.config.backend,
    prompt: agent.config.prompt,
    sessionId: agent.session_id ?? null,
    createdAt: agent.created_at,
    startedAt: agent.started_at ?? null,
    finishedAt: agent.finished_at ?? null,
    outputChunks: agent.output_chunks,
    runCount: agent.run_count ?? 0,
    pid: agent.pid ?? null,
    exitCode: agent.exit_code ?? null,
    errorMessage: agent.error_message ?? null,
    maxTurns: agent.config.max_turns ?? null,

    // Computed
    isRunning,
    isFinished,
    canResume: isFinished && !!agent.session_id,
    canTerminate: isRunning,
    canDelete: isFinished,
  };
}

function agentToDetailViewModel(agent: AgentState): AgentDetailViewModel {
  const base = agentToViewModel(agent);
  return {
    ...base,
    workingDirectory: agent.config.working_directory ?? null,
    systemPrompt: agent.config.system_prompt ?? null,
    model: agent.config.model ?? null,
    environment: agent.config.environment ?? {},
  };
}

function pipelineToViewModel(pipeline: import('../logic').Pipeline): PipelineViewModel {
  const isRunning = pipeline.status === 'running' || pipeline.status === 'paused';

  return {
    id: pipeline.id,
    name: pipeline.name,
    description: pipeline.description ?? null,
    status: pipeline.status,
    nodeCount: pipeline.nodes.length,
    edgeCount: pipeline.edges.length,
    createdAt: pipeline.created_at,
    updatedAt: pipeline.updated_at,
    startedAt: pipeline.started_at ?? null,
    finishedAt: pipeline.finished_at ?? null,

    // Computed
    isRunning,
    isEditable: pipeline.status === 'draft' || pipeline.status === 'ready',
  };
}

function sessionToViewModel(session: import('../logic').PipelineSession): PipelineSessionViewModel {
  return {
    id: session.id,
    pipelineId: session.pipeline_id,
    status: session.status,
    nodeAgentMap: session.node_agent_map,
    nodeStatus: session.node_status,
    loopIterations: session.loop_iterations,
    loopWaitUntil: session.loop_wait_until ?? {},
    executionOrder: session.execution_order,
    startedAt: session.started_at,
    finishedAt: session.finished_at ?? null,
    errorMessage: session.error_message ?? null,

    // Computed
    isRunning: session.status === 'running',
  };
}
