/**
 * Graph indexing for O(1) lookups.
 */

import type {
  GraphData,
  GraphIndex,
  GraphNode,
  GraphEdge,
  EdgeTypeKey,
} from '../types/graph';

/**
 * Build all indices for a graph.
 */
export function buildGraphIndex(data: GraphData): GraphIndex {
  const nodesById = new Map<string, GraphNode>();
  const nodesByType = new Map<string, Set<string>>();
  const nodesByTrait = new Map<string, Set<string>>();
  const edgesByType = new Map<EdgeTypeKey, Set<string>>();
  const edgesById = new Map<string, GraphEdge>();
  const childrenByParent = new Map<string, Set<string>>();
  const outgoingEdges = new Map<string, Map<EdgeTypeKey, string[]>>();
  const incomingEdges = new Map<string, Map<EdgeTypeKey, string[]>>();

  // Index nodes
  for (const node of data.nodes) {
    nodesById.set(node.id, node);

    // Index by type
    if (node.typeName) {
      if (!nodesByType.has(node.typeName)) {
        nodesByType.set(node.typeName, new Set());
      }
      nodesByType.get(node.typeName)!.add(node.id);
    }

    // Index by traits
    for (const trait of node.traits) {
      if (!nodesByTrait.has(trait)) {
        nodesByTrait.set(trait, new Set());
      }
      nodesByTrait.get(trait)!.add(node.id);
    }

    // Index parent-child relationships
    if (node.parentId) {
      if (!childrenByParent.has(node.parentId)) {
        childrenByParent.set(node.parentId, new Set());
      }
      childrenByParent.get(node.parentId)!.add(node.id);
    }

    // Initialize edge maps for this node
    outgoingEdges.set(node.id, new Map());
    incomingEdges.set(node.id, new Map());
  }

  // Index edges
  for (const edge of data.edges) {
    edgesById.set(edge.id, edge);

    // Index by type
    if (!edgesByType.has(edge.type)) {
      edgesByType.set(edge.type, new Set());
    }
    edgesByType.get(edge.type)!.add(edge.id);

    // Index outgoing edges
    const sourceOutgoing = outgoingEdges.get(edge.source);
    if (sourceOutgoing) {
      if (!sourceOutgoing.has(edge.type)) {
        sourceOutgoing.set(edge.type, []);
      }
      sourceOutgoing.get(edge.type)!.push(edge.id);
    }

    // Index incoming edges
    const targetIncoming = incomingEdges.get(edge.target);
    if (targetIncoming) {
      if (!targetIncoming.has(edge.type)) {
        targetIncoming.set(edge.type, []);
      }
      targetIncoming.get(edge.type)!.push(edge.id);
    }

    // For undirected edges, also add reverse
    if (!edge.directional) {
      const targetOutgoing = outgoingEdges.get(edge.target);
      if (targetOutgoing) {
        if (!targetOutgoing.has(edge.type)) {
          targetOutgoing.set(edge.type, []);
        }
        targetOutgoing.get(edge.type)!.push(edge.id);
      }

      const sourceIncoming = incomingEdges.get(edge.source);
      if (sourceIncoming) {
        if (!sourceIncoming.has(edge.type)) {
          sourceIncoming.set(edge.type, []);
        }
        sourceIncoming.get(edge.type)!.push(edge.id);
      }
    }
  }

  return {
    nodesById,
    nodesByType,
    nodesByTrait,
    edgesByType,
    edgesById,
    childrenByParent,
    outgoingEdges,
    incomingEdges,
  };
}

/**
 * Get all unique node type names.
 */
export function getNodeTypes(index: GraphIndex): string[] {
  return Array.from(index.nodesByType.keys()).sort();
}

/**
 * Get all unique trait names.
 */
export function getTraitNames(index: GraphIndex): string[] {
  return Array.from(index.nodesByTrait.keys()).sort();
}

/**
 * Get descendants of a node via composition edges.
 */
export function getDescendants(
  nodeId: string,
  index: GraphIndex,
  maxDepth: number = Infinity
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
 * Get ancestors of a node via composition edges.
 */
export function getAncestors(nodeId: string, index: GraphIndex): Set<string> {
  const ancestors = new Set<string>();
  let currentId: string | null | undefined = nodeId;

  while (currentId) {
    const node = index.nodesById.get(currentId);
    if (node?.parentId && !ancestors.has(node.parentId)) {
      ancestors.add(node.parentId);
      currentId = node.parentId;
    } else {
      break;
    }
  }

  return ancestors;
}

/**
 * Get depth statistics from the graph.
 */
export function getDepthStats(data: GraphData): { min: number; max: number } {
  let min = Infinity;
  let max = 0;

  for (const node of data.nodes) {
    if (node.depth < min) min = node.depth;
    if (node.depth > max) max = node.depth;
  }

  return { min: min === Infinity ? 0 : min, max };
}
