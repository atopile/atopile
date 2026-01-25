/**
 * Filter engine for graph visualization.
 */

import type {
  GraphData,
  GraphIndex,
  GraphNode,
  GraphEdge,
  EdgeTypeKey,
  FilterConfig,
  CollapseState,
} from '../types/graph';
import { getDescendants } from './graphIndex';

/**
 * Default filter configuration.
 */
export function getDefaultFilterConfig(_data: GraphData): FilterConfig {
  void _data;
  // Default to only showing Composition, Pointer, and Connection edges
  const defaultEdgeTypes = new Set<EdgeTypeKey>([
    'composition',
    'pointer',
    'connection',
  ]);

  return {
    nodeTypes: {
      included: new Set(), // Empty means include all
      excluded: new Set(),
    },
    traits: {
      required: new Set(), // No required traits by default - let hide toggles control visibility
      any: new Set(),
    },
    edgeTypes: {
      visible: defaultEdgeTypes,
    },
    depthRange: {
      min: 0,
      max: Infinity,
    },
    hideAnonNodes: true, // Hide anonymous nodes by default
    hideOrphans: true, // Hide nodes whose parents are not visible
    reachability: null,
  };
}

/**
 * Check if a node passes the filter.
 */
export function nodePassesFilter(
  node: GraphNode,
  filter: FilterConfig,
  _index: GraphIndex
): boolean {
  void _index; // Available for future filtering by graph relationships

  // Check hide anonymous nodes filter
  if (filter.hideAnonNodes) {
    const name = node.name ?? '';
    if (name.startsWith('anon') || name.startsWith('_anon')) {
      return false;
    }
  }

  // Check node type filter
  if (filter.nodeTypes.excluded.has(node.typeName ?? '')) {
    return false;
  }
  if (
    filter.nodeTypes.included.size > 0 &&
    !filter.nodeTypes.included.has(node.typeName ?? '')
  ) {
    return false;
  }

  // Check depth range
  if (node.depth < filter.depthRange.min || node.depth > filter.depthRange.max) {
    return false;
  }

  // Check required traits (at least one must be present - OR logic)
  if (filter.traits.required.size > 0) {
    const nodeTraits = new Set(node.traits);
    let hasAny = false;
    for (const required of filter.traits.required) {
      if (nodeTraits.has(required)) {
        hasAny = true;
        break;
      }
    }
    if (!hasAny) {
      return false;
    }
  }

  // Check any traits (at least one must be present)
  if (filter.traits.any.size > 0) {
    const nodeTraits = new Set(node.traits);
    let hasAny = false;
    for (const trait of filter.traits.any) {
      if (nodeTraits.has(trait)) {
        hasAny = true;
        break;
      }
    }
    if (!hasAny) {
      return false;
    }
  }

  return true;
}

/**
 * Check if an edge passes the filter.
 */
export function edgePassesFilter(
  edge: GraphEdge,
  filter: FilterConfig,
  visibleNodes: Set<string>
): boolean {
  // Check edge type visibility
  if (!filter.edgeTypes.visible.has(edge.type)) {
    return false;
  }

  // Check that both endpoints are visible
  if (!visibleNodes.has(edge.source) || !visibleNodes.has(edge.target)) {
    return false;
  }

  return true;
}

/**
 * Compute reachable nodes using BFS.
 */
export function computeReachableNodes(
  fromNodes: Set<string>,
  edgeTypes: Set<EdgeTypeKey>,
  maxHops: number,
  index: GraphIndex
): Set<string> {
  const reachable = new Set<string>(fromNodes);
  const queue: Array<{ id: string; hops: number }> = [];

  for (const id of fromNodes) {
    queue.push({ id, hops: 0 });
  }

  while (queue.length > 0) {
    const { id, hops } = queue.shift()!;
    if (hops >= maxHops) continue;

    // Get outgoing edges of allowed types
    const outgoing = index.outgoingEdges.get(id);
    if (outgoing) {
      for (const edgeType of edgeTypes) {
        const edgeIds = outgoing.get(edgeType);
        if (edgeIds) {
          for (const edgeId of edgeIds) {
            const edge = index.edgesById.get(edgeId);
            if (edge) {
              const targetId = edge.source === id ? edge.target : edge.source;
              if (!reachable.has(targetId)) {
                reachable.add(targetId);
                queue.push({ id: targetId, hops: hops + 1 });
              }
            }
          }
        }
      }
    }
  }

  return reachable;
}

