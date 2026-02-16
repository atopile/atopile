/**
 * Selection state store using Zustand.
 */

import { create } from 'zustand';

interface SelectionState {
  selectedNodes: Set<string>;
  hoveredNode: string | null;
  focusedNode: string | null;
  lockedTooltipNode: string | null; // Node whose tooltip is locked open

  // Actions
  selectNode: (nodeId: string, additive?: boolean) => void;
  deselectNode: (nodeId: string) => void;
  clearSelection: () => void;
  selectMultiple: (nodeIds: string[]) => void;
  toggleSelection: (nodeId: string) => void;
  setHoveredNode: (nodeId: string | null) => void;
  setFocusedNode: (nodeId: string | null) => void;
  lockTooltip: (nodeId: string | null) => void;
}

export const useSelectionStore = create<SelectionState>((set, get) => ({
  selectedNodes: new Set(),
  hoveredNode: null,
  focusedNode: null,
  lockedTooltipNode: null,

  selectNode: (nodeId: string, additive?: boolean) => {
    const { selectedNodes } = get();

    if (additive) {
      const newSelection = new Set(selectedNodes);
      newSelection.add(nodeId);
      set({ selectedNodes: newSelection });
    } else {
      set({ selectedNodes: new Set([nodeId]) });
    }
  },

  deselectNode: (nodeId: string) => {
    const { selectedNodes } = get();
    const newSelection = new Set(selectedNodes);
    newSelection.delete(nodeId);
    set({ selectedNodes: newSelection });
  },

  clearSelection: () => {
    set({ selectedNodes: new Set(), focusedNode: null });
  },

  selectMultiple: (nodeIds: string[]) => {
    set({ selectedNodes: new Set(nodeIds) });
  },

  toggleSelection: (nodeId: string) => {
    const { selectedNodes } = get();
    const newSelection = new Set(selectedNodes);

    if (newSelection.has(nodeId)) {
      newSelection.delete(nodeId);
    } else {
      newSelection.add(nodeId);
    }

    set({ selectedNodes: newSelection });
  },

  setHoveredNode: (nodeId: string | null) => {
    set({ hoveredNode: nodeId });
  },

  setFocusedNode: (nodeId: string | null) => {
    set({ focusedNode: nodeId, selectedNodes: nodeId ? new Set([nodeId]) : new Set() });
  },

  lockTooltip: (nodeId: string | null) => {
    const { lockedTooltipNode } = get();
    // Toggle: if clicking on same node, unlock; otherwise lock to new node
    if (nodeId === lockedTooltipNode) {
      set({ lockedTooltipNode: null });
    } else {
      set({ lockedTooltipNode: nodeId });
    }
  },
}));
