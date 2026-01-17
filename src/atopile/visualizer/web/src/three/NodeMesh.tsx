/**
 * Instanced mesh component for rendering graph nodes.
 *
 * Uses Three.js InstancedMesh for efficient rendering of thousands of nodes
 * with a single draw call. Colors are determined by node type.
 */

import { useRef, useMemo, useEffect, useCallback } from 'react';
import { ThreeEvent } from '@react-three/fiber';
import { Html } from '@react-three/drei';
import * as THREE from 'three';
import type {
  GraphData,
  GraphIndex,
  GraphNode,
  NodePosition,
  CollapseState,
} from '../types/graph';
import { useViewStore, type ColorScheme } from '../stores/viewStore';

// Comprehensive color palette for node types
// Uses a perceptually distinct color scheme
const NODE_TYPE_COLORS: Record<string, string> = {
  // Core electronics
  Resistor: '#22c55e',       // Green
  Capacitor: '#3b82f6',      // Blue
  Inductor: '#a855f7',       // Purple
  LED: '#eab308',            // Yellow
  Diode: '#f97316',          // Orange

  // Interfaces
  Electrical: '#06b6d4',     // Cyan
  ElectricPower: '#ef4444',  // Red
  ElectricLogic: '#8b5cf6',  // Violet
  ElectricSignal: '#14b8a6', // Teal

  // Communication
  I2C: '#ec4899',            // Pink
  SPI: '#f43f5e',            // Rose
  UART: '#84cc16',           // Lime
  USB: '#6366f1',            // Indigo

  // Parameters and expressions
  Pointer: '#64748b',        // Slate
  PointerSet: '#475569',     // Darker slate
  Numeric: '#0ea5e9',        // Sky
  String: '#10b981',         // Emerald

  // Traits (usually prefixed with lowercase)
  can_bridge: '#f59e0b',     // Amber
  can_be_operand: '#78716c', // Stone
  is_interface: '#a3e635',   // Lime bright
  is_module: '#38bdf8',      // Sky bright
  is_literal: '#c084fc',     // Purple bright
  is_parameter: '#2dd4bf',   // Teal bright
  is_parameter_operatable: '#34d399', // Emerald bright

  // Fallback
  default: '#9ca3af',        // Gray
};

// Special state colors
const SELECTED_COLOR = '#fbbf24';  // Amber-400
const HOVERED_COLOR = '#fef3c7';   // Amber-100
const ROOT_COLOR = '#f472b6';      // Pink-400

// Depth-based color palette (gradient from shallow to deep)
const DEPTH_COLORS = [
  '#ef4444', // Red (depth 0)
  '#f97316', // Orange
  '#eab308', // Yellow
  '#22c55e', // Green
  '#06b6d4', // Cyan
  '#3b82f6', // Blue
  '#8b5cf6', // Violet
  '#ec4899', // Pink
  '#64748b', // Slate (deeper)
];

// Trait-based colors (distinct colors for common traits)
const TRAIT_PRIORITY_COLORS: Record<string, string> = {
  is_module: '#3b82f6',           // Blue
  is_interface: '#22c55e',        // Green
  can_bridge: '#f97316',          // Orange
  is_parameter: '#8b5cf6',        // Violet
  is_literal: '#ec4899',          // Pink
  is_parameter_operatable: '#06b6d4', // Cyan
  can_be_operand: '#64748b',      // Slate
};

// Parent-based coloring: hash parent ID to color
function hashStringToColor(str: string): string {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
    hash = hash & hash;
  }
  const hue = Math.abs(hash) % 360;
  return `hsl(${hue}, 70%, 55%)`;
}

/**
 * Get color for a node based on its type and traits.
 */
function getNodeColorByType(
  typeName: string | null,
  traits: string[],
  isRoot: boolean
): string {
  if (isRoot) {
    return ROOT_COLOR;
  }

  // Try exact type match first
  if (typeName && NODE_TYPE_COLORS[typeName]) {
    return NODE_TYPE_COLORS[typeName];
  }

  // Try partial type match (e.g., "Resistor" matches "ResistorVoltageDivider")
  if (typeName) {
    for (const [key, color] of Object.entries(NODE_TYPE_COLORS)) {
      if (typeName.includes(key) || key.includes(typeName)) {
        return color;
      }
    }
  }

  // Try trait-based coloring
  for (const trait of traits) {
    if (NODE_TYPE_COLORS[trait]) {
      return NODE_TYPE_COLORS[trait];
    }
  }

  return NODE_TYPE_COLORS.default;
}

/**
 * Get color based on depth.
 */
function getNodeColorByDepth(depth: number, maxDepth: number): string {
  const normalizedDepth = maxDepth > 0 ? depth / maxDepth : 0;
  const colorIndex = Math.min(
    Math.floor(normalizedDepth * DEPTH_COLORS.length),
    DEPTH_COLORS.length - 1
  );
  return DEPTH_COLORS[colorIndex];
}

/**
 * Get color based on traits (uses most important trait).
 */