/**
 * Compute visible nodes based on filter and collapse state.
 */
export function computeVisibleNodes(
  data: GraphData,
  index: GraphIndex,
  filter: FilterConfig,
  collapse: CollapseState
): Set<string> {
  let visibleNodes = new Set<string>();
  const rootNodeId = data.metadata.rootNodeId;

  // First pass: filter by node properties
  for (const node of data.nodes) {
    if (nodePassesFilter(node, filter, index)) {
      visibleNodes.add(node.id);
    }
  }

  // Always ensure root node is visible (prevents crash when all types excluded)
  if (rootNodeId && !visibleNodes.has(rootNodeId)) {
    visibleNodes.add(rootNodeId);
  }

  // Apply reachability filter if enabled
  if (filter.reachability?.enabled && filter.reachability.fromNodes.size > 0) {
    const reachable = computeReachableNodes(
      filter.reachability.fromNodes,
      filter.reachability.edgeTypes,
      filter.reachability.maxHops,
      index
    );

    // Intersect with current visible set
    visibleNodes = new Set(
      [...visibleNodes].filter((id) => reachable.has(id))
    );
  }

  // Compute trait targets (nodes reached via trait edges)
  const traitTargets = new Set<string>();
  for (const edge of data.edges) {
    if (edge.type === 'trait') {
      traitTargets.add(edge.target);
    }
  }

  // Apply collapse state - hide trait target nodes
  if (collapse.collapsedTraits) {
    visibleNodes = new Set(
      [...visibleNodes].filter((id) => !traitTargets.has(id))
    );
  }

  // Hide descendants of collapsed nodes
  for (const collapsedId of collapse.collapsedNodes) {
    const descendants = getDescendants(collapsedId, index);
    for (const descendantId of descendants) {
      visibleNodes.delete(descendantId);
    }
  }

  // Include parents of all visible nodes (walk up the tree)
  // But respect the hideAnonNodes and collapsedTraits filters
  const parentsToAdd = new Set<string>();
  for (const nodeId of visibleNodes) {
    let currentId: string | null | undefined = nodeId;
    while (currentId) {
      const node = index.nodesById.get(currentId);
      if (node?.parentId && !visibleNodes.has(node.parentId)) {
        // Check if parent should be hidden due to filters
        const parentNode = index.nodesById.get(node.parentId);
        if (parentNode) {
          const parentName = parentNode.name ?? '';
          const isAnon = parentName.startsWith('anon') || parentName.startsWith('_anon');
          const isTraitTarget = traitTargets.has(node.parentId);
          const shouldHide = (filter.hideAnonNodes && isAnon) || (collapse.collapsedTraits && isTraitTarget);
          if (!shouldHide) {
            parentsToAdd.add(node.parentId);
          }
        }
      }
      currentId = node?.parentId;
    }
  }
  for (const parentId of parentsToAdd) {
    visibleNodes.add(parentId);
  }

  // Hide orphans - nodes whose parents are not visible
  // Iterate until no more orphans are found (cascading removal)
  if (filter.hideOrphans) {
    let changed = true;
    while (changed) {
      changed = false;
      const toRemove = new Set<string>();
      for (const nodeId of visibleNodes) {
        // Skip root node
        if (nodeId === rootNodeId) continue;

        const node = index.nodesById.get(nodeId);
        if (node?.parentId && !visibleNodes.has(node.parentId)) {
          toRemove.add(nodeId);
          changed = true;
        }
      }
      for (const nodeId of toRemove) {
        visibleNodes.delete(nodeId);
      }
    }
  }

  return visibleNodes;
}

/**
 * Compute visible edges based on filter and visible nodes.
 */
export function computeVisibleEdges(
  data: GraphData,
  filter: FilterConfig,
  visibleNodes: Set<string>
): Set<string> {
  const visibleEdges = new Set<string>();

  for (const edge of data.edges) {
    if (edgePassesFilter(edge, filter, visibleNodes)) {
      visibleEdges.add(edge.id);
    }
  }

  return visibleEdges;
}

