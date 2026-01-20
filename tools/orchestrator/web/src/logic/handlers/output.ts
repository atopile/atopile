/**
 * Output event handlers - handles agent output streaming and history
 */

import type { UILogic } from '../index';
import type { UIEvent } from '../events';
import type { OutputChunk, StreamEvent } from '../api/types';
import {
  getAgentOutput,
  setAgentOutput,
  addError,
} from '../state';

type OutputEvent = Extract<UIEvent, { type: `output.${string}` }>;

const MAX_CHUNKS_PER_AGENT = 10000;

export async function handleOutputEvent(
  logic: UILogic,
  event: OutputEvent
): Promise<void> {
  switch (event.type) {
    case 'output.connect':
      handleConnect(logic, event);
      break;
    case 'output.disconnect':
      handleDisconnect(logic, event);
      break;
    case 'output.fetch':
      await handleFetch(logic, event);
      break;
    case 'output.fetchHistory':
      await handleFetchHistory(logic, event);
      break;
    case 'output.clear':
      handleClear(logic, event);
      break;
    case 'output.setRunNumber':
      handleSetRunNumber(logic, event);
      break;
  }
}

function handleConnect(
  logic: UILogic,
  event: Extract<UIEvent, { type: 'output.connect' }>
): void {
  const { agentId } = event.payload;

  // Check if already connected
  const currentOutput = getAgentOutput(logic.getState(), agentId);
  if (currentOutput.isConnected) {
    return;
  }

  const handleMessage = (wsEvent: StreamEvent) => {
    if (wsEvent.type === 'agent_output' && wsEvent.chunk) {
      addChunk(logic, agentId, wsEvent.chunk);
    } else if (
      wsEvent.type === 'agent_completed' ||
      wsEvent.type === 'agent_failed' ||
      wsEvent.type === 'agent_terminated'
    ) {
      // Update agent status
      const status =
        wsEvent.type === 'agent_completed'
          ? 'completed'
          : wsEvent.type === 'agent_failed'
          ? 'failed'
          : 'terminated';

      const state = logic.getState();
      const agent = state.agents.get(agentId);
      if (agent) {
        const newAgents = new Map(state.agents);
        newAgents.set(agentId, { ...agent, status });
        logic.setState((s) => ({ ...s, agents: newAgents }));
      }
    }
  };

  const handleClose = () => {
    logic.setState((s) =>
      setAgentOutput(s, agentId, (output) => ({
        ...output,
        isConnected: false,
      }))
    );
  };

  logic.ws.connect(agentId, handleMessage, undefined, handleClose);

  logic.setState((s) =>
    setAgentOutput(s, agentId, (output) => ({
      ...output,
      isConnected: true,
    }))
  );
}

function handleDisconnect(
  logic: UILogic,
  event: Extract<UIEvent, { type: 'output.disconnect' }>
): void {
  const { agentId } = event.payload;

  logic.ws.disconnect(agentId);

  logic.setState((s) =>
    setAgentOutput(s, agentId, (output) => ({
      ...output,
      isConnected: false,
    }))
  );
}

async function handleFetch(
  logic: UILogic,
  event: Extract<UIEvent, { type: 'output.fetch' }>
): Promise<void> {
  const { agentId, runNumber } = event.payload;

  try {
    const state = logic.getState();
    const currentOutput = getAgentOutput(state, agentId);

    // Update current run number if provided
    if (runNumber !== undefined) {
      logic.setState((s) =>
        setAgentOutput(s, agentId, (output) => ({
          ...output,
          currentRunNumber: runNumber,
        }))
      );
    }

    const effectiveRunNumber = runNumber ?? currentOutput.currentRunNumber;

    // Find highest sequence for current run
    let sinceSequence = 0;
    if (currentOutput.chunks.length > 0) {
      const currentRunChunks =
        effectiveRunNumber !== undefined
          ? currentOutput.chunks.filter((c) => c.run_number === effectiveRunNumber)
          : currentOutput.chunks.filter((c) => c.run_number === undefined);

      if (currentRunChunks.length > 0) {
        sinceSequence = Math.max(...currentRunChunks.map((c) => c.sequence));
      }
    }

    const response = await logic.api.agents.getOutput(agentId, sinceSequence);

    // Add new chunks with the current run number
    for (const chunk of response.chunks) {
      addChunk(logic, agentId, chunk, effectiveRunNumber);
    }
  } catch (e) {
    console.error('Failed to fetch output:', e);
  }
}

