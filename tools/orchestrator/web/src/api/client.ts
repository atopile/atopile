import type {
  AgentConfig,
  AgentListResponse,
  AgentOutputResponse,
  AgentStateResponse,
  BackendsResponse,
  CreatePipelineRequest,
  HealthResponse,
  Pipeline,
  PipelineListResponse,
  SendInputRequest,
  SendInputResponse,
  SessionListResponse,
  SessionStateResponse,
  SpawnAgentResponse,
  StatsResponse,
  TerminateAgentRequest,
  TerminateAgentResponse,
} from './types';

// Use relative URLs when proxied through Vite, or full URL for production
const API_BASE = import.meta.env.DEV ? '/api' : (import.meta.env.VITE_API_URL || 'http://localhost:8765');

class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public data?: unknown
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${url}`, {
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

export const api = {
  // Health & Info
  health: () => fetchJson<HealthResponse>('/health'),
  stats: () => fetchJson<StatsResponse>('/stats'),
  backends: () => fetchJson<BackendsResponse>('/backends'),

  // Agents
  agents: {
    list: (params?: { status?: string; backend?: string; limit?: number; offset?: number }) => {
      const searchParams = new URLSearchParams();
      if (params?.status) searchParams.set('status', params.status);
      if (params?.backend) searchParams.set('backend', params.backend);
      if (params?.limit) searchParams.set('limit', String(params.limit));
      if (params?.offset) searchParams.set('offset', String(params.offset));
      const query = searchParams.toString();
      return fetchJson<AgentListResponse>(`/agents${query ? `?${query}` : ''}`);
    },

    get: (id: string) => fetchJson<AgentStateResponse>(`/agents/${id}`),

    spawn: (config: AgentConfig) =>
      fetchJson<SpawnAgentResponse>('/agents/spawn', {
        method: 'POST',
        body: JSON.stringify({ config }),
      }),

    terminate: (id: string, options?: TerminateAgentRequest) =>
      fetchJson<TerminateAgentResponse>(`/agents/${id}/terminate`, {
        method: 'POST',
        body: JSON.stringify(options || {}),
      }),

    sendInput: (id: string, input: string, newline = true) =>
      fetchJson<SendInputResponse>(`/agents/${id}/input`, {
        method: 'POST',
        body: JSON.stringify({ input, newline } as SendInputRequest),
      }),

    getOutput: (id: string, sinceSequence = 0, maxChunks = 1000) => {
      const params = new URLSearchParams({
        since_sequence: String(sinceSequence),
        max_chunks: String(maxChunks),
      });
      return fetchJson<AgentOutputResponse>(`/agents/${id}/output?${params}`);
    },

    delete: (id: string) =>
      fetchJson<{ status: string; agent_id: string }>(`/agents/${id}`, {
        method: 'DELETE',
      }),

    resume: (id: string, prompt: string, options?: { max_turns?: number; max_budget_usd?: number }) =>
      fetchJson<SpawnAgentResponse>(`/agents/${id}/resume`, {
        method: 'POST',
        body: JSON.stringify({ prompt, ...options }),
      }),
  },

  // Sessions
  sessions: {
    list: (params?: { status?: string; backend?: string; limit?: number }) => {
      const searchParams = new URLSearchParams();
      if (params?.status) searchParams.set('status', params.status);
      if (params?.backend) searchParams.set('backend', params.backend);
      if (params?.limit) searchParams.set('limit', String(params.limit));
      const query = searchParams.toString();
      return fetchJson<SessionListResponse>(`/sessions${query ? `?${query}` : ''}`);
    },

    get: (id: string) => fetchJson<SessionStateResponse>(`/sessions/${id}`),

    resume: (id: string, prompt: string, options?: { max_turns?: number; timeout_seconds?: number }) =>
      fetchJson<{ agent_id: string; session_id: string; message: string }>(`/sessions/${id}/resume`, {
        method: 'POST',
        body: JSON.stringify({ prompt, ...options }),
      }),

    delete: (id: string) =>
      fetchJson<{ status: string; session_id: string }>(`/sessions/${id}`, {
        method: 'DELETE',
      }),
  },

  // Pipelines
  pipelines: {
    list: () => fetchJson<PipelineListResponse>('/pipelines'),

    get: (id: string) => fetchJson<Pipeline>(`/pipelines/${id}`),

    create: (pipeline: CreatePipelineRequest) =>
      fetchJson<Pipeline>('/pipelines', {
        method: 'POST',
        body: JSON.stringify(pipeline),
      }),

    update: (id: string, pipeline: Partial<CreatePipelineRequest>) =>
      fetchJson<Pipeline>(`/pipelines/${id}`, {
        method: 'PUT',
        body: JSON.stringify(pipeline),
      }),

    delete: (id: string) =>
      fetchJson<{ status: string; pipeline_id: string }>(`/pipelines/${id}`, {
        method: 'DELETE',
      }),

    run: (id: string) =>
      fetchJson<{ status: string; message: string }>(`/pipelines/${id}/run`, {
        method: 'POST',
      }),

    pause: (id: string) =>
      fetchJson<{ status: string; message: string }>(`/pipelines/${id}/pause`, {
        method: 'POST',
      }),

    resume: (id: string) =>
      fetchJson<{ status: string; message: string }>(`/pipelines/${id}/resume`, {
        method: 'POST',
      }),

    stop: (id: string) =>
      fetchJson<{ status: string; message: string }>(`/pipelines/${id}/stop`, {
        method: 'POST',
      }),
  },
};

export { ApiError };
export default api;
