import { create } from 'zustand';
import { api } from '@/api/client';
import type {
  Pipeline,
  PipelineNode,
  PipelineEdge,
  PipelineConfig,
  PipelineSession,
  CreatePipelineRequest,
} from '@/api/types';

interface PipelineStore {
  // State
  pipelines: Map<string, Pipeline>;
  selectedPipelineId: string | null;
  loading: boolean;
  error: string | null;

  // Session state
  sessions: Map<string, PipelineSession[]>;  // pipeline_id -> sessions
  selectedSessionId: string | null;

  // Editor state (for unsaved changes)
  editorNodes: PipelineNode[];
  editorEdges: PipelineEdge[];
  editorName: string;
  editorDescription: string;
  editorConfig: PipelineConfig;
  hasUnsavedChanges: boolean;

  // Actions
  fetchPipelines: () => Promise<void>;
  fetchPipeline: (id: string) => Promise<Pipeline | null>;
  selectPipeline: (id: string | null) => void;
  createPipeline: (pipeline: CreatePipelineRequest) => Promise<string>;
  updatePipeline: (id: string, updates: Partial<CreatePipelineRequest>) => Promise<void>;
  deletePipeline: (id: string) => Promise<void>;
  runPipeline: (id: string) => Promise<void>;
  pausePipeline: (id: string) => Promise<void>;
  resumePipeline: (id: string) => Promise<void>;
  stopPipeline: (id: string) => Promise<void>;

  // Session actions
  fetchSessions: (pipelineId: string) => Promise<void>;
  selectSession: (sessionId: string | null) => void;

  // Editor actions
  setEditorNodes: (nodes: PipelineNode[]) => void;
  setEditorEdges: (edges: PipelineEdge[]) => void;
  setEditorName: (name: string) => void;
  setEditorDescription: (description: string) => void;
  setEditorConfig: (config: PipelineConfig) => void;
  loadPipelineToEditor: (pipeline: Pipeline) => void;
  saveEditorPipeline: () => Promise<string>;
  resetEditor: () => void;

  // Computed
  getPipeline: (id: string) => Pipeline | undefined;
  getSelectedPipeline: () => Pipeline | undefined;
  getSessionsForPipeline: (pipelineId: string) => PipelineSession[];
  getSelectedSession: () => PipelineSession | undefined;
}

const defaultConfig: PipelineConfig = {
  parallel_execution: false,
  stop_on_failure: true,
};

