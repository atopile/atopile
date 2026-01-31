/**
 * Layout engine for graph visualization.
 *
 * Uses graphology with ForceAtlas2 for force-directed layout.
 */

import Graph from 'graphology';
import forceAtlas2 from 'graphology-layout-forceatlas2';
import type {
  GraphData,
  GraphIndex,
  LayoutResult,
  NodePosition,
  EdgeTypeKey,
} from '../types/graph';

interface LayoutOptions {
  iterations: number;
  settings?: {
    gravity?: number;
    scalingRatio?: number;
    strongGravityMode?: boolean;
    slowDown?: number;
    barnesHutOptimize?: boolean;
    barnesHutTheta?: number;
    adjustSizes?: boolean;
    linLogMode?: boolean;
  };
  visibleNodes?: Set<string>;
  visibleEdges?: Set<string>;
  edgeTypes?: Set<EdgeTypeKey>;
}

const DEFAULT_OPTIONS: LayoutOptions = {
  iterations: 100,
  settings: {
    gravity: 1,
    scalingRatio: 10,
    strongGravityMode: false,
    slowDown: 1,
    barnesHutOptimize: true,
    barnesHutTheta: 0.5,
    adjustSizes: false,
    linLogMode: false,
  },
};

/**
 * Compute layout for the graph using ForceAtlas2.
 */
export function computeLayout(
  data: GraphData,
  _index: GraphIndex,
  options: Partial<LayoutOptions> = {}
): LayoutResult {
  void _index; // Available for future layout algorithms that use graph structure
  const opts = { ...DEFAULT_OPTIONS, ...options };

  // Create a graphology graph
  const graph = new Graph({ type: 'undirected', allowSelfLoops: false });

  // Determine which nodes and edges to include
  const nodesToInclude = opts.visibleNodes ?? new Set(data.nodes.map((n) => n.id));
  const edgesToInclude = opts.visibleEdges ?? new Set(data.edges.map((e) => e.id));
  const edgeTypesToInclude = opts.edgeTypes ?? new Set(['composition', 'connection'] as EdgeTypeKey[]);

  // Add nodes with initial positions based on hierarchy
  for (const node of data.nodes) {
    if (!nodesToInclude.has(node.id)) continue;

    // Initial position based on depth and some randomness
    const angle = Math.random() * Math.PI * 2;
    const radius = node.depth * 50 + Math.random() * 20;
    const x = Math.cos(angle) * radius;
    const y = Math.sin(angle) * radius;

    graph.addNode(node.id, {
      x,
      y,
      // Larger nodes for root/parent nodes
      size: Math.max(1, 10 - node.depth),
    });
  }

  // Add edges
  for (const edge of data.edges) {
    if (!edgesToInclude.has(edge.id)) continue;
    if (!edgeTypesToInclude.has(edge.type)) continue;

    // Only add edge if both nodes are in the graph
    if (!graph.hasNode(edge.source) || !graph.hasNode(edge.target)) continue;

    // Avoid duplicate edges
    if (!graph.hasEdge(edge.source, edge.target)) {
      try {
        graph.addEdge(edge.source, edge.target, {
          weight: edge.type === 'composition' ? 2 : 1, // Stronger weight for composition
        });
      } catch {
        // Edge might already exist in undirected graph
      }
    }
  }

  // Run ForceAtlas2 layout
  if (graph.order > 0) {
    forceAtlas2.assign(graph, {
      iterations: opts.iterations,
      settings: opts.settings,
    });
  }

  // Extract positions
  const positions = new Map<string, NodePosition>();
  let minX = Infinity,
    maxX = -Infinity,
    minY = Infinity,
    maxY = -Infinity;

  graph.forEachNode((nodeId, attrs) => {
    const x = attrs.x ?? 0;
    const y = attrs.y ?? 0;
    const z = 0; // 2D layout

    positions.set(nodeId, { x, y, z });

    if (x < minX) minX = x;
    if (x > maxX) maxX = x;
    if (y < minY) minY = y;
    if (y > maxY) maxY = y;
  });

  // Handle empty graph
  if (positions.size === 0) {
    return {
      positions,
      bounds: { minX: 0, maxX: 0, minY: 0, maxY: 0 },
    };
  }

  return {
    positions,
    bounds: { minX, maxX, minY, maxY },
  };
}

