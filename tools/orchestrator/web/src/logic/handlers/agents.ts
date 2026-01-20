/**
 * Agent event handlers
 */

import type { UILogic } from '../index';
import type { UIEvent } from '../events';
import { setLoading, addError, updateMap, deleteFromMap } from '../state';

type AgentEvent = Extract<UIEvent, { type: `agents.${string}` }>;

export async function handleAgentEvent(
  logic: UILogic,
  event: AgentEvent
): Promise<void> {
  switch (event.type) {
    case 'agents.spawn':
      await handleSpawn(logic, event);
      break;
    case 'agents.select':
      handleSelect(logic, event);
      break;
    case 'agents.terminate':
      await handleTerminate(logic, event);
      break;
    case 'agents.delete':
      await handleDelete(logic, event);
      break;
    case 'agents.sendInput':
      await handleSendInput(logic, event);
      break;
    case 'agents.resume':
      await handleResume(logic, event);
      break;
    case 'agents.rename':
      await handleRename(logic, event);
      break;
    case 'agents.refresh':
      await handleRefresh(logic);
      break;
    case 'agents.refreshOne':
      await handleRefreshOne(logic, event);
      break;
  }
}

async function handleSpawn(
  logic: UILogic,
  event: Extract<UIEvent, { type: 'agents.spawn' }>
): Promise<void> {
  const { payload } = event;

  logic.setState((s) => setLoading(s, 'spawn', true));

  try {
    const response = await logic.api.agents.spawn(
      {
        backend: payload.backend,
        prompt: payload.prompt,
        working_directory: payload.workingDirectory,
        max_turns: payload.maxTurns,
        max_budget_usd: payload.maxBudgetUsd,
        system_prompt: payload.systemPrompt,
        model: payload.model,
      },
      payload.name
    );

    // Fetch the full agent state
    const agentResponse = await logic.api.agents.get(response.agent_id);

    logic.setState((s) => ({
      ...s,
      agents: updateMap(s.agents, response.agent_id, agentResponse.agent),
      selectedAgentId: response.agent_id,
      loading: { ...s.loading, spawn: false },
    }));
  } catch (e) {
    logic.setState((s) => ({
      ...setLoading(s, 'spawn', false),
      ...addError(s, e instanceof Error ? e.message : 'Failed to spawn agent', 'agents.spawn'),
    }));
    throw e;
  }
}

function handleSelect(
  logic: UILogic,
  event: Extract<UIEvent, { type: 'agents.select' }>
): void {
  logic.setState((s) => ({
    ...s,
    selectedAgentId: event.payload.agentId,
  }));
}

async function handleTerminate(
  logic: UILogic,
  event: Extract<UIEvent, { type: 'agents.terminate' }>
): Promise<void> {
  const { agentId, force } = event.payload;
  const loadingKey = `terminate-${agentId}`;

  logic.setState((s) => setLoading(s, loadingKey, true));

  try {
    await logic.api.agents.terminate(agentId, { force });

    // Fetch updated agent state
    const response = await logic.api.agents.get(agentId);

    logic.setState((s) => ({
      ...s,
      agents: updateMap(s.agents, agentId, response.agent),
      loading: { ...s.loading, [loadingKey]: false },
    }));
  } catch (e) {
    logic.setState((s) => ({
      ...setLoading(s, loadingKey, false),
      ...addError(s, e instanceof Error ? e.message : 'Failed to terminate agent', 'agents.terminate'),
    }));
    throw e;
  }
}

async function handleDelete(
  logic: UILogic,
  event: Extract<UIEvent, { type: 'agents.delete' }>
): Promise<void> {
  const { agentId } = event.payload;
  const loadingKey = `delete-${agentId}`;

  logic.setState((s) => setLoading(s, loadingKey, true));

  try {
    await logic.api.agents.delete(agentId);

    logic.setState((s) => {
      // Clear agent output data
      const newOutputs = new Map(s.agentOutputs);
      newOutputs.delete(agentId);

      return {
        ...s,
        agents: deleteFromMap(s.agents, agentId),
        agentOutputs: newOutputs,
        selectedAgentId: s.selectedAgentId === agentId ? null : s.selectedAgentId,
        loading: { ...s.loading, [loadingKey]: false },
      };
    });
  } catch (e) {
    logic.setState((s) => ({
      ...setLoading(s, loadingKey, false),
      ...addError(s, e instanceof Error ? e.message : 'Failed to delete agent', 'agents.delete'),
    }));
    throw e;
  }
}

