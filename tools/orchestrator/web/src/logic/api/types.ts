// Agent types
export type AgentStatus = 'pending' | 'starting' | 'running' | 'completed' | 'failed' | 'terminated';
export type AgentBackendType = 'claude-code' | 'codex' | 'cursor';
export type OutputType = 'system' | 'assistant' | 'tool_use' | 'tool_result' | 'error' | 'raw' | 'result' | 'text_delta' | 'stream_start' | 'stream_stop';
export type TodoStatus = 'pending' | 'in_progress' | 'completed';

export interface TodoItem {
  content: string;
  status: TodoStatus;
  active_form?: string;
}

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
  name?: string;
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
  run_count?: number;
  metadata: Record<string, unknown>;
  todos?: TodoItem[];
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
  run_number?: number;
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

export interface RunOutput {
  run_number: number;
  prompt?: string;
  chunks: OutputChunk[];
  started_at?: string;
}

export interface AgentHistoryResponse {
  agent_id: string;
  runs: RunOutput[];
  total_runs: number;
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

export interface ImportSessionRequest {
  session_id: string;
  prompt: string;
  name?: string;
  backend?: AgentBackendType;
  working_directory?: string;
  model?: string;
  max_turns?: number;
  max_budget_usd?: number;
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
export type PipelineNodeType = 'agent' | 'trigger' | 'condition' | 'wait';
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

export interface WaitNodeData {
  duration_seconds: number;
}

export interface ConditionNodeData {
  count_limit?: number;
  time_limit_seconds?: number;
}

export type PipelineNodeData = AgentNodeData | TriggerNodeData | ConditionNodeData | WaitNodeData;

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
  node_agent_map: Record<string, string>;
  node_status: Record<string, string>;
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

// Pipeline Session types
export type PipelineSessionStatus = 'running' | 'completed' | 'failed' | 'stopped';

export interface PipelineSession {
  id: string;
  pipeline_id: string;
  status: PipelineSessionStatus;
  node_agent_map: Record<string, string>;
  node_status: Record<string, string>;
  wait_until: Record<string, string>;  // wait_node_id -> ISO datetime when wait will end
  condition_counts: Record<string, number>;  // condition_node_id -> evaluation count
  execution_order: string[];
  started_at: string;
  finished_at?: string;
  error_message?: string;
}

export interface PipelineSessionListResponse {
  sessions: PipelineSession[];
  total: number;
}

export interface PipelineSessionResponse {
  session: PipelineSession;
}

// Global events WebSocket types
export type GlobalEventType =
  | 'connected'
  | 'agent_spawned'
  | 'agent_status_changed'
  | 'agent_deleted'
  | 'agent_todos_changed'
  | 'session_created'
  | 'session_status_changed'
  | 'session_node_status_changed'
  | 'session_deleted'
  | 'pipeline_created'
  | 'pipeline_updated'
  | 'pipeline_deleted'
  | 'ping'
  | 'pong';

export interface GlobalEvent {
  type: GlobalEventType;
  timestamp: string;
  data?: {
    status?: string;
    agent?: AgentState;
    session?: PipelineSession;
    [key: string]: unknown;
  };
  agent_id?: string;
  session_id?: string;
  pipeline_id?: string;
  node_id?: string;
}
