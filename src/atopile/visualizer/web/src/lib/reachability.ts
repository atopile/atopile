/**
 * Reachability analysis for graph visualization.
 */

import type { GraphIndex, EdgeTypeKey } from '../types/graph';

interface ReachabilityResult {
  reachableNodes: Set<string>;
  paths: Map<string, string[]>; // nodeId -> path of edge IDs to reach it
  distances: Map<string, number>; // nodeId -> hop count
}

/**
 * Perform BFS to find all reachable nodes from a set of source nodes.
 */
export function findReachableNodes(
  sourceNodes: Set<string>,
  edgeTypes: Set<EdgeTypeKey>,
  maxHops: number,
  index: GraphIndex,
  bidirectional: boolean = true
): ReachabilityResult {
  const reachableNodes = new Set<string>(sourceNodes);
  const paths = new Map<string, string[]>();
  const distances = new Map<string, number>();

  // Initialize sources
  for (const nodeId of sourceNodes) {
    paths.set(nodeId, []);
    distances.set(nodeId, 0);
  }

  const queue: Array<{ nodeId: string; path: string[]; hops: number }> = [];
  for (const nodeId of sourceNodes) {
    queue.push({ nodeId, path: [], hops: 0 });
  }

  while (queue.length > 0) {
    const { nodeId, path, hops } = queue.shift()!;

    if (hops >= maxHops) continue;

    // Get outgoing edges of allowed types
    const outgoing = index.outgoingEdges.get(nodeId);
    if (outgoing) {
      for (const edgeType of edgeTypes) {
        const edgeIds = outgoing.get(edgeType);
        if (edgeIds) {
          for (const edgeId of edgeIds) {
            const edge = index.edgesById.get(edgeId);
            if (edge) {
              // Determine target node
              let targetId: string;
              if (edge.directional) {
                // For directional edges, only follow in the direction
                if (edge.source === nodeId) {
                  targetId = edge.target;
                } else if (bidirectional) {
                  targetId = edge.source;
                } else {
                  continue;
                }
              } else {
                // For undirected edges, go either way
                targetId = edge.source === nodeId ? edge.target : edge.source;
              }

              if (!reachableNodes.has(targetId)) {
                reachableNodes.add(targetId);
                const newPath = [...path, edgeId];
                paths.set(targetId, newPath);
                distances.set(targetId, hops + 1);
                queue.push({ nodeId: targetId, path: newPath, hops: hops + 1 });
              }
            }
          }
        }
      }
    }
  }

  return { reachableNodes, paths, distances };
}

/**
 * Find the shortest path between two nodes.
 */
export function findShortestPath(
  sourceId: string,
  targetId: string,
  edgeTypes: Set<EdgeTypeKey>,
  index: GraphIndex,
  maxHops: number = 100
): string[] | null {
  if (sourceId === targetId) {
    return [];
  }

  const visited = new Set<string>([sourceId]);
  const queue: Array<{ nodeId: string; path: string[] }> = [
    { nodeId: sourceId, path: [] },
  ];

  while (queue.length > 0) {
    const { nodeId, path } = queue.shift()!;

    if (path.length >= maxHops) continue;

    const outgoing = index.outgoingEdges.get(nodeId);
    if (outgoing) {
      for (const edgeType of edgeTypes) {
        const edgeIds = outgoing.get(edgeType);
        if (edgeIds) {
          for (const edgeId of edgeIds) {
            const edge = index.edgesById.get(edgeId);
            if (edge) {
              const nextId = edge.source === nodeId ? edge.target : edge.source;

              if (nextId === targetId) {
                return [...path, edgeId];
              }

              if (!visited.has(nextId)) {
                visited.add(nextId);
                queue.push({ nodeId: nextId, path: [...path, edgeId] });
              }
            }
          }
        }
      }
    }
  }

  return null; // No path found
}

/**
 * Get all nodes at exactly N hops from the source.
 */
export function getNodesAtDistance(
  sourceId: string,
  distance: number,
  edgeTypes: Set<EdgeTypeKey>,
  index: GraphIndex
): Set<string> {
  const result = findReachableNodes(
    new Set([sourceId]),
    edgeTypes,
    distance,
    index
  );

  const nodesAtDistance = new Set<string>();
  for (const [nodeId, dist] of result.distances) {
    if (dist === distance) {
      nodesAtDistance.add(nodeId);
    }
  }

  return nodesAtDistance;
}

/**
 * Find all nodes that can reach the target (reverse reachability).
 */
export function findNodesReachingTarget(
  targetId: string,
  edgeTypes: Set<EdgeTypeKey>,
  maxHops: number,
  index: GraphIndex
): Set<string> {
  const canReach = new Set<string>([targetId]);
  const queue: Array<{ nodeId: string; hops: number }> = [
    { nodeId: targetId, hops: 0 },
  ];

  while (queue.length > 0) {
    const { nodeId, hops } = queue.shift()!;

    if (hops >= maxHops) continue;

    // Look at incoming edges
    const incoming = index.incomingEdges.get(nodeId);
    if (incoming) {
      for (const edgeType of edgeTypes) {
        const edgeIds = incoming.get(edgeType);
        if (edgeIds) {
          for (const edgeId of edgeIds) {
            const edge = index.edgesById.get(edgeId);
            if (edge) {
              const sourceId = edge.target === nodeId ? edge.source : edge.target;
              if (!canReach.has(sourceId)) {
                canReach.add(sourceId);
                queue.push({ nodeId: sourceId, hops: hops + 1 });
              }
            }
          }
        }
      }
    }
  }

  return canReach;
}