async function handleSendInput(
  logic: UILogic,
  event: Extract<UIEvent, { type: 'agents.sendInput' }>
): Promise<void> {
  const { agentId, input } = event.payload;
  const loadingKey = `input-${agentId}`;

  logic.setState((s) => setLoading(s, loadingKey, true));

  try {
    await logic.api.agents.sendInput(agentId, input);

    logic.setState((s) => setLoading(s, loadingKey, false));
  } catch (e) {
    logic.setState((s) => ({
      ...setLoading(s, loadingKey, false),
      ...addError(s, e instanceof Error ? e.message : 'Failed to send input', 'agents.sendInput'),
    }));
  }
}

async function handleResume(
  logic: UILogic,
  event: Extract<UIEvent, { type: 'agents.resume' }>
): Promise<void> {
  const { agentId, prompt } = event.payload;
  const loadingKey = `resume-${agentId}`;

  logic.setState((s) => setLoading(s, loadingKey, true));

  try {
    await logic.api.agents.resume(agentId, prompt);

    // Fetch updated agent state
    const response = await logic.api.agents.get(agentId);
    const newRunCount = response.agent.run_count ?? 0;

    // Update agent state and add the new prompt to output
    logic.setState((s) => {
      // Add the prompt for the new run
      const currentOutput = s.agentOutputs.get(agentId) ?? {
        chunks: [],
        prompts: [],
        isConnected: false,
        hasHistory: false,
        currentRunNumber: 0,
      };

      // Check if prompt for this run already exists
      const hasPrompt = currentOutput.prompts.some((p) => p.run === newRunCount);
      const newPrompts = hasPrompt
        ? currentOutput.prompts
        : [...currentOutput.prompts, { run: newRunCount, prompt }];

      const newOutputs = new Map(s.agentOutputs);
      newOutputs.set(agentId, {
        ...currentOutput,
        prompts: newPrompts,
        currentRunNumber: newRunCount,
      });

      return {
        ...s,
        agents: updateMap(s.agents, agentId, response.agent),
        agentOutputs: newOutputs,
        loading: { ...s.loading, [loadingKey]: false },
      };
    });
  } catch (e) {
    logic.setState((s) => ({
      ...setLoading(s, loadingKey, false),
      ...addError(s, e instanceof Error ? e.message : 'Failed to resume agent', 'agents.resume'),
    }));
    throw e;
  }
}

async function handleRename(
  logic: UILogic,
  event: Extract<UIEvent, { type: 'agents.rename' }>
): Promise<void> {
  const { agentId, name } = event.payload;

  try {
    const response = await logic.api.agents.rename(agentId, name);

    logic.setState((s) => ({
      ...s,
      agents: updateMap(s.agents, agentId, response.agent),
    }));
  } catch (e) {
    logic.setState((s) =>
      addError(s, e instanceof Error ? e.message : 'Failed to rename agent', 'agents.rename')
    );
    throw e;
  }
}

async function handleRefresh(logic: UILogic): Promise<void> {
  logic.setState((s) => setLoading(s, 'agents', true));

  try {
    const response = await logic.api.agents.list({ limit: 100 });

    const agentsMap = new Map<string, (typeof response.agents)[0]>();
    for (const agent of response.agents) {
      agentsMap.set(agent.id, agent);
    }

    logic.setState((s) => ({
      ...s,
      agents: agentsMap,
      loading: { ...s.loading, agents: false },
    }));
  } catch (e) {
    logic.setState((s) => ({
      ...setLoading(s, 'agents', false),
      ...addError(s, e instanceof Error ? e.message : 'Failed to fetch agents', 'agents.refresh'),
    }));
  }
}

async function handleRefreshOne(
  logic: UILogic,
  event: Extract<UIEvent, { type: 'agents.refreshOne' }>
): Promise<void> {
  const { agentId } = event.payload;

  try {
    const response = await logic.api.agents.get(agentId);

    logic.setState((s) => ({
      ...s,
      agents: updateMap(s.agents, agentId, response.agent),
    }));
  } catch (e) {
    logic.setState((s) =>
      addError(s, e instanceof Error ? e.message : 'Failed to fetch agent', 'agents.refreshOne')
    );
  }
}
