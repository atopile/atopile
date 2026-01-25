/**
 * Collapse state store using Zustand.
 */

import { create } from 'zustand';
import type { CollapseState, GraphData, GraphIndex } from '../types/graph';
import {
  getDefaultCollapseState,
  toggleNodeCollapse,
  expandNode,
  collapseNode,
  collapseAtDepth,
  expandAtDepth,
  expandAll,
  collapseAll,
  toggleTraitCollapse,
  collapseNodesAtOrBelowDepth,
} from '../lib/collapseEngine';

interface CollapseStoreState {
  state: CollapseState;

  // Actions
  toggleCollapse: (nodeId: string) => void;
  expand: (nodeId: string, index: GraphIndex, expandAncestors?: boolean) => void;
  collapse: (nodeId: string) => void;
  collapseDepth: (depth: number, data: GraphData) => void;
  expandDepth: (depth: number, data: GraphData) => void;
  collapseToDepth: (depth: number, data: GraphData, index: GraphIndex) => void;
  expandAllNodes: () => void;
  collapseAllNodes: (data: GraphData) => void;
  toggleTraits: () => void;
  reset: () => void;
}

export const useCollapseStore = create<CollapseStoreState>((set, get) => ({
  state: getDefaultCollapseState(),

  toggleCollapse: (nodeId: string) => {
    const { state } = get();
    set({ state: toggleNodeCollapse(nodeId, state) });
  },

  expand: (nodeId: string, index: GraphIndex, expandAncestors?: boolean) => {
    const { state } = get();
    set({ state: expandNode(nodeId, state, index, expandAncestors) });
  },

  collapse: (nodeId: string) => {
    const { state } = get();
    set({ state: collapseNode(nodeId, state) });
  },

  collapseDepth: (depth: number, data: GraphData) => {
    const { state } = get();
    set({ state: collapseAtDepth(depth, data, state) });
  },

  expandDepth: (depth: number, data: GraphData) => {
    const { state } = get();
    set({ state: expandAtDepth(depth, data, state) });
  },

  collapseToDepth: (depth: number, data: GraphData, index: GraphIndex) => {
    const { state } = get();
    set({ state: collapseNodesAtOrBelowDepth(depth, data, index, state) });
  },

  expandAllNodes: () => {
    set({ state: expandAll() });
  },

  collapseAllNodes: (data: GraphData) => {
    set({ state: collapseAll(data) });
  },

  toggleTraits: () => {
    const { state } = get();
    set({ state: toggleTraitCollapse(state) });
  },

  reset: () => {
    set({ state: getDefaultCollapseState() });
  },
}));
