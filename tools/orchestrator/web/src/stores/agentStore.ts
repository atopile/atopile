import { create } from 'zustand';
import { api } from '@/api/client';
import type { AgentConfig, AgentState } from '@/api/types';

interface AgentStore {
  // State
  agents: Map<string, AgentState>;
  selectedAgentId: string | null;
  loading: boolean;
  error: string | null;

  // Actions
  fetchAgents: () => Promise<void>;
  fetchAgent: (id: string) => Promise<AgentState | null>;
  selectAgent: (id: string | null) => void;
  spawnAgent: (config: AgentConfig) => Promise<string>;
  resumeAgent: (id: string, prompt: string) => Promise<string>;
  terminateAgent: (id: string, force?: boolean) => Promise<void>;
  deleteAgent: (id: string) => Promise<void>;
  sendInput: (id: string, input: string) => Promise<boolean>;
  updateAgent: (id: string, updates: Partial<AgentState>) => void;
  setError: (error: string | null) => void;

  // Computed
  getAgent: (id: string) => AgentState | undefined;
  getRunningAgents: () => AgentState[];
  getSelectedAgent: () => AgentState | undefined;
}

export const useAgentStore = create<AgentStore>((set, get) => ({
  // Initial state
  agents: new Map(),
  selectedAgentId: null,
  loading: false,
  error: null,

  // Actions
  fetchAgents: async () => {
    set({ loading: true, error: null });
    try {
      const response = await api.agents.list({ limit: 100 });
      const agentsMap = new Map<string, AgentState>();
      for (const agent of response.agents) {
        agentsMap.set(agent.id, agent);
      }
      set({ agents: agentsMap, loading: false });
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to fetch agents', loading: false });
    }
  },

  fetchAgent: async (id: string) => {
    try {
      const response = await api.agents.get(id);
      const { agents } = get();
      const newAgents = new Map(agents);
      newAgents.set(id, response.agent);
      set({ agents: newAgents });
      return response.agent;
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to fetch agent' });
      return null;
    }
  },

  selectAgent: (id: string | null) => {
    set({ selectedAgentId: id });
  },

  spawnAgent: async (config: AgentConfig) => {
    set({ loading: true, error: null });
    try {
      const response = await api.agents.spawn(config);
      // Fetch the full agent state
      await get().fetchAgent(response.agent_id);
      set({ loading: false, selectedAgentId: response.agent_id });
      return response.agent_id;
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to spawn agent', loading: false });
      throw e;
    }
  },

  resumeAgent: async (id: string, prompt: string) => {
    set({ loading: true, error: null });
    try {
      const response = await api.agents.resume(id, prompt);
      // Fetch the updated agent state (same agent ID is reused)
      await get().fetchAgent(response.agent_id);
      set({ loading: false, selectedAgentId: response.agent_id });
      // Note: The AgentDetail component should clear and reconnect output
      // when it detects the agent has been resumed (status changes to running)
      return response.agent_id;
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to resume agent', loading: false });
      throw e;
    }
  },

  terminateAgent: async (id: string, force = false) => {
    try {
      await api.agents.terminate(id, { force });
      await get().fetchAgent(id);
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to terminate agent' });
      throw e;
    }
  },

  deleteAgent: async (id: string) => {
    try {
      await api.agents.delete(id);
      const { agents, selectedAgentId } = get();
      const newAgents = new Map(agents);
      newAgents.delete(id);
      set({
        agents: newAgents,
        selectedAgentId: selectedAgentId === id ? null : selectedAgentId,
      });
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to delete agent' });
      throw e;
    }
  },

  sendInput: async (id: string, input: string) => {
    try {
      const response = await api.agents.sendInput(id, input);
      return response.success;
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to send input' });
      return false;
    }
  },

  updateAgent: (id: string, updates: Partial<AgentState>) => {
    const { agents } = get();
    const agent = agents.get(id);
    if (agent) {
      const newAgents = new Map(agents);
      newAgents.set(id, { ...agent, ...updates });
      set({ agents: newAgents });
    }
  },

  setError: (error: string | null) => {
    set({ error });
  },

  // Computed getters
  getAgent: (id: string) => {
    return get().agents.get(id);
  },

  getRunningAgents: () => {
    const { agents } = get();
    return Array.from(agents.values()).filter(
      (a) => a.status === 'running' || a.status === 'starting' || a.status === 'pending'
    );
  },

  getSelectedAgent: () => {
    const { agents, selectedAgentId } = get();
    return selectedAgentId ? agents.get(selectedAgentId) : undefined;
  },
}));

export default useAgentStore;
