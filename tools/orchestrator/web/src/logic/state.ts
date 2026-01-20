/**
 * UI State - The complete state of the application
 * This is pure data with no React dependencies
 */

import type {
  AgentState,
  Pipeline,
  PipelineSession,
  PipelineNode,
  PipelineEdge,
  PipelineConfig,
  OutputChunk,
} from './api/types';
import type { PromptInfo, ErrorViewModel } from './viewmodels';

// Output state per agent
export interface AgentOutputState {
  chunks: OutputChunk[];
  prompts: PromptInfo[];
  isConnected: boolean;
  hasHistory: boolean;
  currentRunNumber: number;
}

// Editor state for pipeline editing
export interface EditorState {
  nodes: PipelineNode[];
  edges: PipelineEdge[];
  name: string;
  description: string;
  config: PipelineConfig;
  hasUnsavedChanges: boolean;
}

// Complete UI State
export interface UIState {
  // Version counter - incremented on every state update to ensure React detects changes
  _version: number;

  // Current page/route
  currentPage: 'dashboard' | 'pipelines';

  // Dashboard state
  agents: Map<string, AgentState>;
  selectedAgentId: string | null;
  agentOutputs: Map<string, AgentOutputState>;

  // Pipelines state
  pipelines: Map<string, Pipeline>;
  selectedPipelineId: string | null;
  pipelineSessions: Map<string, PipelineSession[]>; // pipeline_id -> sessions
  selectedSessionId: string | null;

  // Editor state
  editor: EditorState;

  // UI preferences
  verbose: boolean;

  // Dialogs/modals
  dialogs: Record<string, { open: boolean; data?: unknown }>;

  // Loading states (keyed by operation identifier)
  loading: Record<string, boolean>;

  // Global errors
  errors: ErrorViewModel[];
}

// Default pipeline config
export const defaultPipelineConfig: PipelineConfig = {
  parallel_execution: false,
  stop_on_failure: true,
};

// Initial state factory
export function createInitialState(): UIState {
  return {
    _version: 0,

    currentPage: 'dashboard',

    agents: new Map(),
    selectedAgentId: null,
    agentOutputs: new Map(),

    pipelines: new Map(),
    selectedPipelineId: null,
    pipelineSessions: new Map(),
    selectedSessionId: null,

    editor: {
      nodes: [],
      edges: [],
      name: 'New Pipeline',
      description: '',
      config: defaultPipelineConfig,
      hasUnsavedChanges: false,
    },

    verbose: false,

    dialogs: {},
    loading: {},
    errors: [],
  };
}

// State helper functions
export function createAgentOutputState(): AgentOutputState {
  return {
    chunks: [],
    prompts: [],
    isConnected: false,
    hasHistory: false,
    currentRunNumber: 0,
  };
}

export function getAgentOutput(state: UIState, agentId: string): AgentOutputState {
  return state.agentOutputs.get(agentId) || createAgentOutputState();
}

export function setAgentOutput(
  state: UIState,
  agentId: string,
  updater: (output: AgentOutputState) => AgentOutputState
): UIState {
  const current = getAgentOutput(state, agentId);
  const updated = updater(current);
  const newOutputs = new Map(state.agentOutputs);
  newOutputs.set(agentId, updated);
  return { ...state, agentOutputs: newOutputs };
}

export function setLoading(state: UIState, key: string, value: boolean): UIState {
  return {
    ...state,
    loading: { ...state.loading, [key]: value },
  };
}

export function addError(state: UIState, message: string, source: string): UIState {
  const error: ErrorViewModel = {
    id: `error-${Date.now()}-${Math.random().toString(36).slice(2)}`,
    message,
    timestamp: new Date().toISOString(),
    source,
  };
  return {
    ...state,
    errors: [...state.errors, error],
  };
}

export function clearError(state: UIState, errorId: string): UIState {
  return {
    ...state,
    errors: state.errors.filter((e) => e.id !== errorId),
  };
}

export function clearAllErrors(state: UIState): UIState {
  return {
    ...state,
    errors: [],
  };
}

// Immutable Map update helpers
export function updateMap<K, V>(map: Map<K, V>, key: K, value: V): Map<K, V> {
  const newMap = new Map(map);
  newMap.set(key, value);
  return newMap;
}

export function deleteFromMap<K, V>(map: Map<K, V>, key: K): Map<K, V> {
  const newMap = new Map(map);
  newMap.delete(key);
  return newMap;
}

export function updateMapItem<K, V>(
  map: Map<K, V>,
  key: K,
  updater: (value: V) => V
): Map<K, V> {
  const current = map.get(key);
  if (current === undefined) {
    return map;
  }
  const newMap = new Map(map);
  newMap.set(key, updater(current));
  return newMap;
}
