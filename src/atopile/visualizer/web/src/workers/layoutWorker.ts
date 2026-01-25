/**
 * Web Worker for computing graph layouts.
 *
 * This runs force-directed layout algorithms off the main thread
 * to keep the UI responsive during computation.
 */

import Graph from 'graphology';
import forceAtlas2 from 'graphology-layout-forceatlas2';

export interface LayoutWorkerInput {
  type: 'compute';
  nodes: Array<{
    id: string;
    depth: number;
    childCount: number;
    parentId: string | null;
  }>;
  edges: Array<{
    id: string;
    source: string;
    target: string;
    type: string;
  }>;
  options: {
    iterations: number;
    edgeWeightByType: Record<string, number>;
    includeEdgeTypes: string[];
  };
}

export interface LayoutWorkerOutput {
  type: 'progress' | 'complete' | 'error';
  progress?: number;
  positions?: Record<string, { x: number; y: number; z: number }>;
  bounds?: { minX: number; maxX: number; minY: number; maxY: number };
  error?: string;
}

// Handle incoming messages
self.onmessage = (event: MessageEvent<LayoutWorkerInput>) => {
  const { type, nodes, edges, options } = event.data;

  if (type !== 'compute') {
    return;
  }

  try {
    const result = computeLayout(nodes, edges, options);
    self.postMessage({
      type: 'complete',
      positions: result.positions,
      bounds: result.bounds,
    } satisfies LayoutWorkerOutput);
  } catch (error) {
    self.postMessage({
      type: 'error',
      error: error instanceof Error ? error.message : 'Unknown error',
    } satisfies LayoutWorkerOutput);
  }
};

function computeLayout(
  nodes: LayoutWorkerInput['nodes'],
  edges: LayoutWorkerInput['edges'],
  options: LayoutWorkerInput['options']
): { positions: Record<string, { x: number; y: number; z: number }>; bounds: { minX: number; maxX: number; minY: number; maxY: number } } {
  // Create graphology graph
  const graph = new Graph({ type: 'undirected', allowSelfLoops: false });

  // Build node set for validation and depth lookup
  const nodeSet = new Set(nodes.map((n) => n.id));
  const nodeDepthMap = new Map(nodes.map((n) => [n.id, n.depth]));

  // Find max depth for z-axis scaling
  let maxDepth = 0;
  for (const node of nodes) {
    if (node.depth > maxDepth) maxDepth = node.depth;
  }
  const zScale = maxDepth > 0 ? 300 / maxDepth : 0;

  // Add nodes with initial positions based on hierarchy
  for (const node of nodes) {
    // Initial position: spread by depth with some randomness
    // Use polar coordinates for x/y, depth for z
    const angle = Math.random() * Math.PI * 2;
    const radius = node.depth * 80 + Math.random() * 40;
    const x = Math.cos(angle) * radius;
    const y = Math.sin(angle) * radius;

    graph.addNode(node.id, {
      x,
      y,
      size: node.childCount > 0 ? 2 : 1,
      depth: node.depth,
    });
  }

  // Add edges with weights
  const includedTypes = new Set(options.includeEdgeTypes);

  for (const edge of edges) {
    if (!includedTypes.has(edge.type)) continue;
    if (!nodeSet.has(edge.source) || !nodeSet.has(edge.target)) continue;

    // Avoid duplicate edges in undirected graph
    if (!graph.hasEdge(edge.source, edge.target)) {
      try {
        const weight = options.edgeWeightByType[edge.type] ?? 1;
        graph.addEdge(edge.source, edge.target, { weight });
      } catch {
        // Edge might already exist
      }
    }
  }

  // Report progress
  self.postMessage({ type: 'progress', progress: 0.1 } satisfies LayoutWorkerOutput);

  // Run ForceAtlas2 layout
  if (graph.order > 0) {
    const settings = {
      gravity: 1,
      scalingRatio: 10,
      strongGravityMode: false,
      slowDown: 1,
      barnesHutOptimize: graph.order > 1000,
      barnesHutTheta: 0.5,
      adjustSizes: false,
      linLogMode: false,
    };

    // Run in batches to report progress
    const batchSize = Math.ceil(options.iterations / 10);
    for (let i = 0; i < options.iterations; i += batchSize) {
      const iterationsThisBatch = Math.min(batchSize, options.iterations - i);
      forceAtlas2.assign(graph, {
        iterations: iterationsThisBatch,
        settings,
      });

      const progress = 0.1 + 0.8 * ((i + iterationsThisBatch) / options.iterations);
      self.postMessage({ type: 'progress', progress } satisfies LayoutWorkerOutput);
    }
  }

  self.postMessage({ type: 'progress', progress: 0.95 } satisfies LayoutWorkerOutput);

  // Extract positions and compute bounds
  const positions: Record<string, { x: number; y: number; z: number }> = {};
  let minX = Infinity,
    maxX = -Infinity,
    minY = Infinity,
    maxY = -Infinity;

  graph.forEachNode((nodeId, attrs) => {
    const x = attrs.x ?? 0;
    const y = attrs.y ?? 0;
    // Use depth for z-axis (3D visualization)
    const depth = nodeDepthMap.get(nodeId) ?? 0;
    const z = depth * zScale;

    positions[nodeId] = { x, y, z };

    if (x < minX) minX = x;
    if (x > maxX) maxX = x;
    if (y < minY) minY = y;
    if (y > maxY) maxY = y;
  });

  // Handle empty graph
  if (Object.keys(positions).length === 0) {
    return {
      positions: {},
      bounds: { minX: 0, maxX: 0, minY: 0, maxY: 0 },
    };
  }

  // Normalize positions to center around origin
  const centerX = (minX + maxX) / 2;
  const centerY = (minY + maxY) / 2;
  const scale = 500 / Math.max(maxX - minX, maxY - minY, 1);

  for (const nodeId of Object.keys(positions)) {
    positions[nodeId].x = (positions[nodeId].x - centerX) * scale;
    positions[nodeId].y = (positions[nodeId].y - centerY) * scale;
  }

  // Anchor: ensure the depth-0 node is exactly at the origin.
  // (If multiple depth-0 nodes exist, anchor on the first.)
  const rootNodeId = nodes.find((n) => n.depth === 0)?.id ?? nodes[0]?.id ?? null;
  if (rootNodeId && positions[rootNodeId]) {
    const offsetX = positions[rootNodeId].x;
    const offsetY = positions[rootNodeId].y;
    const offsetZ = positions[rootNodeId].z;

    for (const nodeId of Object.keys(positions)) {
      positions[nodeId].x -= offsetX;
      positions[nodeId].y -= offsetY;
      positions[nodeId].z -= offsetZ;
    }
  }

  // Recompute bounds after normalization + anchoring
  minX = Infinity;
  maxX = -Infinity;
  minY = Infinity;
  maxY = -Infinity;
  for (const pos of Object.values(positions)) {
    if (pos.x < minX) minX = pos.x;
    if (pos.x > maxX) maxX = pos.x;
    if (pos.y < minY) minY = pos.y;
    if (pos.y > maxY) maxY = pos.y;
  }

  return {
    positions,
    bounds: {
      minX,
      maxX,
      minY,
      maxY,
    },
  };
}
