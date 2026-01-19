/**
 * View Models - UI-specific representations of domain data
 * These are derived from API types but shaped for efficient rendering
 */

import type {
  AgentStatus,
  AgentBackendType,
  OutputChunk,
  PipelineStatus,
  PipelineSessionStatus,
  PipelineNode,
  PipelineEdge,
  PipelineConfig,
} from './api/types';

// Agent View Models
export interface AgentViewModel {
  id: string;
  name: string | null;
  status: AgentStatus;
  backend: AgentBackendType;
  prompt: string;
  sessionId: string | null;
  createdAt: string;
  startedAt: string | null;
  finishedAt: string | null;
  outputChunks: number;
  runCount: number;
  pid: number | null;
  exitCode: number | null;
  errorMessage: string | null;
  maxTurns: number | null;

  // Computed for display
  isRunning: boolean;
  isFinished: boolean;
  canResume: boolean;
  canTerminate: boolean;
  canDelete: boolean;
}

export interface AgentDetailViewModel extends AgentViewModel {
  // Extended detail fields
  workingDirectory: string | null;
  systemPrompt: string | null;
  model: string | null;
  environment: Record<string, string>;
}

// Output View Models
export interface PromptInfo {
  run: number;
  prompt: string;
}

export interface OutputViewModel {
  chunks: OutputChunk[];
  prompts: PromptInfo[];
  currentRunNumber: number;
  isConnected: boolean;
  hasHistory: boolean;
}

// Pipeline View Models
export interface PipelineViewModel {
  id: string;
  name: string;
  description: string | null;
  status: PipelineStatus;
  nodeCount: number;
  edgeCount: number;
  createdAt: string;
  updatedAt: string;
  startedAt: string | null;
  finishedAt: string | null;

  // Computed for display
  isRunning: boolean;
  isEditable: boolean;
}

export interface PipelineSessionViewModel {
  id: string;
  pipelineId: string;
  status: PipelineSessionStatus;
  nodeAgentMap: Record<string, string>;
  nodeStatus: Record<string, string>;
  loopIterations: Record<string, number>;
  loopWaitUntil: Record<string, string>;  // node_id -> ISO datetime when loop will resume
  executionOrder: string[];
  startedAt: string;
  finishedAt: string | null;
  errorMessage: string | null;

  // Computed
  isRunning: boolean;
}

// Editor View Model
export interface PipelineEditorViewModel {
  nodes: PipelineNode[];
  edges: PipelineEdge[];
  name: string;
  description: string;
  config: PipelineConfig;
  hasUnsavedChanges: boolean;
  selectedPipelineId: string | null;
}

// Error View Model
export interface ErrorViewModel {
  id: string;
  message: string;
  timestamp: string;
  source: string;
}

// Dialog state
export type DialogType =
  | 'spawn-agent'
  | 'confirm-delete-agent'
  | 'confirm-delete-pipeline'
  | 'pipeline-sessions';
