/**
 * Pipeline event handlers
 */

import type { UILogic } from '../index';
import type { UIEvent } from '../events';
import type { Pipeline } from '../api/types';
import {
  setLoading,
  addError,
  updateMap,
  deleteFromMap,
  defaultPipelineConfig,
} from '../state';

type PipelineEvent = Extract<UIEvent, { type: `pipelines.${string}` }>;
type SessionEvent = Extract<UIEvent, { type: `sessions.${string}` }>;
type EditorEvent = Extract<UIEvent, { type: `editor.${string}` }>;

export async function handlePipelineEvent(
  logic: UILogic,
  event: PipelineEvent
): Promise<void> {
  switch (event.type) {
    case 'pipelines.select':
      handleSelect(logic, event);
      break;
    case 'pipelines.create':
      await handleCreate(logic, event);
      break;
    case 'pipelines.update':
      await handleUpdate(logic, event);
      break;
    case 'pipelines.delete':
      await handleDelete(logic, event);
      break;
    case 'pipelines.run':
      await handleRun(logic, event);
      break;
    case 'pipelines.pause':
      await handlePause(logic, event);
      break;
    case 'pipelines.resume':
      await handleResume(logic, event);
      break;
    case 'pipelines.stop':
      await handleStop(logic, event);
      break;
    case 'pipelines.refresh':
      await handleRefresh(logic);
      break;
  }
}

export async function handleSessionEvent(
  logic: UILogic,
  event: SessionEvent
): Promise<void> {
  switch (event.type) {
    case 'sessions.select':
      handleSessionSelect(logic, event);
      break;
    case 'sessions.fetch':
      await handleSessionFetch(logic, event);
      break;
    case 'sessions.stop':
      await handleSessionStop(logic, event);
      break;
    case 'sessions.delete':
      await handleSessionDelete(logic, event);
      break;
  }
}

export function handleEditorEvent(logic: UILogic, event: EditorEvent): void {
  switch (event.type) {
    case 'editor.setNodes':
      logic.setState((s) => ({
        ...s,
        editor: { ...s.editor, nodes: event.payload.nodes, hasUnsavedChanges: true },
      }));
      break;
    case 'editor.setEdges':
      logic.setState((s) => ({
        ...s,
        editor: { ...s.editor, edges: event.payload.edges, hasUnsavedChanges: true },
      }));
      break;
    case 'editor.setName':
      logic.setState((s) => ({
        ...s,
        editor: { ...s.editor, name: event.payload.name, hasUnsavedChanges: true },
      }));
      break;
    case 'editor.setDescription':
      logic.setState((s) => ({
        ...s,
        editor: { ...s.editor, description: event.payload.description, hasUnsavedChanges: true },
      }));
      break;
    case 'editor.setConfig':
      logic.setState((s) => ({
        ...s,
        editor: { ...s.editor, config: event.payload.config, hasUnsavedChanges: true },
      }));
      break;
    case 'editor.loadPipeline':
      handleEditorLoadPipeline(logic, event);
      break;
    case 'editor.save':
      handleEditorSave(logic);
      break;
    case 'editor.reset':
      handleEditorReset(logic);
      break;
  }
}

// Pipeline handlers

function handleSelect(
  logic: UILogic,
  event: Extract<UIEvent, { type: 'pipelines.select' }>
): void {
  const { pipelineId } = event.payload;

  logic.setState((s) => ({ ...s, selectedPipelineId: pipelineId }));

  // Load pipeline to editor if selected
  if (pipelineId) {
    const pipeline = logic.getState().pipelines.get(pipelineId);
    if (pipeline) {
      loadPipelineToEditor(logic, pipeline);
    }
  }
}

async function handleCreate(
  logic: UILogic,
  event: Extract<UIEvent, { type: 'pipelines.create' }>
): Promise<void> {
  logic.setState((s) => setLoading(s, 'createPipeline', true));

  try {
    const pipeline = await logic.api.pipelines.create(event.payload);

    logic.setState((s) => ({
      ...s,
      pipelines: updateMap(s.pipelines, pipeline.id, pipeline),
      selectedPipelineId: pipeline.id,
      loading: { ...s.loading, createPipeline: false },
    }));
  } catch (e) {
    logic.setState((s) => ({
      ...setLoading(s, 'createPipeline', false),
      ...addError(s, e instanceof Error ? e.message : 'Failed to create pipeline', 'pipelines.create'),
    }));
    throw e;
  }
}