function getNodeColorByTrait(traits: string[]): string {
  // Check traits in priority order
  for (const [trait, color] of Object.entries(TRAIT_PRIORITY_COLORS)) {
    if (traits.includes(trait)) {
      return color;
    }
  }
  return NODE_TYPE_COLORS.default;
}

/**
 * Get color based on parent ID.
 */
function getNodeColorByParent(parentId: string | null): string {
  if (!parentId) return ROOT_COLOR;
  return hashStringToColor(parentId);
}

/**
 * Get color for a node based on selected color scheme.
 */
function getNodeColor(
  node: GraphNode,
  colorScheme: ColorScheme,
  isRoot: boolean,
  maxDepth: number
): string {
  if (isRoot) {
    return ROOT_COLOR;
  }

  switch (colorScheme) {
    case 'type':
      return getNodeColorByType(node.typeName, node.traits, isRoot);
    case 'depth':
      return getNodeColorByDepth(node.depth, maxDepth);
    case 'trait':
      return getNodeColorByTrait(node.traits);
    case 'parent':
      return getNodeColorByParent(node.parentId);
    default:
      return getNodeColorByType(node.typeName, node.traits, isRoot);
  }
}

/**
 * Calculate node size based on its properties.
 */
function getNodeSize(
  childCount: number,
  depth: number,
  isRoot: boolean
): number {
  if (isRoot) return 6;
  if (childCount > 10) return 4;
  if (childCount > 0) return 3;
  // Slightly larger nodes at shallower depths for visual hierarchy
  return depth <= 2 ? 2.5 : 2;
}

interface NodeMeshProps {
  data: GraphData;
  index: GraphIndex;
  positions: Map<string, NodePosition>;
  visibleNodes: Set<string>;
  selectedNodes: Set<string>;
  hoveredNode: string | null;
  collapseState: CollapseState;
  onSelect: (nodeId: string, additive?: boolean) => void;
  onHover: (nodeId: string | null) => void;
  onDoubleClick?: (nodeId: string) => void;
}