/**
 * Compute a hierarchical layout based on composition edges.
 */
export function computeHierarchicalLayout(
  data: GraphData,
  _index: GraphIndex,
  visibleNodes?: Set<string>
): LayoutResult {
  void _index; // Available for future hierarchical layout improvements
  const positions = new Map<string, NodePosition>();
  const nodesToInclude = visibleNodes ?? new Set(data.nodes.map((n) => n.id));

  // Group nodes by depth
  const nodesByDepth = new Map<number, string[]>();
  for (const node of data.nodes) {
    if (!nodesToInclude.has(node.id)) continue;

    if (!nodesByDepth.has(node.depth)) {
      nodesByDepth.set(node.depth, []);
    }
    nodesByDepth.get(node.depth)!.push(node.id);
  }

  // Layout each depth level
  const levelHeight = 100;
  const nodeSpacing = 50;

  let minX = Infinity,
    maxX = -Infinity,
    minY = Infinity,
    maxY = -Infinity;

  const depths = Array.from(nodesByDepth.keys()).sort((a, b) => a - b);

  for (const depth of depths) {
    const nodes = nodesByDepth.get(depth)!;
    const y = depth * levelHeight;

    // Center nodes at this level
    const totalWidth = (nodes.length - 1) * nodeSpacing;
    const startX = -totalWidth / 2;

    for (let i = 0; i < nodes.length; i++) {
      const x = startX + i * nodeSpacing;
      positions.set(nodes[i], { x, y, z: 0 });

      if (x < minX) minX = x;
      if (x > maxX) maxX = x;
      if (y < minY) minY = y;
      if (y > maxY) maxY = y;
    }
  }

  if (positions.size === 0) {
    return {
      positions,
      bounds: { minX: 0, maxX: 0, minY: 0, maxY: 0 },
    };
  }

  return {
    positions,
    bounds: { minX, maxX, minY, maxY },
  };
}

/**
 * Normalize positions to a given range.
 */
export function normalizePositions(
  result: LayoutResult,
  targetSize: number = 1000
): LayoutResult {
  const { positions, bounds } = result;

  const width = bounds.maxX - bounds.minX || 1;
  const height = bounds.maxY - bounds.minY || 1;
  const scale = targetSize / Math.max(width, height);

  const centerX = (bounds.minX + bounds.maxX) / 2;
  const centerY = (bounds.minY + bounds.maxY) / 2;

  const normalizedPositions = new Map<string, NodePosition>();

  for (const [nodeId, pos] of positions) {
    normalizedPositions.set(nodeId, {
      x: (pos.x - centerX) * scale,
      y: (pos.y - centerY) * scale,
      z: pos.z,
    });
  }

  return {
    positions: normalizedPositions,
    bounds: {
      minX: -targetSize / 2,
      maxX: targetSize / 2,
      minY: -targetSize / 2,
      maxY: targetSize / 2,
    },
  };
}

/**
 * Create positions for a subset of nodes by interpolating from existing positions.
 */
export function interpolatePositions(
  existingPositions: Map<string, NodePosition>,
  newNodes: Set<string>,
  index: GraphIndex
): Map<string, NodePosition> {
  const result = new Map<string, NodePosition>(existingPositions);

  for (const nodeId of newNodes) {
    if (result.has(nodeId)) continue;

    // Try to get position from parent
    const node = index.nodesById.get(nodeId);
    if (node?.parentId && result.has(node.parentId)) {
      const parentPos = result.get(node.parentId)!;
      // Offset slightly from parent
      result.set(nodeId, {
        x: parentPos.x + (Math.random() - 0.5) * 20,
        y: parentPos.y + (Math.random() - 0.5) * 20,
        z: parentPos.z,
      });
    } else {
      // Random position
      result.set(nodeId, {
        x: (Math.random() - 0.5) * 500,
        y: (Math.random() - 0.5) * 500,
        z: 0,
      });
    }
  }

  return result;
}