async function handleUpdate(
  logic: UILogic,
  event: Extract<UIEvent, { type: 'pipelines.update' }>
): Promise<void> {
  const { pipelineId, ...updates } = event.payload;

  try {
    const pipeline = await logic.api.pipelines.update(pipelineId, updates);

    logic.setState((s) => ({
      ...s,
      pipelines: updateMap(s.pipelines, pipelineId, pipeline),
      editor: { ...s.editor, hasUnsavedChanges: false },
    }));
  } catch (e) {
    logic.setState((s) =>
      addError(s, e instanceof Error ? e.message : 'Failed to update pipeline', 'pipelines.update')
    );
    throw e;
  }
}

async function handleDelete(
  logic: UILogic,
  event: Extract<UIEvent, { type: 'pipelines.delete' }>
): Promise<void> {
  const { pipelineId } = event.payload;

  try {
    await logic.api.pipelines.delete(pipelineId);

    logic.setState((s) => {
      // Also remove sessions for this pipeline
      const newSessions = new Map(s.pipelineSessions);
      newSessions.delete(pipelineId);

      return {
        ...s,
        pipelines: deleteFromMap(s.pipelines, pipelineId),
        pipelineSessions: newSessions,
        selectedPipelineId: s.selectedPipelineId === pipelineId ? null : s.selectedPipelineId,
      };
    });
  } catch (e) {
    logic.setState((s) =>
      addError(s, e instanceof Error ? e.message : 'Failed to delete pipeline', 'pipelines.delete')
    );
    throw e;
  }
}

async function handleRun(
  logic: UILogic,
  event: Extract<UIEvent, { type: 'pipelines.run' }>
): Promise<void> {
  const { pipelineId } = event.payload;

  try {
    await logic.api.pipelines.run(pipelineId);

    // Fetch updated pipeline state
    const pipeline = await logic.api.pipelines.get(pipelineId);
    logic.setState((s) => ({
      ...s,
      pipelines: updateMap(s.pipelines, pipelineId, pipeline),
    }));

    // Fetch sessions to get the new session
    await fetchSessions(logic, pipelineId);
  } catch (e) {
    logic.setState((s) =>
      addError(s, e instanceof Error ? e.message : 'Failed to run pipeline', 'pipelines.run')
    );
    throw e;
  }
}

async function handlePause(
  logic: UILogic,
  event: Extract<UIEvent, { type: 'pipelines.pause' }>
): Promise<void> {
  const { pipelineId } = event.payload;

  try {
    await logic.api.pipelines.pause(pipelineId);

    const pipeline = await logic.api.pipelines.get(pipelineId);
    logic.setState((s) => ({
      ...s,
      pipelines: updateMap(s.pipelines, pipelineId, pipeline),
    }));
  } catch (e) {
    logic.setState((s) =>
      addError(s, e instanceof Error ? e.message : 'Failed to pause pipeline', 'pipelines.pause')
    );
    throw e;
  }
}

async function handleResume(
  logic: UILogic,
  event: Extract<UIEvent, { type: 'pipelines.resume' }>
): Promise<void> {
  const { pipelineId } = event.payload;

  try {
    await logic.api.pipelines.resume(pipelineId);

    const pipeline = await logic.api.pipelines.get(pipelineId);
    logic.setState((s) => ({
      ...s,
      pipelines: updateMap(s.pipelines, pipelineId, pipeline),
    }));
  } catch (e) {
    logic.setState((s) =>
      addError(s, e instanceof Error ? e.message : 'Failed to resume pipeline', 'pipelines.resume')
    );
    throw e;
  }
}

async function handleStop(
  logic: UILogic,
  event: Extract<UIEvent, { type: 'pipelines.stop' }>
): Promise<void> {
  const { pipelineId } = event.payload;

  try {
    await logic.api.pipelines.stop(pipelineId);

    const pipeline = await logic.api.pipelines.get(pipelineId);
    logic.setState((s) => ({
      ...s,
      pipelines: updateMap(s.pipelines, pipelineId, pipeline),
    }));
  } catch (e) {
    logic.setState((s) =>
      addError(s, e instanceof Error ? e.message : 'Failed to stop pipeline', 'pipelines.stop')
    );
    throw e;
  }
}

async function handleRefresh(logic: UILogic): Promise<void> {
  logic.setState((s) => setLoading(s, 'pipelines', true));

  try {
    const response = await logic.api.pipelines.list();

    const pipelinesMap = new Map<string, Pipeline>();
    for (const pipeline of response.pipelines) {
      pipelinesMap.set(pipeline.id, pipeline);
    }

    logic.setState((s) => ({
      ...s,
      pipelines: pipelinesMap,
      loading: { ...s.loading, pipelines: false },
    }));
  } catch (e) {
    logic.setState((s) => ({
      ...setLoading(s, 'pipelines', false),
      ...addError(s, e instanceof Error ? e.message : 'Failed to fetch pipelines', 'pipelines.refresh'),
    }));
  }
}

