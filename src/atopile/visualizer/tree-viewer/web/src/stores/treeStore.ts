import { create } from 'zustand';
import type {
  PowerTreeData,
  I2CTreeData,
  TreeGraphData,
  ViewerMode,
} from '../types/tree';
import type { LayoutResult, NodePosition } from '../lib/layoutEngine';
import { computeTreeLayout } from '../lib/layoutEngine';
import { powerTreeToGraph, i2cTreeToGraph } from '../lib/dataTransform';

interface TreeState {
  mode: ViewerMode;
  isLoading: boolean;
  loadError: string | null;

  // Raw data
  powerData: PowerTreeData | null;
  i2cData: I2CTreeData | null;

  // Transformed + laid out
  graphData: TreeGraphData | null;
  layout: LayoutResult | null;

  // Interaction
  hoveredNode: string | null;
  selectedNode: string | null;

  // Actions
  setMode: (mode: ViewerMode) => void;
  loadData: (url: string) => Promise<void>;
  setHoveredNode: (id: string | null) => void;
  setSelectedNode: (id: string | null) => void;
}

export const useTreeStore = create<TreeState>((set, get) => ({
  mode: 'power',
  isLoading: false,
  loadError: null,
  powerData: null,
  i2cData: null,
  graphData: null,
  layout: null,
  hoveredNode: null,
  selectedNode: null,

  setMode: (mode: ViewerMode) => {
    set({ mode, selectedNode: null, hoveredNode: null });
  },

  loadData: async (url: string) => {
    set({ isLoading: true, loadError: null });
    try {
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      const rawData = await response.json();
      const { mode } = get();

      let graphData: TreeGraphData;

      if (mode === 'power') {
        const powerData = rawData as PowerTreeData;
        graphData = powerTreeToGraph(powerData);
        set({ powerData });
      } else {
        const i2cData = rawData as I2CTreeData;
        graphData = i2cTreeToGraph(i2cData);
        set({ i2cData });
      }

      const layout = computeTreeLayout(graphData);
      set({ graphData, layout, isLoading: false });
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Unknown error';
      set({ isLoading: false, loadError: msg });
    }
  },

  setHoveredNode: (id) => set({ hoveredNode: id }),
  setSelectedNode: (id) => set((state) => ({
    selectedNode: state.selectedNode === id ? null : id,
  })),
}));