/**
 * Navigation state for tree-walking.
 */
export interface NavigationState {
  currentRootId: string | null;
  viewDepth: number;
  depthEnabled: boolean;
}

/**
 * Compute visible nodes with navigation-based tree walking.
 * Shows nodes from currentRoot down to viewDepth levels.
 */
export function computeVisibleNodesWithNavigation(
  data: GraphData,
  index: GraphIndex,
  filter: FilterConfig,
  collapse: CollapseState,
  navigation: NavigationState
): Set<string> {
  // First get the filtered visible nodes
  let visibleNodes = computeVisibleNodes(data, index, filter, collapse);

  // Apply navigation-based depth limiting (only if depth filtering is enabled)
  const { currentRootId, viewDepth, depthEnabled } = navigation;
  const actualRootId = currentRootId ?? data.metadata.rootNodeId;

  if (depthEnabled && actualRootId) {
    const rootNode = index.nodesById.get(actualRootId);
    if (rootNode) {
      // Filter to only show nodes within viewDepth from current root
      const navigationFiltered = new Set<string>();

      // Always include the current navigation root
      navigationFiltered.add(actualRootId);

      // Include descendants up to viewDepth (respecting filters)
      const descendants = getDescendantsWithDepth(actualRootId, index, viewDepth);
      for (const descendantId of descendants) {
        if (visibleNodes.has(descendantId)) {
          navigationFiltered.add(descendantId);
        }
      }

      // Include immediate children that pass filter
      const children = index.childrenByParent.get(actualRootId);
      if (children) {
        for (const childId of children) {
          if (visibleNodes.has(childId)) {
            navigationFiltered.add(childId);
          }
        }
      }

      // Include parent chain from navigation root up to actual root
      if (currentRootId) {
        let parentId: string | null | undefined = rootNode.parentId;
        while (parentId) {
          navigationFiltered.add(parentId);
          const parentNode = index.nodesById.get(parentId);
          parentId = parentNode?.parentId;
        }
      }

      visibleNodes = navigationFiltered;
    }
  }

  // Ensure actual root is always visible
  if (data.metadata.rootNodeId && !visibleNodes.has(data.metadata.rootNodeId)) {
    // Only add if we're viewing from actual root
    if (!currentRootId) {
      visibleNodes.add(data.metadata.rootNodeId);
    }
  }

  // Ensure navigation root is always visible
  if (currentRootId && !visibleNodes.has(currentRootId)) {
    visibleNodes.add(currentRootId);
  }

  return visibleNodes;
}

/**
 * Get descendants up to a certain depth.
 */
export function getDescendantsWithDepth(
  nodeId: string,
  index: GraphIndex,
  maxDepth: number
): Set<string> {
  const descendants = new Set<string>();
  const queue: Array<{ id: string; depth: number }> = [{ id: nodeId, depth: 0 }];

  while (queue.length > 0) {
    const { id, depth } = queue.shift()!;
    if (depth >= maxDepth) continue;

    const children = index.childrenByParent.get(id);
    if (children) {
      for (const childId of children) {
        if (!descendants.has(childId)) {
          descendants.add(childId);
          queue.push({ id: childId, depth: depth + 1 });
        }
      }
    }
  }

  return descendants;
}

/**
 * Get statistics about visible graph.
 */
export function getVisibilityStats(
  data: GraphData,
  visibleNodes: Set<string>,
  visibleEdges: Set<string>
): {
  totalNodes: number;
  visibleNodes: number;
  totalEdges: number;
  visibleEdges: number;
  percentNodes: number;
  percentEdges: number;
} {
  const totalNodes = data.nodes.length;
  const totalEdges = data.edges.length;

  return {
    totalNodes,
    visibleNodes: visibleNodes.size,
    totalEdges,
    visibleEdges: visibleEdges.size,
    percentNodes: totalNodes > 0 ? (visibleNodes.size / totalNodes) * 100 : 0,
    percentEdges: totalEdges > 0 ? (visibleEdges.size / totalEdges) * 100 : 0,
  };
}
