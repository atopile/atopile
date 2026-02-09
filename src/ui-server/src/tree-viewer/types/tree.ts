/** Power tree JSON schema (v1.0 - hierarchical with converters) */
export interface PowerTreeData {
  version: string;
  nodes: PowerTreeNode[];
  edges: PowerTreeEdge[];
}

export interface PowerTreeNode {
  id: string;
  type: 'source' | 'converter' | 'sink';
  name: string;
  voltage?: string;
  voltage_in?: string;
  voltage_out?: string;
  max_current?: string;
  parent_module?: string | null;
}

export interface PowerTreeEdge {
  from: string;
  to: string;
}

/** I2C tree JSON schema */
export interface I2CTreeData {
  version: string;
  buses: I2CBus[];
}

export interface I2CBus {
  id: string;
  controllers: I2CController[];
  targets: I2CTarget[];
  frequency: string | null;
}

export interface I2CController {
  id: string;
  name: string;
  parent_module: string | null;
}

export interface I2CTarget {
  id: string;
  name: string;
  parent_module: string | null;
  address: string | null;
  address_resolved: boolean;
}

/** Unified tree node for layout/rendering */
export type TreeNodeType = 'source' | 'sink' | 'converter' | 'controller' | 'target';

export interface TreeNode {
  id: string;
  type: TreeNodeType;
  label: string;
  sublabel?: string;
  meta?: Record<string, string>;
  resolved?: boolean;
  /** Group ID for nodes that should be visually grouped (e.g. same parent module). */
  group?: string;
  /** Group display label (e.g. "mcu"). */
  groupLabel?: string;
}

export interface TreeEdge {
  id: string;
  source: string;
  target: string;
  label?: string;
  /** Current in amps flowing through this edge (for power tree). */
  currentAmps?: number;
}

export interface TreeGraphData {
  nodes: TreeNode[];
  edges: TreeEdge[];
}

export type ViewerMode = 'power' | 'i2c';