export const usePipelineStore = create<PipelineStore>((set, get) => ({
  // Initial state
  pipelines: new Map(),
  selectedPipelineId: null,
  loading: false,
  error: null,

  // Session state
  sessions: new Map(),
  selectedSessionId: null,

  // Editor state
  editorNodes: [],
  editorEdges: [],
  editorName: 'New Pipeline',
  editorDescription: '',
  editorConfig: defaultConfig,
  hasUnsavedChanges: false,

  // Actions
  fetchPipelines: async () => {
    set({ loading: true, error: null });
    try {
      const response = await api.pipelines.list();
      const pipelinesMap = new Map<string, Pipeline>();
      for (const pipeline of response.pipelines) {
        pipelinesMap.set(pipeline.id, pipeline);
      }
      set({ pipelines: pipelinesMap, loading: false });
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to fetch pipelines', loading: false });
    }
  },

  fetchPipeline: async (id: string) => {
    try {
      const pipeline = await api.pipelines.get(id);
      const { pipelines } = get();
      const newPipelines = new Map(pipelines);
      newPipelines.set(id, pipeline);
      set({ pipelines: newPipelines });
      return pipeline;
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to fetch pipeline' });
      return null;
    }
  },

  selectPipeline: (id: string | null) => {
    set({ selectedPipelineId: id });
    if (id) {
      const pipeline = get().pipelines.get(id);
      if (pipeline) {
        get().loadPipelineToEditor(pipeline);
      }
    }
  },

  createPipeline: async (pipeline: CreatePipelineRequest) => {
    set({ loading: true, error: null });
    try {
      const created = await api.pipelines.create(pipeline);
      const { pipelines } = get();
      const newPipelines = new Map(pipelines);
      newPipelines.set(created.id, created);
      set({ pipelines: newPipelines, loading: false, selectedPipelineId: created.id });
      return created.id;
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to create pipeline', loading: false });
      throw e;
    }
  },

  updatePipeline: async (id: string, updates: Partial<CreatePipelineRequest>) => {
    try {
      const updated = await api.pipelines.update(id, updates);
      const { pipelines } = get();
      const newPipelines = new Map(pipelines);
      newPipelines.set(id, updated);
      set({ pipelines: newPipelines, hasUnsavedChanges: false });
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to update pipeline' });
      throw e;
    }
  },

  deletePipeline: async (id: string) => {
    try {
      await api.pipelines.delete(id);
      const { pipelines, selectedPipelineId } = get();
      const newPipelines = new Map(pipelines);
      newPipelines.delete(id);
      set({
        pipelines: newPipelines,
        selectedPipelineId: selectedPipelineId === id ? null : selectedPipelineId,
      });
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to delete pipeline' });
      throw e;
    }
  },

  runPipeline: async (id: string) => {
    try {
      await api.pipelines.run(id);
      await get().fetchPipeline(id);
      // Fetch sessions after running to get the new session
      await get().fetchSessions(id);
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to run pipeline' });
      throw e;
    }
  },

  pausePipeline: async (id: string) => {
    try {
      await api.pipelines.pause(id);
      await get().fetchPipeline(id);
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to pause pipeline' });
      throw e;
    }
  },

  resumePipeline: async (id: string) => {
    try {
      await api.pipelines.resume(id);
      await get().fetchPipeline(id);
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to resume pipeline' });
      throw e;
    }
  },

  stopPipeline: async (id: string) => {
    try {
      await api.pipelines.stop(id);
      await get().fetchPipeline(id);
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to stop pipeline' });
      throw e;
    }
  },

  // Session actions
  fetchSessions: async (pipelineId: string) => {
    try {
      const response = await api.pipelines.listSessions(pipelineId);
      const { sessions, selectedSessionId } = get();
      const newSessions = new Map(sessions);
      newSessions.set(pipelineId, response.sessions);

      // Auto-select the latest session if none selected or if current selection is for this pipeline
      let newSelectedSessionId = selectedSessionId;
      if (response.sessions.length > 0) {
        const currentSession = selectedSessionId
          ? response.sessions.find(s => s.id === selectedSessionId)
          : null;
        // If no session selected, or selected session is not in this pipeline, select the latest
        if (!currentSession) {
          newSelectedSessionId = response.sessions[0].id;
        }
      }

      set({ sessions: newSessions, selectedSessionId: newSelectedSessionId });
    } catch (e) {
      console.error('Failed to fetch sessions:', e);
    }
  },

  selectSession: (sessionId: string | null) => {
    set({ selectedSessionId: sessionId });
  },

  // Editor actions
  setEditorNodes: (nodes: PipelineNode[]) => {
    set({ editorNodes: nodes, hasUnsavedChanges: true });
  },

  setEditorEdges: (edges: PipelineEdge[]) => {
    set({ editorEdges: edges, hasUnsavedChanges: true });
  },

  setEditorName: (name: string) => {
    set({ editorName: name, hasUnsavedChanges: true });
  },

  setEditorDescription: (description: string) => {
    set({ editorDescription: description, hasUnsavedChanges: true });
  },

  setEditorConfig: (config: PipelineConfig) => {
    set({ editorConfig: config, hasUnsavedChanges: true });
  },

  loadPipelineToEditor: (pipeline: Pipeline) => {
    set({
      editorNodes: pipeline.nodes,
      editorEdges: pipeline.edges,
      editorName: pipeline.name,
      editorDescription: pipeline.description || '',
      editorConfig: pipeline.config,
      hasUnsavedChanges: false,
    });
  },

  saveEditorPipeline: async () => {
    const { selectedPipelineId, editorNodes, editorEdges, editorName, editorDescription, editorConfig } = get();

    const pipelineData: CreatePipelineRequest = {
      name: editorName,
      description: editorDescription || undefined,
      nodes: editorNodes,
      edges: editorEdges,
      config: editorConfig,
    };

    if (selectedPipelineId) {
      await get().updatePipeline(selectedPipelineId, pipelineData);
      return selectedPipelineId;
    } else {
      return get().createPipeline(pipelineData);
    }
  },

  resetEditor: () => {
    set({
      editorNodes: [],
      editorEdges: [],
      editorName: 'New Pipeline',
      editorDescription: '',
      editorConfig: defaultConfig,
      hasUnsavedChanges: false,
      selectedPipelineId: null,
    });
  },

  // Computed
  getPipeline: (id: string) => {
    return get().pipelines.get(id);
  },

  getSelectedPipeline: () => {
    const { pipelines, selectedPipelineId } = get();
    return selectedPipelineId ? pipelines.get(selectedPipelineId) : undefined;
  },

  getSessionsForPipeline: (pipelineId: string) => {
    return get().sessions.get(pipelineId) || [];
  },

  getSelectedSession: () => {
    const { sessions, selectedPipelineId, selectedSessionId } = get();
    if (!selectedPipelineId || !selectedSessionId) return undefined;
    const pipelineSessions = sessions.get(selectedPipelineId);
    return pipelineSessions?.find(s => s.id === selectedSessionId);
  },
}));

export default usePipelineStore;
