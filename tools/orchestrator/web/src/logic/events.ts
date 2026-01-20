/**
 * UI Events - All possible user actions in the application
 * These are dispatched by the UI and handled by the logic layer
 */

import type { AgentBackendType, PipelineNode, PipelineEdge, PipelineConfig } from './api/types';

// Agent Events
export type AgentSpawnEvent = {
  type: 'agents.spawn';
  payload: {
    backend: AgentBackendType;
    prompt: string;
    name?: string;
    workingDirectory?: string;
    maxTurns?: number;
    maxBudgetUsd?: number;
    systemPrompt?: string;
    model?: string;
  };
};

export type AgentSelectEvent = {
  type: 'agents.select';
  payload: { agentId: string | null };
};

export type AgentTerminateEvent = {
  type: 'agents.terminate';
  payload: { agentId: string; force?: boolean };
};

export type AgentDeleteEvent = {
  type: 'agents.delete';
  payload: { agentId: string };
};

export type AgentSendInputEvent = {
  type: 'agents.sendInput';
  payload: { agentId: string; input: string };
};

export type AgentResumeEvent = {
  type: 'agents.resume';
  payload: { agentId: string; prompt: string };
};

export type AgentRenameEvent = {
  type: 'agents.rename';
  payload: { agentId: string; name: string };
};

export type AgentRefreshEvent = {
  type: 'agents.refresh';
  payload?: undefined;
};

export type AgentRefreshOneEvent = {
  type: 'agents.refreshOne';
  payload: { agentId: string };
};

// Output Events
export type OutputConnectEvent = {
  type: 'output.connect';
  payload: { agentId: string };
};

export type OutputDisconnectEvent = {
  type: 'output.disconnect';
  payload: { agentId: string };
};

export type OutputFetchEvent = {
  type: 'output.fetch';
  payload: { agentId: string; runNumber?: number };
};

export type OutputFetchHistoryEvent = {
  type: 'output.fetchHistory';
  payload: { agentId: string };
};

export type OutputClearEvent = {
  type: 'output.clear';
  payload: { agentId: string };
};

export type OutputSetRunNumberEvent = {
  type: 'output.setRunNumber';
  payload: { agentId: string; runNumber: number };
};

// Pipeline Events
export type PipelineSelectEvent = {
  type: 'pipelines.select';
  payload: { pipelineId: string | null };
};

export type PipelineCreateEvent = {
  type: 'pipelines.create';
  payload: {
    name: string;
    description?: string;
    nodes: PipelineNode[];
    edges: PipelineEdge[];
    config: PipelineConfig;
  };
};

export type PipelineUpdateEvent = {
  type: 'pipelines.update';
  payload: {
    pipelineId: string;
    name?: string;
    description?: string;
    nodes?: PipelineNode[];
    edges?: PipelineEdge[];
    config?: PipelineConfig;
  };
};

export type PipelineDeleteEvent = {
  type: 'pipelines.delete';
  payload: { pipelineId: string };
};

export type PipelineRunEvent = {
  type: 'pipelines.run';
  payload: { pipelineId: string };
};

export type PipelinePauseEvent = {
  type: 'pipelines.pause';
  payload: { pipelineId: string };
};

export type PipelineResumeEvent = {
  type: 'pipelines.resume';
  payload: { pipelineId: string };
};

export type PipelineStopEvent = {
  type: 'pipelines.stop';
  payload: { pipelineId: string };
};

export type PipelineRefreshEvent = {
  type: 'pipelines.refresh';
  payload?: undefined;
};

// Pipeline Session Events
export type SessionSelectEvent = {
  type: 'sessions.select';
  payload: { sessionId: string | null };
};

export type SessionFetchEvent = {
  type: 'sessions.fetch';
  payload: { pipelineId: string };
};

export type SessionStopEvent = {
  type: 'sessions.stop';
  payload: { pipelineId: string; sessionId: string; force?: boolean };
};

export type SessionDeleteEvent = {
  type: 'sessions.delete';
  payload: { pipelineId: string; sessionId: string; force?: boolean };
};

// Editor Events
export type EditorSetNodesEvent = {
  type: 'editor.setNodes';
  payload: { nodes: PipelineNode[] };
};

export type EditorSetEdgesEvent = {
  type: 'editor.setEdges';
  payload: { edges: PipelineEdge[] };
};

export type EditorSetNameEvent = {
  type: 'editor.setName';
  payload: { name: string };
};

export type EditorSetDescriptionEvent = {
  type: 'editor.setDescription';
  payload: { description: string };
};

export type EditorSetConfigEvent = {
  type: 'editor.setConfig';
  payload: { config: PipelineConfig };
};

export type EditorLoadPipelineEvent = {
  type: 'editor.loadPipeline';
  payload: { pipelineId: string };
};

export type EditorSaveEvent = {
  type: 'editor.save';
  payload?: undefined;
};

export type EditorResetEvent = {
  type: 'editor.reset';
  payload?: undefined;
};

// UI Events
export type UINavigateEvent = {
  type: 'ui.navigate';
  payload: { page: 'dashboard' | 'pipelines' };
};

export type UIToggleVerboseEvent = {
  type: 'ui.toggleVerbose';
  payload: { value: boolean };
};

// Dialog Events
export type DialogOpenEvent = {
  type: 'dialog.open';
  payload: { dialog: string; data?: unknown };
};

export type DialogCloseEvent = {
  type: 'dialog.close';
  payload: { dialog: string };
};

// Error Events
export type ErrorClearEvent = {
  type: 'error.clear';
  payload: { errorId: string };
};

export type ErrorClearAllEvent = {
  type: 'error.clearAll';
  payload?: undefined;
};

// Union of all events
export type UIEvent =
  // Agent events
  | AgentSpawnEvent
  | AgentSelectEvent
  | AgentTerminateEvent
  | AgentDeleteEvent
  | AgentSendInputEvent
  | AgentResumeEvent
  | AgentRenameEvent
  | AgentRefreshEvent
  | AgentRefreshOneEvent
  // Output events
  | OutputConnectEvent
  | OutputDisconnectEvent
  | OutputFetchEvent
  | OutputFetchHistoryEvent
  | OutputClearEvent
  | OutputSetRunNumberEvent
  // Pipeline events
  | PipelineSelectEvent
  | PipelineCreateEvent
  | PipelineUpdateEvent
  | PipelineDeleteEvent
  | PipelineRunEvent
  | PipelinePauseEvent
  | PipelineResumeEvent
  | PipelineStopEvent
  | PipelineRefreshEvent
  // Session events
  | SessionSelectEvent
  | SessionFetchEvent
  | SessionStopEvent
  | SessionDeleteEvent
  // Editor events
  | EditorSetNodesEvent
  | EditorSetEdgesEvent
  | EditorSetNameEvent
  | EditorSetDescriptionEvent
  | EditorSetConfigEvent
  | EditorLoadPipelineEvent
  | EditorSaveEvent
  | EditorResetEvent
  // UI events
  | UINavigateEvent
  | UIToggleVerboseEvent
  // Dialog events
  | DialogOpenEvent
  | DialogCloseEvent
  // Error events
  | ErrorClearEvent
  | ErrorClearAllEvent;
