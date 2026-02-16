/**
 * Navigation state store for tree-walking navigation.
 *
 * Instead of collapsing nodes, we navigate through the tree:
 * - Click a node to "drill down" into it (it becomes the new root)
 * - Use breadcrumbs to navigate back up
 * - Show only N levels of depth from the current root
 */

import { create } from 'zustand';

interface NavigationState {
  // Current "root" node we're viewing from (null = actual root)
  currentRootId: string | null;

  // Breadcrumb trail for navigation (ancestors of current root)
  breadcrumbs: Array<{ id: string; name: string }>;

  // How many levels deep to show from current root
  viewDepth: number;

  // Whether depth filtering is enabled
  depthEnabled: boolean;

  // Actions
  navigateTo: (nodeId: string, nodeName: string, ancestors: Array<{ id: string; name: string }>) => void;
  navigateUp: (toNodeId: string | null) => void;
  navigateToRoot: () => void;
  setViewDepth: (depth: number) => void;
  toggleDepthEnabled: () => void;
  reset: () => void;
}

export const useNavigationStore = create<NavigationState>((set, get) => ({
  currentRootId: null,
  breadcrumbs: [],
  viewDepth: 10, // Default: show 10 levels deep
  depthEnabled: true, // Depth filtering enabled by default

  navigateTo: (nodeId: string, nodeName: string, ancestors: Array<{ id: string; name: string }>) => {
    const { currentRootId, breadcrumbs } = get();

    // Build new breadcrumbs: include current root (if any) plus the new node's ancestors
    const newBreadcrumbs: Array<{ id: string; name: string }> = [];

    // Add ancestors that aren't already in breadcrumbs
    for (const ancestor of ancestors) {
      if (!breadcrumbs.some(b => b.id === ancestor.id)) {
        newBreadcrumbs.push(ancestor);
      }
    }

    // If we had a current root that's not in ancestors, add it
    if (currentRootId && !ancestors.some(a => a.id === currentRootId)) {
      const existingBreadcrumb = breadcrumbs.find(b => b.id === currentRootId);
      if (existingBreadcrumb) {
        // Insert current root at the appropriate position
        const insertIndex = newBreadcrumbs.findIndex(b =>
          ancestors.findIndex(a => a.id === b.id) > ancestors.findIndex(a => a.id === currentRootId)
        );
        if (insertIndex >= 0) {
          newBreadcrumbs.splice(insertIndex, 0, existingBreadcrumb);
        } else {
          newBreadcrumbs.push(existingBreadcrumb);
        }
      }
    }

    // Use breadcrumbs directly from ancestors (simpler approach)
    set({
      currentRootId: nodeId,
      breadcrumbs: [...ancestors, { id: nodeId, name: nodeName }],
    });
  },

  navigateUp: (toNodeId: string | null) => {
    const { breadcrumbs } = get();

    if (toNodeId === null) {
      // Go to actual root
      set({
        currentRootId: null,
        breadcrumbs: [],
      });
      return;
    }

    // Find the node in breadcrumbs and trim
    const index = breadcrumbs.findIndex(b => b.id === toNodeId);
    if (index >= 0) {
      set({
        currentRootId: toNodeId,
        breadcrumbs: breadcrumbs.slice(0, index + 1),
      });
    }
  },

  navigateToRoot: () => {
    set({
      currentRootId: null,
      breadcrumbs: [],
    });
  },

  setViewDepth: (depth: number) => {
    set({ viewDepth: Math.max(1, depth) });
  },

  toggleDepthEnabled: () => {
    set((state) => ({ depthEnabled: !state.depthEnabled }));
  },

  reset: () => {
    set({
      currentRootId: null,
      breadcrumbs: [],
      viewDepth: 10,
      depthEnabled: true,
    });
  },
}));