// Session handlers

function handleSessionSelect(
  logic: UILogic,
  event: Extract<UIEvent, { type: 'sessions.select' }>
): void {
  logic.setState((s) => ({
    ...s,
    selectedSessionId: event.payload.sessionId,
  }));
}

async function handleSessionFetch(
  logic: UILogic,
  event: Extract<UIEvent, { type: 'sessions.fetch' }>
): Promise<void> {
  await fetchSessions(logic, event.payload.pipelineId);
}

async function handleSessionStop(
  logic: UILogic,
  event: Extract<UIEvent, { type: 'sessions.stop' }>
): Promise<void> {
  const { pipelineId, sessionId, force } = event.payload;

  try {
    await logic.api.pipelines.stopSession(pipelineId, sessionId, force);
    await fetchSessions(logic, pipelineId);
  } catch (e) {
    logic.setState((s) =>
      addError(s, e instanceof Error ? e.message : 'Failed to stop session', 'sessions.stop')
    );
    throw e;
  }
}

async function handleSessionDelete(
  logic: UILogic,
  event: Extract<UIEvent, { type: 'sessions.delete' }>
): Promise<void> {
  const { pipelineId, sessionId, force } = event.payload;

  try {
    await logic.api.pipelines.deleteSession(pipelineId, sessionId, force);

    logic.setState((s) => {
      const currentSessions = s.pipelineSessions.get(pipelineId) || [];
      const newSessions = currentSessions.filter((session) => session.id !== sessionId);
      const newPipelineSessions = new Map(s.pipelineSessions);
      newPipelineSessions.set(pipelineId, newSessions);

      return {
        ...s,
        pipelineSessions: newPipelineSessions,
        selectedSessionId: s.selectedSessionId === sessionId ? null : s.selectedSessionId,
      };
    });
  } catch (e) {
    logic.setState((s) =>
      addError(s, e instanceof Error ? e.message : 'Failed to delete session', 'sessions.delete')
    );
    throw e;
  }
}

// Helper function for fetching sessions
async function fetchSessions(logic: UILogic, pipelineId: string): Promise<void> {
  try {
    const response = await logic.api.pipelines.listSessions(pipelineId);

    logic.setState((s) => {
      const newSessions = new Map(s.pipelineSessions);
      newSessions.set(pipelineId, response.sessions);

      // Auto-select the latest session if none selected
      let newSelectedSessionId = s.selectedSessionId;
      if (response.sessions.length > 0) {
        const currentSession = s.selectedSessionId
          ? response.sessions.find((session) => session.id === s.selectedSessionId)
          : null;
        if (!currentSession) {
          newSelectedSessionId = response.sessions[0].id;
        }
      }

      return {
        ...s,
        pipelineSessions: newSessions,
        selectedSessionId: newSelectedSessionId,
      };
    });
  } catch (e) {
    console.error('Failed to fetch sessions:', e);
  }
}

// Editor handlers

function handleEditorLoadPipeline(
  logic: UILogic,
  event: Extract<UIEvent, { type: 'editor.loadPipeline' }>
): void {
  const pipeline = logic.getState().pipelines.get(event.payload.pipelineId);
  if (pipeline) {
    loadPipelineToEditor(logic, pipeline);
  }
}

async function handleEditorSave(logic: UILogic): Promise<void> {
  const state = logic.getState();
  const { editor, selectedPipelineId } = state;

  const pipelineData = {
    name: editor.name,
    description: editor.description || undefined,
    nodes: editor.nodes,
    edges: editor.edges,
    config: editor.config,
  };

  if (selectedPipelineId) {
    // Update existing pipeline
    await logic.dispatch({
      type: 'pipelines.update',
      payload: { pipelineId: selectedPipelineId, ...pipelineData },
    });
  } else {
    // Create new pipeline
    await logic.dispatch({
      type: 'pipelines.create',
      payload: pipelineData,
    });
  }
}

function handleEditorReset(logic: UILogic): void {
  logic.setState((s) => ({
    ...s,
    editor: {
      nodes: [],
      edges: [],
      name: 'New Pipeline',
      description: '',
      config: defaultPipelineConfig,
      hasUnsavedChanges: false,
    },
    selectedPipelineId: null,
  }));
}

// Helper to load a pipeline into the editor
function loadPipelineToEditor(logic: UILogic, pipeline: Pipeline): void {
  logic.setState((s) => ({
    ...s,
    editor: {
      nodes: pipeline.nodes,
      edges: pipeline.edges,
      name: pipeline.name,
      description: pipeline.description || '',
      config: pipeline.config,
      hasUnsavedChanges: false,
    },
  }));
}
