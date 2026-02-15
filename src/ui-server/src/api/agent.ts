import { API_URL } from './config';
import type {
  CancelRunResponse,
  CreateRunRequest,
  CreateRunResponse,
  CreateSessionRequest,
  CreateSessionResponse,
  GetRunResponse,
  SendMessageRequest,
  SendMessageResponse,
  SteerRunRequest,
  SteerRunResponse,
  ToolDirectoryItem,
  ToolDirectoryResponse,
  ToolMemoryEntry,
  ToolSuggestion,
  ToolSuggestionsRequest,
  ToolSuggestionsResponse,
  ToolTraceResponse,
} from '../types/gen/generated';

export type AgentToolTrace = ToolTraceResponse;
export type AgentToolDirectoryItem = ToolDirectoryItem;
export type AgentToolSuggestion = ToolSuggestion;
export type AgentToolMemoryEntry = ToolMemoryEntry;
export type AgentMessageResponse = SendMessageResponse;
export type AgentRunCreateResponse = CreateRunResponse;
export type AgentRunStatusResponse = GetRunResponse;
export type AgentRunCancelResponse = CancelRunResponse;
export type AgentRunSteerResponse = SteerRunResponse;

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
    const requestBody: CreateSessionRequest = { projectRoot };
    return request<CreateSessionResponse>('/api/agent/sessions', {
      method: 'POST',
      body: JSON.stringify(requestBody),
    });
  },

  async sendMessage(
    sessionId: string,
    payload: SendMessageRequest
  ): Promise<AgentMessageResponse> {
    const requestBody: SendMessageRequest = {
      message: payload.message,
      projectRoot: payload.projectRoot,
      selectedTargets: payload.selectedTargets ?? [],
    };
    return request<AgentMessageResponse>(`/api/agent/sessions/${encodeURIComponent(sessionId)}/messages`, {
      method: 'POST',
      body: JSON.stringify(requestBody),
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
    payload: ToolSuggestionsRequest
  ): Promise<ToolSuggestionsResponse> {
    const requestBody: ToolSuggestionsRequest = {
      message: payload.message ?? '',
      projectRoot: payload.projectRoot ?? null,
      selectedTargets: payload.selectedTargets ?? [],
    };
    return request<ToolSuggestionsResponse>(
      `/api/agent/sessions/${encodeURIComponent(sessionId)}/tool-suggestions`,
      {
        method: 'POST',
        body: JSON.stringify(requestBody),
      }
    );
  },

  async createRun(
    sessionId: string,
    payload: CreateRunRequest
  ): Promise<AgentRunCreateResponse> {
    const requestBody: CreateRunRequest = {
      message: payload.message,
      projectRoot: payload.projectRoot,
      selectedTargets: payload.selectedTargets ?? [],
    };
    return request<AgentRunCreateResponse>(
      `/api/agent/sessions/${encodeURIComponent(sessionId)}/runs`,
      {
        method: 'POST',
        body: JSON.stringify(requestBody),
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
    payload: SteerRunRequest
  ): Promise<AgentRunSteerResponse> {
    const requestBody: SteerRunRequest = { message: payload.message };
    return request<AgentRunSteerResponse>(
      `/api/agent/sessions/${encodeURIComponent(sessionId)}/runs/${encodeURIComponent(runId)}/steer`,
      {
        method: 'POST',
        body: JSON.stringify(requestBody),
      }
    );
  },
};