async function handleFetchHistory(
  logic: UILogic,
  event: Extract<UIEvent, { type: 'output.fetchHistory' }>
): Promise<void> {
  const { agentId } = event.payload;

  try {
    const response = await logic.api.agents.getHistory(agentId);

    const allChunks: OutputChunk[] = [];
    const allPrompts: { run: number; prompt: string }[] = [];
    let maxRunNumber = 0;

    // Combine all runs, preserving run_number and prompts
    for (const run of response.runs) {
      maxRunNumber = Math.max(maxRunNumber, run.run_number);

      if (run.prompt) {
        allPrompts.push({ run: run.run_number, prompt: run.prompt });
      }

      for (const chunk of run.chunks) {
        allChunks.push({
          ...chunk,
          run_number: run.run_number,
        });
      }
    }

    logic.setState((s) =>
      setAgentOutput(s, agentId, () => ({
        chunks: allChunks,
        prompts: allPrompts,
        isConnected: getAgentOutput(s, agentId).isConnected,
        hasHistory: true,
        currentRunNumber: maxRunNumber,
      }))
    );
  } catch (e) {
    console.error('Failed to fetch full history:', e);
    logic.setState((s) =>
      addError(s, e instanceof Error ? e.message : 'Failed to fetch history', 'output.fetchHistory')
    );
  }
}

function handleClear(
  logic: UILogic,
  event: Extract<UIEvent, { type: 'output.clear' }>
): void {
  const { agentId } = event.payload;

  logic.setState((s) => {
    const newOutputs = new Map(s.agentOutputs);
    newOutputs.delete(agentId);
    return { ...s, agentOutputs: newOutputs };
  });
}

function handleSetRunNumber(
  logic: UILogic,
  event: Extract<UIEvent, { type: 'output.setRunNumber' }>
): void {
  const { agentId, runNumber } = event.payload;

  logic.setState((s) =>
    setAgentOutput(s, agentId, (output) => ({
      ...output,
      currentRunNumber: runNumber,
    }))
  );
}

// Helper function to add a chunk with deduplication
function addChunk(
  logic: UILogic,
  agentId: string,
  chunk: OutputChunk,
  runNumber?: number
): void {
  logic.setState((s) => {
    const currentOutput = getAgentOutput(s, agentId);

    // Use provided runNumber, or fall back to tracked current run number
    const effectiveRunNumber = runNumber ?? currentOutput.currentRunNumber;

    // Add run_number to chunk if we have one
    const chunkWithRun =
      effectiveRunNumber !== undefined
        ? { ...chunk, run_number: effectiveRunNumber }
        : chunk;

    // Avoid duplicates by sequence number AND run_number
    const isDuplicate = currentOutput.chunks.some(
      (c) =>
        c.sequence === chunkWithRun.sequence &&
        c.run_number === chunkWithRun.run_number
    );

    if (isDuplicate) {
      return s;
    }

    // Add chunk and trim if needed
    let newChunks = [...currentOutput.chunks, chunkWithRun];
    if (newChunks.length > MAX_CHUNKS_PER_AGENT) {
      newChunks = newChunks.slice(newChunks.length - MAX_CHUNKS_PER_AGENT);
    }

    return setAgentOutput(s, agentId, (output) => ({
      ...output,
      chunks: newChunks,
    }));
  });
}

// Helper to add a prompt
export function addPrompt(
  logic: UILogic,
  agentId: string,
  run: number,
  prompt: string
): void {
  logic.setState((s) => {
    const currentOutput = getAgentOutput(s, agentId);

    // Avoid duplicates
    if (currentOutput.prompts.some((p) => p.run === run)) {
      return s;
    }

    return setAgentOutput(s, agentId, (output) => ({
      ...output,
      prompts: [...output.prompts, { run, prompt }],
    }));
  });
}
