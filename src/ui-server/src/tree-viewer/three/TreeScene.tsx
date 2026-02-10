import { useEffect, useMemo, useRef, type MutableRefObject } from 'react';
import { Canvas, useThree } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import * as THREE from 'three';
import { useTreeStore } from '../stores/treeStore';
import { TreeNodeMesh } from './TreeNodeMesh';
import { TreeEdgeLines } from './TreeEdgeLines';
import { GroupBox } from './GroupBox';
import { useTheme } from '../lib/theme';

function ZoomToCursor({ controlsRef }: { controlsRef: MutableRefObject<any> }) {
  const { camera, gl } = useThree();
  const zoomRaycaster = useRef(new THREE.Raycaster());
  const zoomPlane = useRef(new THREE.Plane(new THREE.Vector3(0, 0, 1), 0));
  const zoomNDC = useRef(new THREE.Vector2());
  const zoomWorldA = useRef(new THREE.Vector3());
  const zoomWorldB = useRef(new THREE.Vector3());

  useEffect(() => {
    const canvas = gl.domElement;

    const handleWheel = (e: WheelEvent) => {
      e.preventDefault();

      const rect = canvas.getBoundingClientRect();
      zoomNDC.current.set(
        ((e.clientX - rect.left) / rect.width) * 2 - 1,
        -((e.clientY - rect.top) / rect.height) * 2 + 1,
      );

      // World point under cursor BEFORE zoom.
      zoomRaycaster.current.setFromCamera(zoomNDC.current, camera);
      zoomRaycaster.current.ray.intersectPlane(
        zoomPlane.current,
        zoomWorldA.current,
      );

      // Match schematic-viewer zoom response.
      const rawDelta = e.deltaMode === 1 ? e.deltaY * 33 : e.deltaY;
      const step = rawDelta * 0.002;
      const factor = Math.exp(step);
      const newZ = THREE.MathUtils.clamp(camera.position.z * factor, 0.4, 400);
      camera.position.z = newZ;
      camera.updateMatrixWorld(true);

      // World point under cursor AFTER zoom.
      zoomRaycaster.current.setFromCamera(zoomNDC.current, camera);
      zoomRaycaster.current.ray.intersectPlane(
        zoomPlane.current,
        zoomWorldB.current,
      );

      // Pan to keep the same world point under the cursor.
      const dx = zoomWorldA.current.x - zoomWorldB.current.x;
      const dy = zoomWorldA.current.y - zoomWorldB.current.y;
      camera.position.x += dx;
      camera.position.y += dy;

      if (controlsRef.current) {
        controlsRef.current.target.x += dx;
        controlsRef.current.target.y += dy;
        controlsRef.current.update();
      }
    };

    canvas.addEventListener('wheel', handleWheel, { passive: false });
    return () => canvas.removeEventListener('wheel', handleWheel);
  }, [camera, controlsRef, gl]);

  return null;
}

export function TreeScene() {
  const { graphData, layout } = useTreeStore();
  const theme = useTheme();
  const controlsRef = useRef<any>(null);

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
      <ZoomToCursor controlsRef={controlsRef} />
      <ambientLight intensity={1} />

      <OrbitControls
        ref={controlsRef}
        target={[centerX, centerY, 0]}
        enableRotate={false}
        enablePan={true}
        enableZoom={false}
        minDistance={1}
        maxDistance={50}
        mouseButtons={{
          LEFT: 0 as any,
          MIDDLE: 1 as any,
          RIGHT: 2 as any,
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
