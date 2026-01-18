import { create } from 'zustand';
import { api } from '@/api/client';
import { wsManager } from '@/api/websocket';
import type { OutputChunk, StreamEvent } from '@/api/types';
import { useAgentStore } from './agentStore';

interface OutputStore {
  // State
  outputs: Map<string, OutputChunk[]>;
  connections: Set<string>;
  maxChunksPerAgent: number;

  // Actions
  addChunk: (agentId: string, chunk: OutputChunk) => void;
  clearOutput: (agentId: string) => void;
  fetchOutput: (agentId: string) => Promise<void>;
  connectToAgent: (agentId: string) => void;
  disconnectFromAgent: (agentId: string) => void;
  disconnectAll: () => void;

  // Computed
  getOutput: (agentId: string) => OutputChunk[];
  isConnected: (agentId: string) => boolean;
}

export const useOutputStore = create<OutputStore>((set, get) => ({
  // Initial state
  outputs: new Map(),
  connections: new Set(),
  maxChunksPerAgent: 1000,

  // Actions
  addChunk: (agentId: string, chunk: OutputChunk) => {
    const { outputs, maxChunksPerAgent } = get();
    const agentOutput = outputs.get(agentId) || [];

    // Avoid duplicates by sequence number
    if (agentOutput.some((c) => c.sequence === chunk.sequence)) {
      return;
    }

    // Add chunk and trim if needed
    const newOutput = [...agentOutput, chunk];
    if (newOutput.length > maxChunksPerAgent) {
      newOutput.splice(0, newOutput.length - maxChunksPerAgent);
    }

    const newOutputs = new Map(outputs);
    newOutputs.set(agentId, newOutput);
    set({ outputs: newOutputs });
  },

  clearOutput: (agentId: string) => {
    const { outputs } = get();
    const newOutputs = new Map(outputs);
    newOutputs.delete(agentId);
    set({ outputs: newOutputs });
  },

  fetchOutput: async (agentId: string) => {
    try {
      const { outputs } = get();
      const existing = outputs.get(agentId) || [];
      const sinceSequence = existing.length > 0 ? existing[existing.length - 1].sequence + 1 : 0;

      const response = await api.agents.getOutput(agentId, sinceSequence);

      // Add new chunks
      for (const chunk of response.chunks) {
        get().addChunk(agentId, chunk as OutputChunk);
      }
    } catch (e) {
      console.error('Failed to fetch output:', e);
    }
  },

  connectToAgent: (agentId: string) => {
    const { connections } = get();

    if (connections.has(agentId)) {
      return;
    }

    const handleMessage = (event: StreamEvent) => {
      if (event.type === 'agent_output' && event.chunk) {
        get().addChunk(agentId, event.chunk);
      } else if (
        event.type === 'agent_completed' ||
        event.type === 'agent_failed' ||
        event.type === 'agent_terminated'
      ) {
        // Update agent status
        const status = event.type === 'agent_completed'
          ? 'completed'
          : event.type === 'agent_failed'
          ? 'failed'
          : 'terminated';
        useAgentStore.getState().updateAgent(agentId, { status });
      }
    };

    const handleClose = () => {
      const { connections } = get();
      const newConnections = new Set(connections);
      newConnections.delete(agentId);
      set({ connections: newConnections });
    };

    wsManager.connect(agentId, handleMessage, undefined, handleClose);

    const newConnections = new Set(connections);
    newConnections.add(agentId);
    set({ connections: newConnections });
  },

  disconnectFromAgent: (agentId: string) => {
    const { connections } = get();
    wsManager.disconnect(agentId);
    const newConnections = new Set(connections);
    newConnections.delete(agentId);
    set({ connections: newConnections });
  },

  disconnectAll: () => {
    wsManager.disconnectAll();
    set({ connections: new Set() });
  },

  // Computed
  getOutput: (agentId: string) => {
    return get().outputs.get(agentId) || [];
  },

  isConnected: (agentId: string) => {
    return get().connections.has(agentId);
  },
}));

export default useOutputStore;
