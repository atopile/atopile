import { create } from 'zustand';
import { api } from '@/api/client';
import { wsManager } from '@/api/websocket';
import type { OutputChunk, StreamEvent } from '@/api/types';
import { useAgentStore } from './agentStore';

interface PromptInfo {
  run: number;
  prompt: string;
}

interface OutputStore {
  // State
  outputs: Map<string, OutputChunk[]>;
  prompts: Map<string, PromptInfo[]>;  // Prompts per agent, indexed by run number
  connections: Set<string>;
  maxChunksPerAgent: number;
  historyLoaded: Set<string>;  // Track which agents have full history loaded
  currentRunNumber: Map<string, number>;  // Track current run number per agent for WebSocket chunks

  // Actions
  addChunk: (agentId: string, chunk: OutputChunk, runNumber?: number) => void;
  addPrompt: (agentId: string, run: number, prompt: string) => void;
  clearOutput: (agentId: string) => void;
  fetchOutput: (agentId: string, runNumber?: number) => Promise<void>;
  fetchFullHistory: (agentId: string) => Promise<void>;
  setCurrentRunNumber: (agentId: string, runNumber: number) => void;
  connectToAgent: (agentId: string) => void;
  disconnectFromAgent: (agentId: string) => void;
  disconnectAll: () => void;

  // Computed
  getOutput: (agentId: string) => OutputChunk[];
  getPrompts: (agentId: string) => PromptInfo[];
  isConnected: (agentId: string) => boolean;
  hasHistory: (agentId: string) => boolean;
  getCurrentRunNumber: (agentId: string) => number;
}

export const useOutputStore = create<OutputStore>((set, get) => ({
  // Initial state
  outputs: new Map(),
  prompts: new Map(),
  connections: new Set(),
  maxChunksPerAgent: 10000,  // Increased for multi-run history
  historyLoaded: new Set(),
  currentRunNumber: new Map(),

  // Actions
  addChunk: (agentId: string, chunk: OutputChunk, runNumber?: number) => {
    const { outputs, maxChunksPerAgent, currentRunNumber } = get();
    const agentOutput = outputs.get(agentId) || [];

    // Use provided runNumber, or fall back to tracked current run number
    const effectiveRunNumber = runNumber ?? currentRunNumber.get(agentId);

    // Add run_number to chunk if we have one
    const chunkWithRun = effectiveRunNumber !== undefined
      ? { ...chunk, run_number: effectiveRunNumber }
      : chunk;

    // Avoid duplicates by sequence number AND run_number
    const isDuplicate = agentOutput.some((c) =>
      c.sequence === chunkWithRun.sequence &&
      c.run_number === chunkWithRun.run_number
    );
    if (isDuplicate) {
      return;
    }

    // Add chunk and trim if needed
    const newOutput = [...agentOutput, chunkWithRun];
    if (newOutput.length > maxChunksPerAgent) {
      newOutput.splice(0, newOutput.length - maxChunksPerAgent);
    }

    const newOutputs = new Map(outputs);
    newOutputs.set(agentId, newOutput);
    set({ outputs: newOutputs });
  },

  addPrompt: (agentId: string, run: number, prompt: string) => {
    const { prompts } = get();
    const agentPrompts = prompts.get(agentId) || [];
    // Avoid duplicates
    if (!agentPrompts.some(p => p.run === run)) {
      const newPrompts = new Map(prompts);
      newPrompts.set(agentId, [...agentPrompts, { run, prompt }]);
      set({ prompts: newPrompts });
    }
  },

  clearOutput: (agentId: string) => {
    const { outputs, prompts, historyLoaded, currentRunNumber } = get();
    const newOutputs = new Map(outputs);
    newOutputs.delete(agentId);
    const newPrompts = new Map(prompts);
    newPrompts.delete(agentId);
    const newHistoryLoaded = new Set(historyLoaded);
    newHistoryLoaded.delete(agentId);
    const newCurrentRunNumber = new Map(currentRunNumber);
    newCurrentRunNumber.delete(agentId);
    set({ outputs: newOutputs, prompts: newPrompts, historyLoaded: newHistoryLoaded, currentRunNumber: newCurrentRunNumber });
  },

  fetchOutput: async (agentId: string, runNumber?: number) => {
    try {
      const { outputs, currentRunNumber } = get();
      const existing = outputs.get(agentId) || [];

      // Set current run number if provided
      if (runNumber !== undefined) {
        const newCurrentRunNumber = new Map(currentRunNumber);
        newCurrentRunNumber.set(agentId, runNumber);
        set({ currentRunNumber: newCurrentRunNumber });
      }

      // Find highest sequence for current run
      const effectiveRunNumber = runNumber ?? currentRunNumber.get(agentId);
      let sinceSequence = 0;

      if (existing.length > 0) {
        // Filter chunks for current run
        const currentRunChunks = effectiveRunNumber !== undefined
          ? existing.filter(c => c.run_number === effectiveRunNumber)
          : existing.filter(c => c.run_number === undefined);

        if (currentRunChunks.length > 0) {
          sinceSequence = Math.max(...currentRunChunks.map(c => c.sequence));
        }
      }

      const response = await api.agents.getOutput(agentId, sinceSequence);

      // Add new chunks with the current run number
      for (const chunk of response.chunks) {
        get().addChunk(agentId, chunk as OutputChunk, effectiveRunNumber);
      }
    } catch (e) {
      console.error('Failed to fetch output:', e);
    }
  },

  fetchFullHistory: async (agentId: string) => {
    try {
      const response = await api.agents.getHistory(agentId);

      // Clear existing output and replace with full history
      const { outputs, prompts, historyLoaded, currentRunNumber } = get();
      const newOutputs = new Map(outputs);
      const newPrompts = new Map(prompts);
      const allChunks: OutputChunk[] = [];
      const allPrompts: PromptInfo[] = [];

      let maxRunNumber = 0;

      // Combine all runs, preserving run_number and prompts
      for (const run of response.runs) {
        maxRunNumber = Math.max(maxRunNumber, run.run_number);
        // Store prompt for this run
        if (run.prompt) {
          allPrompts.push({ run: run.run_number, prompt: run.prompt });
        }
        for (const chunk of run.chunks) {
          allChunks.push({
            ...(chunk as OutputChunk),
            run_number: run.run_number,
          });
        }
      }

      newOutputs.set(agentId, allChunks);
      newPrompts.set(agentId, allPrompts);

      // Mark history as loaded and track current run number
      const newHistoryLoaded = new Set(historyLoaded);
      newHistoryLoaded.add(agentId);

      const newCurrentRunNumber = new Map(currentRunNumber);
      newCurrentRunNumber.set(agentId, maxRunNumber);

      set({ outputs: newOutputs, prompts: newPrompts, historyLoaded: newHistoryLoaded, currentRunNumber: newCurrentRunNumber });
    } catch (e) {
      console.error('Failed to fetch full history:', e);
    }
  },

  setCurrentRunNumber: (agentId: string, runNumber: number) => {
    const { currentRunNumber } = get();
    const newCurrentRunNumber = new Map(currentRunNumber);
    newCurrentRunNumber.set(agentId, runNumber);
    set({ currentRunNumber: newCurrentRunNumber });
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

  getPrompts: (agentId: string) => {
    return get().prompts.get(agentId) || [];
  },

  isConnected: (agentId: string) => {
    return get().connections.has(agentId);
  },

  hasHistory: (agentId: string) => {
    return get().historyLoaded.has(agentId);
  },

  getCurrentRunNumber: (agentId: string) => {
    return get().currentRunNumber.get(agentId) ?? 0;
  },
}));

export default useOutputStore;
