/**
 * Line component for rendering graph edges.
 */

import { useMemo } from 'react';
import * as THREE from 'three';
import type { GraphData, GraphIndex, NodePosition, EdgeTypeKey } from '../types/graph';

// Colors for different edge types
const EDGE_COLORS: Record<EdgeTypeKey, string> = {
  composition: '#4CAF50',
  trait: '#9C27B0',
  pointer: '#FF9800',
  connection: '#2196F3',
  operand: '#F44336',
  type: '#607D8B',
  next: '#795548',
};

const SELECTED_EDGE_COLOR = '#FFD700';

interface EdgeLinesProps {
  data: GraphData;
  index: GraphIndex; // Available for future use with edge routing
  positions: Map<string, NodePosition>;
  visibleEdges: Set<string>;
  selectedNodes: Set<string>;
}

export function EdgeLines({
  data,
  index: _index,
  positions,
  visibleEdges,
  selectedNodes,
}: EdgeLinesProps) {
  void _index; // Available for edge routing algorithms
  // Group edges by type for efficient rendering
  const edgesByType = useMemo(() => {
    const groups = new Map<EdgeTypeKey, Array<{ edge: typeof data.edges[0]; selected: boolean }>>();

    for (const edge of data.edges) {
      if (!visibleEdges.has(edge.id)) continue;

      const sourcePos = positions.get(edge.source);
      const targetPos = positions.get(edge.target);
      if (!sourcePos || !targetPos) continue;

      const selected =
        selectedNodes.has(edge.source) || selectedNodes.has(edge.target);

      if (!groups.has(edge.type)) {
        groups.set(edge.type, []);
      }
      groups.get(edge.type)!.push({ edge, selected });
    }

    return groups;
  }, [data.edges, visibleEdges, positions, selectedNodes]);

  return (
    <group>
      {Array.from(edgesByType.entries()).map(([edgeType, edges]) => (
        <EdgeTypeGroup
          key={edgeType}
          edgeType={edgeType}
          edges={edges}
          positions={positions}
        />
      ))}
    </group>
  );
}

interface EdgeTypeGroupProps {
  edgeType: EdgeTypeKey;
  edges: Array<{ edge: { source: string; target: string; id: string }; selected: boolean }>;
  positions: Map<string, NodePosition>;
}

function EdgeTypeGroup({ edgeType, edges, positions }: EdgeTypeGroupProps) {
  // Create geometry for all edges of this type
  const { geometry, selectedGeometry } = useMemo(() => {
    const regularPositions: number[] = [];
    const selectedPositions: number[] = [];

    for (const { edge, selected } of edges) {
      const sourcePos = positions.get(edge.source);
      const targetPos = positions.get(edge.target);

      if (!sourcePos || !targetPos) continue;

      const posArray = selected ? selectedPositions : regularPositions;
      posArray.push(sourcePos.x, sourcePos.y, sourcePos.z);
      posArray.push(targetPos.x, targetPos.y, targetPos.z);
    }

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute(
      'position',
      new THREE.Float32BufferAttribute(regularPositions, 3)
    );

    const selectedGeometry = new THREE.BufferGeometry();
    selectedGeometry.setAttribute(
      'position',
      new THREE.Float32BufferAttribute(selectedPositions, 3)
    );

    return { geometry, selectedGeometry };
  }, [edges, positions]);

  const color = EDGE_COLORS[edgeType] ?? '#9E9E9E';
  const opacity = edgeType === 'composition' ? 0.8 : 0.5;
  const lineWidth = edgeType === 'composition' ? 2 : 1;

  return (
    <group>
      {/* Regular edges */}
      <lineSegments geometry={geometry}>
        <lineBasicMaterial
          color={color}
          transparent
          opacity={opacity}
          linewidth={lineWidth}
        />
      </lineSegments>

      {/* Selected edges */}
      <lineSegments geometry={selectedGeometry}>
        <lineBasicMaterial
          color={SELECTED_EDGE_COLOR}
          transparent
          opacity={1}
          linewidth={3}
        />
      </lineSegments>
    </group>
  );
}
