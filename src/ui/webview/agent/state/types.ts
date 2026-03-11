import type { ToolTraceResponse as AgentToolTrace } from '../api';

export type MessageRole = 'user' | 'assistant' | 'system';

export type AgentProgressPhase =
  | 'thinking'
  | 'tool_start'
  | 'tool_end'
  | 'done'
  | 'stopped'
  | 'error'
  | 'compacting'
  | 'design_questions';

export interface AgentChecklistItem {
  id: string;
  description: string;
  criteria: string;
  status: 'not_started' | 'doing' | 'done' | 'blocked';
  requirement_id?: string | null;
}

export interface AgentChecklist {
  items: AgentChecklistItem[];
  created_at: number;
}

export interface DesignQuestion {
  id: string;
  question: string;
  options?: string[];
  default?: string;
}

export interface DesignQuestionsData {
  context: string;
  questions: DesignQuestion[];
}

export interface AgentProgressPayload {
  session_id?: unknown;
  run_id?: unknown;
  phase?: unknown;
  call_id?: unknown;
  name?: unknown;
  args?: unknown;
  trace?: unknown;
  status_text?: unknown;
  detail_text?: unknown;
  activity_summary?: unknown;
  loop?: unknown;
  tool_index?: unknown;
  tool_count?: unknown;
  input_tokens?: unknown;
  output_tokens?: unknown;
  total_tokens?: unknown;
  context_limit_tokens?: unknown;
  contextLimitTokens?: unknown;
  usage?: unknown;
  checklist?: unknown;
  context?: unknown;
  questions?: unknown;
  response?: unknown;
  error?: unknown;
}

export interface AgentTraceView extends AgentToolTrace {
  callId?: string;
  running?: boolean;
}

export interface AgentEditDiffUiPayload {
  path: string;
  before_content: string;
  after_content: string;
}

export interface AgentMessage {
  id: string;
  role: MessageRole;
  content: string;
  pending?: boolean;
  activity?: string;
  toolTraces?: AgentTraceView[];
  checklist?: AgentChecklist | null;
  designQuestions?: DesignQuestionsData | null;
}

export interface AgentChatSnapshot {
  id: string;
  projectRoot: string;
  title: string;
  sessionId: string | null;
  isSessionLoading: boolean;
  isSending: boolean;
  isStopping: boolean;
  activeRunId: string | null;
  runStartedAt: number | null;
  messages: AgentMessage[];
  input: string;
  error: string | null;
  activityLabel: string;
  createdAt: number;
  updatedAt: number;
}

export interface AgentState {
  snapshots: AgentChatSnapshot[];
  activeChatByProject: Record<string, string>;
  isHydrated: boolean;
}

export const DEFAULT_AGENT_STATE: AgentState = {
  snapshots: [],
  activeChatByProject: {},
  isHydrated: false,
};
