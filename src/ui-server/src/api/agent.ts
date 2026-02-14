import { API_URL } from './config';

export interface AgentToolTrace {
  name: string;
  args: Record<string, unknown>;
  ok: boolean;
  result: Record<string, unknown>;
}

export interface AgentToolDirectoryItem {
  name: string;
  category: string;
  purpose: string;
  tooltip: string;
  inputs: string[];
  typical_output: string;
  keywords: string[];
}

export interface AgentToolSuggestion {
  name: string;
  category: string;
  score: number;
  reason: string;
  tooltip: string;
  prefilled_args: Record<string, unknown>;
  prefilled_prompt?: string | null;
  kind: 'tool' | 'composite';
}

export interface AgentToolMemoryEntry {
  tool_name: string;
  summary: string;
  ok: boolean;
  updated_at: number;
  age_seconds: number;
  stale: boolean;
  stale_hint?: string | null;
  context_id?: string | null;
}

export interface AgentMessageResponse {
  sessionId: string;
  assistantMessage: string;
  model: string;
  toolTraces: AgentToolTrace[];
  toolSuggestions?: AgentToolSuggestion[];
  toolMemory?: AgentToolMemoryEntry[];
}

export interface AgentRunCreateResponse {
  runId: string;
  status: string;
}

export interface AgentRunStatusResponse {
  runId: string;
  status: string;
  response?: AgentMessageResponse | null;
  error?: string | null;
}

export interface AgentRunCancelResponse {
  runId: string;
  status: string;
  error?: string | null;
}

export interface AgentRunSteerResponse {
  runId: string;
  status: string;
  queuedMessages: number;
}

interface CreateSessionResponse {
  sessionId: string;
  projectRoot: string;
}

interface ToolDirectoryResponse {
  tools: AgentToolDirectoryItem[];
  categories: string[];
  suggestions: AgentToolSuggestion[];
  toolMemory: AgentToolMemoryEntry[];
}

interface ToolSuggestionsResponse {
  suggestions: AgentToolSuggestion[];
  toolMemory: AgentToolMemoryEntry[];
}

export class AgentApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'AgentApiError';
  }
}

async function request<T>(path: string, init: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init.headers || {}),
    },
  });

  if (!response.ok) {
    let message = response.statusText;
    try {
      const data = await response.json();
      if (data && typeof data === 'object' && 'detail' in data) {
        message = String(data.detail);
      }
    } catch {
      // Ignore parse errors, fallback to statusText.
    }
    throw new AgentApiError(response.status, message);
  }

  return (await response.json()) as T;
}

export const agentApi = {
  async createSession(projectRoot: string): Promise<CreateSessionResponse> {
    return request<CreateSessionResponse>('/api/agent/sessions', {
      method: 'POST',
      body: JSON.stringify({ projectRoot }),
    });
  },

  async sendMessage(
    sessionId: string,
    payload: { message: string; projectRoot: string; selectedTargets?: string[] }
  ): Promise<AgentMessageResponse> {
    return request<AgentMessageResponse>(`/api/agent/sessions/${encodeURIComponent(sessionId)}/messages`, {
      method: 'POST',
      body: JSON.stringify({
        message: payload.message,
        projectRoot: payload.projectRoot,
        selectedTargets: payload.selectedTargets ?? [],
      }),
    });
  },

  async getToolDirectory(sessionId?: string): Promise<ToolDirectoryResponse> {
    const suffix = sessionId
      ? `?sessionId=${encodeURIComponent(sessionId)}`
      : '';
    return request<ToolDirectoryResponse>(`/api/agent/tools${suffix}`, {
      method: 'GET',
    });
  },

  async getToolSuggestions(
    sessionId: string,
    payload: { message: string; projectRoot?: string | null; selectedTargets?: string[] }
  ): Promise<ToolSuggestionsResponse> {
    return request<ToolSuggestionsResponse>(
      `/api/agent/sessions/${encodeURIComponent(sessionId)}/tool-suggestions`,
      {
        method: 'POST',
        body: JSON.stringify({
          message: payload.message,
          projectRoot: payload.projectRoot ?? null,
          selectedTargets: payload.selectedTargets ?? [],
        }),
      }
    );
  },

  async createRun(
    sessionId: string,
    payload: { message: string; projectRoot: string; selectedTargets?: string[] }
  ): Promise<AgentRunCreateResponse> {
    return request<AgentRunCreateResponse>(
      `/api/agent/sessions/${encodeURIComponent(sessionId)}/runs`,
      {
        method: 'POST',
        body: JSON.stringify({
          message: payload.message,
          projectRoot: payload.projectRoot,
          selectedTargets: payload.selectedTargets ?? [],
        }),
      }
    );
  },

  async getRunStatus(
    sessionId: string,
    runId: string
  ): Promise<AgentRunStatusResponse> {
    return request<AgentRunStatusResponse>(
      `/api/agent/sessions/${encodeURIComponent(sessionId)}/runs/${encodeURIComponent(runId)}`,
      {
        method: 'GET',
      }
    );
  },

  async cancelRun(
    sessionId: string,
    runId: string
  ): Promise<AgentRunCancelResponse> {
    return request<AgentRunCancelResponse>(
      `/api/agent/sessions/${encodeURIComponent(sessionId)}/runs/${encodeURIComponent(runId)}/cancel`,
      {
        method: 'POST',
      }
    );
  },

  async steerRun(
    sessionId: string,
    runId: string,
    payload: { message: string }
  ): Promise<AgentRunSteerResponse> {
    return request<AgentRunSteerResponse>(
      `/api/agent/sessions/${encodeURIComponent(sessionId)}/runs/${encodeURIComponent(runId)}/steer`,
      {
        method: 'POST',
        body: JSON.stringify({
          message: payload.message,
        }),
      }
    );
  },
};
