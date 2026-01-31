/**
 * Collapse engine for graph visualization.
 */

import type {
  GraphData,
  GraphIndex,
  CollapseState,
} from '../types/graph';
import { getDescendants } from './graphIndex';

/**
 * Get default collapse state.
 */
export function getDefaultCollapseState(): CollapseState {
  return {
    collapsedNodes: new Set(),
    collapsedTraits: true, // Hide trait nodes by default
  };
}

/**
 * Toggle collapse state for a node.
 */
export function toggleNodeCollapse(
  nodeId: string,
  state: CollapseState
): CollapseState {
  const newCollapsed = new Set(state.collapsedNodes);

  if (newCollapsed.has(nodeId)) {
    newCollapsed.delete(nodeId);
  } else {
    newCollapsed.add(nodeId);
  }

  return {
    ...state,
    collapsedNodes: newCollapsed,
  };
}

/**
 * Expand a node (and optionally all its ancestors).
 */
export function expandNode(
  nodeId: string,
  state: CollapseState,
  index: GraphIndex,
  expandAncestors: boolean = false
): CollapseState {
  const newCollapsed = new Set(state.collapsedNodes);

  // Remove this node from collapsed
  newCollapsed.delete(nodeId);

  // If expanding ancestors, remove all ancestors too
  if (expandAncestors) {
    let currentId: string | null | undefined = nodeId;
    while (currentId) {
      newCollapsed.delete(currentId);
      const node = index.nodesById.get(currentId);
      currentId = node?.parentId;
    }
  }

  return {
    ...state,
    collapsedNodes: newCollapsed,
  };
}

/**
 * Collapse a node and optionally all its siblings.
 */
export function collapseNode(
  nodeId: string,
  state: CollapseState
): CollapseState {
  const newCollapsed = new Set(state.collapsedNodes);
  newCollapsed.add(nodeId);

  return {
    ...state,
    collapsedNodes: newCollapsed,
  };
}

/**
 * Collapse all nodes at a specific depth.
 */
export function collapseAtDepth(
  depth: number,
  data: GraphData,
  state: CollapseState
): CollapseState {
  const newCollapsed = new Set(state.collapsedNodes);

  for (const node of data.nodes) {
    if (node.depth === depth && node.childCount > 0) {
      newCollapsed.add(node.id);
    }
  }

  return {
    ...state,
    collapsedNodes: newCollapsed,
  };
}

/**
 * Expand all nodes at a specific depth.
 */
export function expandAtDepth(
  depth: number,
  data: GraphData,
  state: CollapseState
): CollapseState {
  const newCollapsed = new Set(state.collapsedNodes);

  for (const node of data.nodes) {
    if (node.depth === depth) {
      newCollapsed.delete(node.id);
    }
  }

  return {
    ...state,
    collapsedNodes: newCollapsed,
  };
}

/**
 * Expand all nodes.
 */
export function expandAll(): CollapseState {
  return {
    collapsedNodes: new Set(),
    collapsedTraits: false,
  };
}

/**
 * Collapse all nodes with children.
 */
export function collapseAll(data: GraphData): CollapseState {
  const collapsed = new Set<string>();

  for (const node of data.nodes) {
    if (node.childCount > 0) {
      collapsed.add(node.id);
    }
  }

  return {
    collapsedNodes: collapsed,
    collapsedTraits: true,
  };
}

/**
 * Toggle trait collapse.
 */
export function toggleTraitCollapse(state: CollapseState): CollapseState {
  return {
    ...state,
    collapsedTraits: !state.collapsedTraits,
  };
}

/**
 * Get the count of hidden descendants for a collapsed node.
 */
export function getHiddenDescendantCount(
  nodeId: string,
  index: GraphIndex
): number {
  return getDescendants(nodeId, index).size;
}

/**
 * Check if a node is visible (not hidden by a collapsed ancestor).
 */
export function isNodeVisible(
  nodeId: string,
  state: CollapseState,
  index: GraphIndex
): boolean {
  // Check if any ancestor is collapsed
  let currentId: string | null | undefined = nodeId;

  while (currentId) {
    const node = index.nodesById.get(currentId);
    if (!node) break;

    // Check if parent is collapsed
    if (node.parentId && state.collapsedNodes.has(node.parentId)) {
      return false;
    }

    currentId = node.parentId;
  }

  return true;
}

/**
 * Get all collapsed ancestor IDs for a node.
 */
export function getCollapsedAncestors(
  nodeId: string,
  state: CollapseState,
  index: GraphIndex
): string[] {
  const collapsedAncestors: string[] = [];
  let currentId: string | null | undefined = nodeId;

  while (currentId) {
    const node = index.nodesById.get(currentId);
    if (!node) break;

    if (node.parentId && state.collapsedNodes.has(node.parentId)) {
      collapsedAncestors.push(node.parentId);
    }

    currentId = node.parentId;
  }

  return collapsedAncestors;
}

/**
 * Collapse all nodes at or below a specific depth that have children.
 * This makes all nodes at depth N visible, but collapses their children.
 */
export function collapseNodesAtOrBelowDepth(
  depth: number,
  data: GraphData,
  _index: GraphIndex,
  _state: CollapseState
): CollapseState {
  void _index;
  void _state;

  const newCollapsed = new Set<string>();

  // Collapse all nodes at the target depth that have children
  for (const node of data.nodes) {
    if (node.depth >= depth && node.childCount > 0) {
      newCollapsed.add(node.id);
    }
  }

  return {
    collapsedNodes: newCollapsed,
    collapsedTraits: false,
  };
}
