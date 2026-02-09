import { useMemo } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import { useTreeStore } from '../stores/treeStore';
import { TreeNodeMesh } from './TreeNodeMesh';
import { TreeEdgeLines } from './TreeEdgeLines';
import { GroupBox } from './GroupBox';
import { useTheme } from '../lib/theme';

export function TreeScene() {
  const { graphData, layout } = useTreeStore();
  const theme = useTheme();

  // Compute groups from node data
  const groups = useMemo(() => {
    if (!graphData) return [];
    const groupMap = new Map<string, { label: string; memberIds: string[]; accent: string }>();
    for (const node of graphData.nodes) {
      if (node.group && node.groupLabel) {
        const existing = groupMap.get(node.group);
        if (existing) {
          existing.memberIds.push(node.id);
        } else {
          // Pick accent from node type
          const accent = node.type === 'controller' ? theme.nodeController
            : node.type === 'source' ? theme.nodeSource
            : node.type === 'sink' ? theme.nodeSink
            : theme.nodeBus;
          groupMap.set(node.group, { label: node.groupLabel, memberIds: [node.id], accent });
        }
      }
    }
    return Array.from(groupMap.entries()).map(([id, data]) => ({
      groupId: id,
      ...data,
    }));
  }, [graphData, theme]);

  if (!graphData || !layout) return null;

  const { bounds } = layout;
  const centerX = ((bounds.minX + bounds.maxX) / 2) / 100;
  const centerY = ((bounds.minY + bounds.maxY) / 2) / 100;
  const rangeX = (bounds.maxX - bounds.minX) / 100;
  const rangeY = (bounds.maxY - bounds.minY) / 100;
  const camDistance = Math.max(rangeX, rangeY) * 0.8 + 3;

  return (
    <Canvas
      camera={{
        position: [centerX, centerY, camDistance],
        fov: 50,
        near: 0.1,
        far: 1000,
      }}
      style={{ background: theme.bgPrimary }}
      onPointerMissed={() => {
        useTreeStore.getState().setSelectedNode(null);
      }}
    >
      <ambientLight intensity={1} />

      <OrbitControls
        target={[centerX, centerY, 0]}
        enableRotate={false}
        enablePan={true}
        enableZoom={true}
        minDistance={1}
        maxDistance={50}
        mouseButtons={{
          LEFT: 2,
          MIDDLE: 1,
          RIGHT: 2,
        }}
      />

      {/* Group backgrounds (behind everything) */}
      {groups.map((g) => (
        <GroupBox
          key={g.groupId}
          groupId={g.groupId}
          label={g.label}
          accent={g.accent}
          memberIds={g.memberIds}
          positions={layout.positions}
          theme={theme}
        />
      ))}

      {/* Edges */}
      <TreeEdgeLines edges={graphData.edges} positions={layout.positions} theme={theme} />

      {/* Nodes */}
      {graphData.nodes.map((node) => {
        const pos = layout.positions.get(node.id);
        if (!pos) return null;
        return <TreeNodeMesh key={node.id} node={node} position={pos} theme={theme} />;
      })}
    </Canvas>
  );
}
