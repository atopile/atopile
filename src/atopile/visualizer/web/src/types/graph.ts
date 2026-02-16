/**
 * TypeScript types for the graph visualization.
 */

export type EdgeTypeKey =
  | 'composition'
  | 'trait'
  | 'pointer'
  | 'connection'
  | 'operand'
  | 'type'
  | 'next';

export interface EdgeTypeConfig {
  id: number;
  name: string;
  color: string;
  directional: boolean;
  description: string;
}

export interface GraphNode {
  id: string;
  uuid: number;
  typeName: string | null;
  name: string | null;
  parentId: string | null;
  depth: number;
  traits: string[];
  attributes: Record<string, unknown>;
  childCount: number;
  traitCount: number;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: EdgeTypeKey;
  name: string | null;
  directional: boolean;
}

export interface GraphMetadata {
  rootNodeId: string;
  totalNodes: number;
  totalEdges: number;
}

export interface GraphData {
  version: string;
  metadata: GraphMetadata;
  edgeTypes: Record<EdgeTypeKey, EdgeTypeConfig>;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

// Index structures for O(1) lookups
export interface GraphIndex {
  nodesById: Map<string, GraphNode>;
  nodesByType: Map<string, Set<string>>; // typeName -> nodeIds
  nodesByTrait: Map<string, Set<string>>; // traitName -> nodeIds
  edgesByType: Map<EdgeTypeKey, Set<string>>; // edgeType -> edgeIds
  edgesById: Map<string, GraphEdge>;
  childrenByParent: Map<string, Set<string>>; // hierarchy
  outgoingEdges: Map<string, Map<EdgeTypeKey, string[]>>; // node -> edgeType -> edgeIds
  incomingEdges: Map<string, Map<EdgeTypeKey, string[]>>; // node -> edgeType -> edgeIds
}

// Collapse state
export interface CollapseState {
  collapsedNodes: Set<string>; // User-collapsed nodes
  collapsedTraits: boolean; // Whether to collapse all trait nodes
}

// Filter configuration
export interface FilterConfig {
  nodeTypes: {
    included: Set<string>;
    excluded: Set<string>;
  };
  traits: {
    required: Set<string>;
    any: Set<string>;
  };
  edgeTypes: {
    visible: Set<EdgeTypeKey>;
  };
  depthRange: {
    min: number;
    max: number;
  };
  hideAnonNodes?: boolean; // Hide nodes with names starting with "anon"
  hideOrphans?: boolean; // Hide nodes whose parents are not visible
  reachability: {
    enabled: boolean;
    fromNodes: Set<string>;
    edgeTypes: Set<EdgeTypeKey>;
    maxHops: number;
  } | null;
}

// Node positions from layout
export interface NodePosition {
  x: number;
  y: number;
  z: number;
}

export interface LayoutResult {
  positions: Map<string, NodePosition>;
  bounds: {
    minX: number;
    maxX: number;
    minY: number;
    maxY: number;
  };
}

// Selection state
export interface SelectionState {
  selectedNodes: Set<string>;
  hoveredNode: string | null;
  focusedNode: string | null;
}

// View state
export interface ViewState {
  zoom: number;
  center: { x: number; y: number };
  is3D: boolean;
}
