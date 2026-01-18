/**
 * Pure fetch-based API client
 * Works in both browser and Node.js/Bun environments
 */

import type {
  AgentConfig,
  AgentHistoryResponse,
  AgentListResponse,
  AgentOutputResponse,
  AgentStateResponse,
  BackendsResponse,
  CreatePipelineRequest,
  HealthResponse,
  Pipeline,
  PipelineListResponse,
  PipelineSession,
  PipelineSessionListResponse,
  SendInputRequest,
  SendInputResponse,
  SessionListResponse,
  SessionStateResponse,
  SpawnAgentResponse,
  StatsResponse,
  TerminateAgentRequest,
  TerminateAgentResponse,
} from './types';

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public data?: unknown
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export class APIClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private async fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${this.baseUrl}${url}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      ...options,
    });

    if (!response.ok) {
      let data: unknown;
      try {
        data = await response.json();
      } catch {
        data = await response.text();
      }
      throw new ApiError(
        `API request failed: ${response.status} ${response.statusText}`,
        response.status,
        data
      );
    }

    return response.json();
  }

  // Health & Info
  health(): Promise<HealthResponse> {
    return this.fetchJson('/health');
  }

  stats(): Promise<StatsResponse> {
    return this.fetchJson('/stats');
  }

  backends(): Promise<BackendsResponse> {
    return this.fetchJson('/backends');
  }

  // Agents
  agents = {
    list: (params?: { status?: string; backend?: string; limit?: number; offset?: number }): Promise<AgentListResponse> => {
      const searchParams = new URLSearchParams();
      if (params?.status) searchParams.set('status', params.status);
      if (params?.backend) searchParams.set('backend', params.backend);
      if (params?.limit) searchParams.set('limit', String(params.limit));
      if (params?.offset) searchParams.set('offset', String(params.offset));
      const query = searchParams.toString();
      return this.fetchJson(`/agents${query ? `?${query}` : ''}`);
    },

    get: (id: string): Promise<AgentStateResponse> => {
      return this.fetchJson(`/agents/${id}`);
    },

    spawn: (config: AgentConfig, name?: string): Promise<SpawnAgentResponse> => {
      return this.fetchJson('/agents/spawn', {
        method: 'POST',
        body: JSON.stringify({ config, name }),
      });
    },

    rename: (id: string, name: string): Promise<AgentStateResponse> => {
      return this.fetchJson(`/agents/${id}`, {
        method: 'PATCH',
        body: JSON.stringify({ name }),
      });
    },

    terminate: (id: string, options?: TerminateAgentRequest): Promise<TerminateAgentResponse> => {
      return this.fetchJson(`/agents/${id}/terminate`, {
        method: 'POST',
        body: JSON.stringify(options || {}),
      });
    },

    sendInput: (id: string, input: string, newline = true): Promise<SendInputResponse> => {
      return this.fetchJson(`/agents/${id}/input`, {
        method: 'POST',
        body: JSON.stringify({ input, newline } as SendInputRequest),
      });
    },

    getOutput: (id: string, sinceSequence = 0, maxChunks = 1000): Promise<AgentOutputResponse> => {
      const params = new URLSearchParams({
        since_sequence: String(sinceSequence),
        max_chunks: String(maxChunks),
      });
      return this.fetchJson(`/agents/${id}/output?${params}`);
    },

    getHistory: (id: string): Promise<AgentHistoryResponse> => {
      return this.fetchJson(`/agents/${id}/history`);
    },

    delete: (id: string): Promise<{ status: string; agent_id: string }> => {
      return this.fetchJson(`/agents/${id}`, {
        method: 'DELETE',
      });
    },

    resume: (id: string, prompt: string, options?: { max_turns?: number; max_budget_usd?: number }): Promise<SpawnAgentResponse> => {
      return this.fetchJson(`/agents/${id}/resume`, {
        method: 'POST',
        body: JSON.stringify({ prompt, ...options }),
      });
    },
  };

  // Sessions
  sessions = {
    list: (params?: { status?: string; backend?: string; limit?: number }): Promise<SessionListResponse> => {
      const searchParams = new URLSearchParams();
      if (params?.status) searchParams.set('status', params.status);
      if (params?.backend) searchParams.set('backend', params.backend);
      if (params?.limit) searchParams.set('limit', String(params.limit));
      const query = searchParams.toString();
      return this.fetchJson(`/sessions${query ? `?${query}` : ''}`);
    },

    get: (id: string): Promise<SessionStateResponse> => {
      return this.fetchJson(`/sessions/${id}`);
    },

    resume: (id: string, prompt: string, options?: { max_turns?: number; timeout_seconds?: number }): Promise<{ agent_id: string; session_id: string; message: string }> => {
      return this.fetchJson(`/sessions/${id}/resume`, {
        method: 'POST',
        body: JSON.stringify({ prompt, ...options }),
      });
    },

    delete: (id: string): Promise<{ status: string; session_id: string }> => {
      return this.fetchJson(`/sessions/${id}`, {
        method: 'DELETE',
      });
    },
  };

  // Pipelines
  pipelines = {
    list: (): Promise<PipelineListResponse> => {
      return this.fetchJson('/pipelines');
    },

    get: (id: string): Promise<Pipeline> => {
      return this.fetchJson(`/pipelines/${id}`);
    },

    create: (pipeline: CreatePipelineRequest): Promise<Pipeline> => {
      return this.fetchJson('/pipelines', {
        method: 'POST',
        body: JSON.stringify(pipeline),
      });
    },

    update: (id: string, pipeline: Partial<CreatePipelineRequest>): Promise<Pipeline> => {
      return this.fetchJson(`/pipelines/${id}`, {
        method: 'PUT',
        body: JSON.stringify(pipeline),
      });
    },

    delete: (id: string): Promise<{ status: string; pipeline_id: string }> => {
      return this.fetchJson(`/pipelines/${id}`, {
        method: 'DELETE',
      });
    },

    run: (id: string): Promise<{ status: string; message: string }> => {
      return this.fetchJson(`/pipelines/${id}/run`, {
        method: 'POST',
      });
    },

    pause: (id: string): Promise<{ status: string; message: string }> => {
      return this.fetchJson(`/pipelines/${id}/pause`, {
        method: 'POST',
      });
    },

    resume: (id: string): Promise<{ status: string; message: string }> => {
      return this.fetchJson(`/pipelines/${id}/resume`, {
        method: 'POST',
      });
    },

    stop: (id: string): Promise<{ status: string; message: string }> => {
      return this.fetchJson(`/pipelines/${id}/stop`, {
        method: 'POST',
      });
    },

    // Pipeline sessions
    listSessions: (pipelineId: string): Promise<PipelineSessionListResponse> => {
      return this.fetchJson(`/pipelines/${pipelineId}/sessions`);
    },

    getSession: (pipelineId: string, sessionId: string): Promise<{ session: PipelineSession }> => {
      return this.fetchJson(`/pipelines/${pipelineId}/sessions/${sessionId}`);
    },

    stopSession: (pipelineId: string, sessionId: string, force = false): Promise<{ status: string; message: string; pipeline_id: string }> => {
      return this.fetchJson(
        `/pipelines/${pipelineId}/sessions/${sessionId}/stop?force=${force}`,
        { method: 'POST' }
      );
    },

    deleteSession: (pipelineId: string, sessionId: string, force = false): Promise<{ status: string; session_id: string; pipeline_id: string }> => {
      return this.fetchJson(
        `/pipelines/${pipelineId}/sessions/${sessionId}?force=${force}`,
        { method: 'DELETE' }
      );
    },
  };
}
