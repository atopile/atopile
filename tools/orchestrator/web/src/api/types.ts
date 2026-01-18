// Agent types
export type AgentStatus = 'pending' | 'starting' | 'running' | 'completed' | 'failed' | 'terminated';
export type AgentBackendType = 'claude-code' | 'codex' | 'cursor';
export type OutputType = 'system' | 'assistant' | 'tool_use' | 'tool_result' | 'error' | 'raw' | 'result' | 'text_delta' | 'stream_start' | 'stream_stop';

export interface AgentConfig {
  backend: AgentBackendType;
  prompt: string;
  working_directory?: string;
  session_id?: string;
  resume_session?: boolean;
  max_turns?: number;
  max_budget_usd?: number;
  allowed_tools?: string[];
  disallowed_tools?: string[];
  system_prompt?: string;
  model?: string;
  timeout_seconds?: number;
  environment?: Record<string, string>;
  extra_args?: string[];
}

export interface AgentState {
  id: string;
  config: AgentConfig;
  status: AgentStatus;
  pid?: number;
  exit_code?: number;
  error_message?: string;
  session_id?: string;
  created_at: string;
  started_at?: string;
  finished_at?: string;
  output_chunks: number;
  last_activity_at?: string;
  metadata: Record<string, unknown>;
}

export interface OutputChunk {
  type: OutputType;
  content?: string;
  tool_name?: string;
  tool_input?: Record<string, unknown>;
  tool_result?: string;
  raw_line?: string;
  data?: Record<string, unknown>;
  timestamp: string;
  sequence: number;
  is_error?: boolean;
}

// Session types
export type SessionStatus = 'active' | 'paused' | 'completed' | 'abandoned';

export interface SessionMetadata {
  id: string;
  backend: AgentBackendType;
  backend_session_id?: string;
  created_at: string;
  updated_at: string;
  working_directory?: string;
  initial_prompt?: string;
  total_turns: number;
  total_cost_usd: number;
  tags: string[];
  custom_data: Record<string, unknown>;
}

export interface SessionState {
  metadata: SessionMetadata;
  status: SessionStatus;
  agent_runs: string[];
  last_agent_id?: string;
}

// API Response types
export interface AgentListResponse {
  agents: AgentState[];
  total: number;
}

export interface AgentStateResponse {
  agent: AgentState;
}

export interface AgentOutputResponse {
  agent_id: string;
  chunks: OutputChunk[];
  total_chunks: number;
}

export interface SpawnAgentRequest {
  config: AgentConfig;
}

export interface SpawnAgentResponse {
  agent_id: string;
  status: AgentStatus;
  message: string;
}

export interface TerminateAgentRequest {
  force?: boolean;
  timeout_seconds?: number;
}

export interface TerminateAgentResponse {
  agent_id: string;
  success: boolean;
  message: string;
}

export interface SendInputRequest {
  input: string;
  newline?: boolean;
}

export interface SendInputResponse {
  success: boolean;
  message: string;
}

export interface SessionListResponse {
  sessions: SessionMetadata[];
  total: number;
}

export interface SessionStateResponse {
  session: SessionState;
}

export interface BackendInfo {
  type: AgentBackendType;
  binary: string;
  path: string;
  capabilities: {
    streaming: boolean;
    resume: boolean;
    session_persistence: boolean;
    input_during_run: boolean;
    tools: boolean;
    budget_control: boolean;
    max_turns: boolean;
    allowed_tools: boolean;
  };
}

export interface BackendsResponse {
  backends: BackendInfo[];
}

export interface StatsResponse {
  agents: {
    total: number;
    running: number;
    completed: number;
    failed: number;
  };
  sessions: {
    total: number;
  };
  backends: {
    available: string[];
  };
  websockets: {
    connections: number;
  };
}

export interface HealthResponse {
  status: string;
  timestamp: string;
}

// WebSocket event types
export type StreamEventType =
  | 'connected'
  | 'agent_started'
  | 'agent_output'
  | 'agent_completed'
  | 'agent_failed'
  | 'agent_terminated'
  | 'error'
  | 'ping'
  | 'pong';

export interface StreamEvent {
  type: StreamEventType;
  agent_id: string;
  chunk?: OutputChunk;
  message?: string;
  data?: Record<string, unknown>;
  timestamp: string;
}

// Pipeline types
export type PipelineStatus = 'draft' | 'ready' | 'running' | 'paused' | 'completed' | 'failed';
export type PipelineNodeType = 'agent' | 'trigger' | 'condition' | 'loop';
export type TriggerType = 'manual' | 'timer' | 'webhook';

export interface PipelineNodePosition {
  x: number;
  y: number;
}

export interface AgentNodeData {
  name: string;
  backend: AgentBackendType;
  prompt: string;
  system_prompt?: string;
  planning_file?: string;
  max_turns?: number;
  max_budget_usd?: number;
  working_directory?: string;
  environment?: Record<string, string>;
}

export interface TriggerNodeData {
  trigger_type: TriggerType;
  interval_seconds?: number;
  cron_expression?: string;
}

export interface LoopNodeData {
  duration_seconds: number;
  restart_on_complete: boolean;
  restart_on_fail: boolean;
  max_iterations?: number;
}

export interface ConditionNodeData {
  expression: string;
}

export type PipelineNodeData = AgentNodeData | TriggerNodeData | LoopNodeData | ConditionNodeData;

export interface PipelineNode {
  id: string;
  type: PipelineNodeType;
  position: PipelineNodePosition;
  data: PipelineNodeData;
}

export interface PipelineEdge {
  id: string;
  source: string;
  target: string;
  source_handle?: string;
  label?: string;
}

export interface PipelineConfig {
  parallel_execution: boolean;
  stop_on_failure: boolean;
  notification_webhook?: string;
}

export interface Pipeline {
  id: string;
  name: string;
  description?: string;
  nodes: PipelineNode[];
  edges: PipelineEdge[];
  config: PipelineConfig;
  status: PipelineStatus;
  current_node_id?: string;
  execution_history: string[];
  node_agent_map: Record<string, string>;  // node_id -> agent_id
  node_status: Record<string, string>;     // node_id -> status
  created_at: string;
  updated_at: string;
  started_at?: string;
  finished_at?: string;
}

export interface PipelineListResponse {
  pipelines: Pipeline[];
  total: number;
}

export interface CreatePipelineRequest {
  name: string;
  description?: string;
  nodes: PipelineNode[];
  edges: PipelineEdge[];
  config: PipelineConfig;
}
