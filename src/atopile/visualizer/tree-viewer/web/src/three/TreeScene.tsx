import { Canvas } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import { useTreeStore } from '../stores/treeStore';
import { TreeNodeMesh } from './TreeNodeMesh';
import { TreeEdgeLines } from './TreeEdgeLines';
import { useTheme } from '../lib/theme';

export function TreeScene() {
  const { graphData, layout } = useTreeStore();
  const theme = useTheme();

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

      <TreeEdgeLines edges={graphData.edges} positions={layout.positions} theme={theme} />

      {graphData.nodes.map((node) => {
        const pos = layout.positions.get(node.id);
        if (!pos) return null;
        return <TreeNodeMesh key={node.id} node={node} position={pos} theme={theme} />;
      })}
    </Canvas>
  );
}
