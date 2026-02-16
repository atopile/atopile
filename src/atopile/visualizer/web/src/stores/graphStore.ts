/**
 * Graph data store using Zustand.
 *
 * Manages graph loading, layout computation (via Web Worker), and positions.
 */

import { create } from 'zustand';
import type {
  GraphData,
  GraphIndex,
  NodePosition,
} from '../types/graph';
import { buildGraphIndex, getDepthStats } from '../lib/graphIndex';
import type {
  LayoutWorkerInput,
  LayoutWorkerOutput,
} from '../workers/layoutWorker';

interface GraphState {
  // Raw data
  data: GraphData | null;
  index: GraphIndex | null;
  isLoading: boolean;
  loadError: string | null;

  // Layout
  positions: Map<string, NodePosition>;
  bounds: { minX: number; maxX: number; minY: number; maxY: number };
  isLayoutRunning: boolean;
  layoutProgress: number;

  // Depth stats
  minDepth: number;
  maxDepth: number;

  // Worker reference
  layoutWorker: Worker | null;

  // Actions
  loadGraph: (url: string) => Promise<void>;
  setGraphData: (data: GraphData) => void;
  runLayout: (
    visibleNodes?: Set<string>,
    visibleEdges?: Set<string>,
    iterations?: number
  ) => void;
  cancelLayout: () => void;
  updatePosition: (nodeId: string, position: NodePosition) => void;
  updatePositions: (positions: Map<string, NodePosition>) => void;
}

export const useGraphStore = create<GraphState>((set, get) => ({
  data: null,
  index: null,
  isLoading: false,
  loadError: null,
  positions: new Map(),
  bounds: { minX: -250, maxX: 250, minY: -250, maxY: 250 },
  isLayoutRunning: false,
  layoutProgress: 0,
  minDepth: 0,
  maxDepth: 0,
  layoutWorker: null,

  loadGraph: async (url: string) => {
    set({ isLoading: true, loadError: null });

    try {
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const text = await response.text();
      let data: GraphData;

      try {
        data = JSON.parse(text);
      } catch (parseError) {
        console.error('JSON parse error:', parseError);
        console.error('Response text (first 500 chars):', text.slice(0, 500));
        throw new Error(`Invalid JSON format: ${parseError}`);
      }

      // Validate structure
      if (!data.nodes || !data.edges || !data.metadata) {
        throw new Error('Invalid graph format: missing nodes, edges, or metadata');
      }

      get().setGraphData(data);
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Unknown error';
      set({
        isLoading: false,
        loadError: `Failed to load graph: ${message}`,
      });
    }
  },

  setGraphData: (data: GraphData) => {
    // Terminate any existing worker
    const existingWorker = get().layoutWorker;
    if (existingWorker) {
      existingWorker.terminate();
    }

    const index = buildGraphIndex(data);
    const depthStats = getDepthStats(data);

    set({
      data,
      index,
      isLoading: false,
      loadError: null,
      minDepth: depthStats.min,
      maxDepth: depthStats.max,
      layoutWorker: null,
    });

    // Run initial layout
    get().runLayout();
  },

  runLayout: (
    visibleNodes?: Set<string>,
    visibleEdges?: Set<string>,
    iterations: number = 150
  ) => {
    const { data, isLayoutRunning, layoutWorker } = get();
    if (!data) return;

    // Cancel any existing layout
    if (isLayoutRunning && layoutWorker) {
      layoutWorker.terminate();
    }

    set({ isLayoutRunning: true, layoutProgress: 0 });

    // Prepare data for worker
    const nodeIds = visibleNodes ?? new Set(data.nodes.map((n) => n.id));
    const edgeIds = visibleEdges ?? new Set(data.edges.map((e) => e.id));

    const nodes = data.nodes
      .filter((n) => nodeIds.has(n.id))
      .map((n) => ({
        id: n.id,
        depth: n.depth,
        childCount: n.childCount,
        parentId: n.parentId,
      }));

    const edges = data.edges
      .filter((e) => edgeIds.has(e.id))
      .map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        type: e.type,
      }));

    // Create worker
    const worker = new Worker(
      new URL('../workers/layoutWorker.ts', import.meta.url),
      { type: 'module' }
    );

    worker.onmessage = (event: MessageEvent<LayoutWorkerOutput>) => {
      const { type, progress, positions, bounds, error } = event.data;

      if (type === 'progress') {
        set({ layoutProgress: progress ?? 0 });
      } else if (type === 'complete' && positions && bounds) {
        const positionMap = new Map<string, NodePosition>();
        for (const [nodeId, pos] of Object.entries(positions)) {
          positionMap.set(nodeId, pos);
        }

        set({
          positions: positionMap,
          bounds,
          isLayoutRunning: false,
          layoutProgress: 1,
          layoutWorker: null,
        });

        worker.terminate();
      } else if (type === 'error') {
        console.error('Layout worker error:', error);
        set({
          isLayoutRunning: false,
          layoutProgress: 0,
          layoutWorker: null,
        });
        worker.terminate();
      }
    };

    worker.onerror = (error) => {
      console.error('Layout worker error:', error);
      set({
        isLayoutRunning: false,
        layoutProgress: 0,
        layoutWorker: null,
      });
      worker.terminate();
    };

    // Store worker reference and start computation
    set({ layoutWorker: worker });

    const input: LayoutWorkerInput = {
      type: 'compute',
      nodes,
      edges,
      options: {
        iterations,
        edgeWeightByType: {
          composition: 3,
          connection: 2,
          trait: 1,
          pointer: 0.5,
          operand: 1,
          type: 0.5,
          next: 1,
        },
        includeEdgeTypes: ['composition', 'connection', 'trait'],
      },
    };

    worker.postMessage(input);
  },

  cancelLayout: () => {
    const { layoutWorker } = get();
    if (layoutWorker) {
      layoutWorker.terminate();
      set({
        isLayoutRunning: false,
        layoutProgress: 0,
        layoutWorker: null,
      });
    }
  },

  updatePosition: (nodeId: string, position: NodePosition) => {
    const positions = new Map(get().positions);
    positions.set(nodeId, position);
    set({ positions });
  },

  updatePositions: (positions: Map<string, NodePosition>) => {
    set({ positions });
  },
}));
