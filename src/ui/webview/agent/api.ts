import { rpcClient } from "../shared/rpcClient";
import { createWebviewLogger } from "../shared/logger";

const logger = createWebviewLogger("Agent");

export interface ToolTraceResponse {
  name: string;
  args: Record<string, unknown>;
  ok: boolean;
  result: Record<string, any>;
}

export interface ToolDirectoryItem {
  name: string;
  category: string;
  purpose: string;
  tooltip: string;
  inputs: string[];
  typicalOutput: string;
  keywords: string[];
}

export interface ToolSuggestion {
  name: string;
  category: string;
  score: number;
  reason: string;
  tooltip: string;
  prefilledArgs: Record<string, unknown>;
  prefilledPrompt: string | null;
  kind: "tool" | "composite";
}

export interface ToolMemoryEntry {
  toolName: string;
  summary: string;
  ok: boolean;
  updatedAt: number;
  ageSeconds: number;
  stale: boolean;
  staleHint: string | null;
  contextId: string | null;
}

export interface CreateSessionResponse {
  sessionId: string;
  projectRoot: string;
}

export interface SessionHistoryMessage {
  role: "user" | "assistant";
  content: string;
}

export interface SessionSummary {
  sessionId: string;
  projectRoot: string;
  history: SessionHistoryMessage[];
  recentSelectedTargets: string[];
  createdAt: number;
  updatedAt: number;
}

export interface ListSessionsResponse {
  sessions: SessionSummary[];
}

export interface SendMessageRequest {
  message: string;
  projectRoot: string;
  selectedTargets?: string[];
}

export interface SendMessageResponse {
  sessionId: string;
  assistantMessage: string;
  model: string;
  toolTraces: ToolTraceResponse[];
  toolSuggestions: ToolSuggestion[];
  toolMemory: ToolMemoryEntry[];
}

export interface ToolDirectoryResponse {
  tools: ToolDirectoryItem[];
  categories: string[];
  suggestions: ToolSuggestion[];
  toolMemory: ToolMemoryEntry[];
}

export interface ToolSuggestionsRequest {
  message?: string;
  projectRoot?: string | null;
  selectedTargets?: string[];
}

export interface ToolSuggestionsResponse {
  suggestions: ToolSuggestion[];
  toolMemory: ToolMemoryEntry[];
}

export interface CreateRunRequest {
  message: string;
  projectRoot: string;
  selectedTargets?: string[];
}

export interface CreateRunResponse {
  runId: string;
  status: string;
}

export interface GetRunResponse {
  runId: string;
  status: string;
  response?: SendMessageResponse | null;
  error?: string | null;
}

export interface CancelRunResponse {
  runId: string;
  status: string;
  error?: string | null;
}

export interface SteerRunRequest {
  message: string;
}

export interface SteerRunResponse {
  runId: string;
  status: string;
  queuedMessages: number;
}

export interface InterruptRunResponse {
  runId: string;
  status: string;
  queuedMessages: number;
  queuedMessage?: string | null;
}

export interface SessionSkillsResponse {
  sessionId: string;
  projectRoot: string;
  skillsDir: string;
  selectedSkillIds: string[];
  selectedSkills: Record<string, unknown>[];
  reasoning: string[];
  totalChars: number;
  generatedAt: number | null;
  loadedSkillsCount: number;
}

export interface AgentProgressEventPayload {
  type: "agent_progress";
  session_id?: string;
  project_root?: string;
  run_id?: string;
  phase?: string;
  call_id?: string;
  name?: string;
  args?: Record<string, unknown>;
  trace?: ToolTraceResponse | null;
  status_text?: string;
  detail_text?: string;
  activity_summary?: string;
  loop?: number;
  tool_index?: number;
  tool_count?: number;
  input_tokens?: number;
  output_tokens?: number;
  total_tokens?: number;
  context_limit_tokens?: number;
  usage?: Record<string, unknown>;
  checklist?: unknown;
  context?: unknown;
  questions?: unknown;
  response?: SendMessageResponse | null;
  error?: string | null;
}

export class AgentApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "AgentApiError";
  }
}

function requireRpcClient() {
  if (!rpcClient) {
    throw new AgentApiError(0, "RPC client is not available");
  }
  return rpcClient;
}

function dispatch(action: string, payload?: Record<string, unknown>): void {
  try {
    const ok = requireRpcClient().sendAction(action, payload);
    if (!ok) {
      throw new AgentApiError(0, "RPC transport is not available");
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : `${action} failed`;
    logger.error(`rpc failed action=${action} message=${message}`);
    throw error instanceof AgentApiError ? error : new AgentApiError(0, message);
  }
}

export const agentApi = {
  createSession(projectRoot: string): void {
    dispatch("agent.createSession", { projectRoot });
  },

  createRun(
    sessionId: string,
    payload: CreateRunRequest,
  ): void {
    dispatch("agent.createRun", {
      agentSessionId: sessionId,
      message: payload.message,
      projectRoot: payload.projectRoot,
      selectedTargets: payload.selectedTargets ?? [],
    });
  },

  cancelRun(
    sessionId: string,
    runId: string,
  ): void {
    dispatch("agent.cancelRun", {
      agentSessionId: sessionId,
      runId,
    });
  },

  steerRun(
    sessionId: string,
    runId: string,
    payload: SteerRunRequest,
  ): void {
    dispatch("agent.steerRun", {
      agentSessionId: sessionId,
      runId,
      message: payload.message,
    });
  },

  interruptRun(
    sessionId: string,
    runId: string,
    payload: { message: string },
  ): void {
    dispatch("agent.interruptRun", {
      agentSessionId: sessionId,
      runId,
      message: payload.message,
    });
  },
};

export function addAgentProgressListener(
  listener: (payload: AgentProgressEventPayload) => void,
): () => void {
  const client = requireRpcClient();
  const handleRaw = (raw: string) => {
    try {
      const msg = JSON.parse(raw) as AgentProgressEventPayload;
      if (msg.type === "agent_progress") {
        listener(msg);
      }
    } catch {
      return;
    }
  };
  client.addRawListener(handleRaw);
  return () => client.removeRawListener(handleRaw);
}