export function NodeMesh({
  data,
  index: _index,
  positions,
  visibleNodes,
  selectedNodes,
  hoveredNode,
  collapseState: _collapseState,
  onSelect,
  onHover,
  onDoubleClick,
}: NodeMeshProps) {
  void _index;
  void _collapseState;

  const meshRef = useRef<THREE.InstancedMesh>(null);
  const { showLabels, zoom, colorScheme } = useViewStore();
  const lastClickTime = useRef<number>(0);
  const lastClickedNode = useRef<string | null>(null);

  // Calculate max depth for depth-based coloring
  const maxDepth = useMemo(() => {
    return Math.max(...data.nodes.map((n) => n.depth), 0);
  }, [data.nodes]);

  // Build arrays of visible nodes with their indices
  const visibleNodeArray = useMemo(() => {
    return data.nodes.filter((node) => visibleNodes.has(node.id));
  }, [data.nodes, visibleNodes]);

  // Map from instance index to node ID
  const instanceToNodeId = useMemo(() => {
    return visibleNodeArray.map((node) => node.id);
  }, [visibleNodeArray]);

  // Determine root node
  const rootNodeId = data.metadata.rootNodeId;

  // Create geometry - slightly larger for better visibility
  const geometry = useMemo(() => new THREE.SphereGeometry(1, 24, 24), []);

  // Stable max instance count (use total nodes to avoid recreating mesh)
  const maxInstanceCount = useMemo(() => Math.max(data.nodes.length, 1), [data.nodes.length]);

  // Create material - note: vertexColors is for per-vertex colors, not instance colors
  // For InstancedMesh, we need to NOT use vertexColors and instead use instanceColor
  const material = useMemo(() => {
    const mat = new THREE.MeshStandardMaterial({
      color: 0xffffff, // Base white, tinted by instanceColor
      roughness: 0.4,
      metalness: 0.1,
    });
    return mat;
  }, []);

  // Update instance matrices and colors
  useEffect(() => {
    if (!meshRef.current) return;
    if (visibleNodeArray.length === 0) return;

    const mesh = meshRef.current;
    const tempMatrix = new THREE.Matrix4();
    const tempColor = new THREE.Color();

    // Ensure instance count matches
    mesh.count = visibleNodeArray.length;

    for (let i = 0; i < visibleNodeArray.length; i++) {
      const node = visibleNodeArray[i];
      const pos = positions.get(node.id);

      if (pos) {
        // Calculate size based on node properties
        const isRoot = node.id === rootNodeId;
        const baseSize = getNodeSize(node.childCount, node.depth, isRoot);

        // Apply hover/selection size boost
        let size = baseSize;
        if (selectedNodes.has(node.id)) {
          size *= 1.3;
        } else if (hoveredNode === node.id) {
          size *= 1.2;
        }

        // Set transform matrix
        tempMatrix.identity();
        tempMatrix.setPosition(pos.x, pos.y, pos.z);
        const scaleMatrix = new THREE.Matrix4().makeScale(size, size, size);
        tempMatrix.multiply(scaleMatrix);
        mesh.setMatrixAt(i, tempMatrix);

        // Determine color
        let color: string;
        if (selectedNodes.has(node.id)) {
          color = SELECTED_COLOR;
        } else if (hoveredNode === node.id) {
          color = HOVERED_COLOR;
        } else {
          color = getNodeColor(node, colorScheme, isRoot, maxDepth);
        }

        tempColor.set(color);
        mesh.setColorAt(i, tempColor);
      }
    }

    mesh.instanceMatrix.needsUpdate = true;
    if (mesh.instanceColor) {
      mesh.instanceColor.needsUpdate = true;
    }

    // Update bounding sphere for proper raycasting
    mesh.computeBoundingSphere();
  }, [visibleNodeArray, positions, selectedNodes, hoveredNode, rootNodeId, colorScheme, maxDepth]);

  // Handle pointer events
  const handlePointerOver = useCallback(
    (event: ThreeEvent<PointerEvent>) => {
      event.stopPropagation();
      const instanceId = event.instanceId;
      if (instanceId !== undefined && instanceId < instanceToNodeId.length) {
        onHover(instanceToNodeId[instanceId]);
        document.body.style.cursor = 'pointer';
      }
    },
    [instanceToNodeId, onHover]
  );

  const handlePointerOut = useCallback(() => {
    onHover(null);
    document.body.style.cursor = 'default';
  }, [onHover]);

  const handleClick = useCallback(
    (event: ThreeEvent<MouseEvent>) => {
      event.stopPropagation();
      const instanceId = event.instanceId;
      if (instanceId !== undefined && instanceId < instanceToNodeId.length) {
        const nodeId = instanceToNodeId[instanceId];
        const now = Date.now();

        // Check for double-click (400ms window)
        if (
          lastClickedNode.current === nodeId &&
          now - lastClickTime.current < 400
        ) {
          // Double-click - navigate into node
          onDoubleClick?.(nodeId);
        } else {
          // Single click - select node
          onSelect(nodeId, event.shiftKey);
        }

        lastClickTime.current = now;
        lastClickedNode.current = nodeId;
      }
    },
    [instanceToNodeId, onSelect, onDoubleClick]
  );

  if (visibleNodeArray.length === 0) {
    return null;
  }

  // Determine which nodes should have labels
  const labeledNodes = useMemo(() => {
    if (!showLabels) return [];

    const labeled: Array<{ node: GraphNode; color: string }> = [];

    for (const node of visibleNodeArray) {
      const isSelected = selectedNodes.has(node.id);
      const isHovered = hoveredNode === node.id;
      const isRoot = node.id === rootNodeId;
      const isImportant = node.childCount > 5 || node.depth === 0;

      const shouldShowLabel =
        isSelected ||
        isHovered ||
        (zoom > 0.5 && (isRoot || isImportant)) ||
        (zoom > 1.5 && node.childCount > 0);

      if (shouldShowLabel) {
        const color = getNodeColor(node, colorScheme, isRoot, maxDepth);
        labeled.push({ node, color });
      }
    }

    return labeled;
  }, [visibleNodeArray, selectedNodes, hoveredNode, rootNodeId, showLabels, zoom, colorScheme, maxDepth]);

  return (
    <group>
      <instancedMesh
        ref={meshRef}
        args={[geometry, material, maxInstanceCount]}
        onPointerOver={handlePointerOver}
        onPointerOut={handlePointerOut}
        onClick={handleClick}
        frustumCulled={false}
      />

      {/* Labels - integrated with nodes */}
      {labeledNodes.map(({ node, color }) => {
        const pos = positions.get(node.id);
        if (!pos) return null;

        const isSelected = selectedNodes.has(node.id);
        const isHovered = hoveredNode === node.id;
        const isRoot = node.id === rootNodeId;

        // Calculate label offset - closer to node
        const nodeSize = getNodeSize(node.childCount, node.depth, isRoot);
        const labelOffset = nodeSize + 2;

        return (
          <Html
            key={node.id}
            position={[pos.x, pos.y + labelOffset, pos.z]}
            center
            style={{
              pointerEvents: 'none',
              userSelect: 'none',
            }}
            distanceFactor={100}
            occlude={false}
            zIndexRange={[0, 1000]}
          >
            <div className="flex flex-col items-center">
              {/* Connector line */}
              <div
                className="w-0.5 h-1"
                style={{ backgroundColor: isSelected ? SELECTED_COLOR : isHovered ? HOVERED_COLOR : color }}
              />
              {/* Label */}
              <div
                className={`px-2 py-1 rounded text-xs whitespace-nowrap max-w-[180px] truncate font-medium shadow-md ${
                  isSelected
                    ? 'text-black'
                    : isHovered
                    ? 'text-black'
                    : 'text-white'
                }`}
                style={{
                  backgroundColor: isSelected ? SELECTED_COLOR : isHovered ? HOVERED_COLOR : color,
                }}
              >
                {node.name ?? node.typeName ?? 'node'}
              </div>
            </div>
          </Html>
        );
      })}
    </group>
  );
}
