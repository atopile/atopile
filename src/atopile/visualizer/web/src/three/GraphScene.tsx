/**
 * Main Three.js scene component for graph visualization.
 *
 * Manages the 3D scene, camera, controls, and orchestrates
 * the rendering of nodes and edges.
 */

import { useEffect, useCallback, useRef } from 'react';
import { Canvas, useThree, useFrame } from '@react-three/fiber';
import { OrbitControls, PerspectiveCamera } from '@react-three/drei';
import * as THREE from 'three';
import { useGraphStore } from '../stores/graphStore';
import { useViewStore } from '../stores/viewStore';
import { useSelectionStore } from '../stores/selectionStore';
import { useFilterStore } from '../stores/filterStore';
import { useCollapseStore } from '../stores/collapseStore';
import { useNavigationStore } from '../stores/navigationStore';
import { useMemo } from 'react';
import { computeVisibleNodesWithNavigation, computeVisibleEdges } from '../lib/filterEngine';
import { getAncestors } from '../lib/graphIndex';
import { NodeMesh } from './NodeMesh';
import { EdgeLines } from './EdgeLines';

/**
 * Hook to handle keyboard shortcuts.
 */
function useKeyboardShortcuts(visibleNodes: Set<string>, visibleEdges: Set<string>) {
  const { bounds, runLayout } = useGraphStore();
  const { fitToView, resetView, toggleLabels } = useViewStore();
  const { clearSelection, selectedNodes } = useSelectionStore();
  const { toggleCollapse, expandAllNodes } = useCollapseStore();

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Ignore if typing in an input
      if (
        event.target instanceof HTMLInputElement ||
        event.target instanceof HTMLTextAreaElement
      ) {
        return;
      }

      switch (event.key.toLowerCase()) {
        case 'f':
          // F = Fit to view
          fitToView(bounds);
          break;

        case 'escape':
          // Escape = Clear selection
          clearSelection();
          break;

        case 'l':
          // L = Toggle labels
          toggleLabels();
          break;

        case 'r':
          // R = Re-run layout (only visible nodes)
          if (!event.ctrlKey && !event.metaKey) {
            runLayout(visibleNodes, visibleEdges);
          }
          break;

        case 'e':
          // E = Expand all
          expandAllNodes();
          break;

        case 'c':
          // C = Collapse selected (if any selected)
          if (!event.ctrlKey && !event.metaKey && selectedNodes.size > 0) {
            for (const nodeId of selectedNodes) {
              toggleCollapse(nodeId);
            }
          }
          break;

        case 'h':
          // H = Home (reset view)
          resetView();
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [
    bounds,
    fitToView,
    clearSelection,
    toggleLabels,
    runLayout,
    expandAllNodes,
    toggleCollapse,
    selectedNodes,
    resetView,
    visibleNodes,
    visibleEdges,
  ]);
}

/**
 * Camera animator component for smooth camera transitions.
 */
function CameraAnimator({ controlsRef }: { controlsRef: React.RefObject<any> }) {
  const { animationTarget, isAnimating, clearAnimation } = useViewStore();
  const { camera } = useThree();

  // Animation state
  const startPosRef = useRef(new THREE.Vector3());
  const startTargetRef = useRef(new THREE.Vector3());
  const progressRef = useRef(0);
  const animationDuration = 0.5; // seconds

  useFrame((_, delta) => {
    if (!isAnimating || !animationTarget || !controlsRef.current) return;

    const controls = controlsRef.current;

    // Initialize animation on first frame
    if (progressRef.current === 0) {
      startPosRef.current.copy(camera.position);
      startTargetRef.current.copy(controls.target);
    }

    // Update progress
    progressRef.current += delta / animationDuration;

    if (progressRef.current >= 1) {
      // Animation complete
      camera.position.set(
        animationTarget.position.x,
        animationTarget.position.y,
        animationTarget.position.z
      );
      controls.target.set(
        animationTarget.lookAt.x,
        animationTarget.lookAt.y,
        animationTarget.lookAt.z
      );
      controls.update();
      progressRef.current = 0;
      clearAnimation();
      return;
    }

    // Smooth easing (ease-out cubic)
    const t = 1 - Math.pow(1 - progressRef.current, 3);

    // Interpolate camera position
    camera.position.lerpVectors(
      startPosRef.current,
      new THREE.Vector3(
        animationTarget.position.x,
        animationTarget.position.y,
        animationTarget.position.z
      ),
      t
    );

    // Interpolate look-at target
    const newTarget = new THREE.Vector3().lerpVectors(
      startTargetRef.current,
      new THREE.Vector3(
        animationTarget.lookAt.x,
        animationTarget.lookAt.y,
        animationTarget.lookAt.z
      ),
      t
    );
    controls.target.copy(newTarget);
    controls.update();
  });

  return null;
}

/**
 * Inner scene component that has access to Three.js context.
 */
function SceneContent() {
  const { data, index, positions, bounds, runLayout } = useGraphStore();
  const { cameraPosition, fitToView, setZoom, animateTo } = useViewStore();
  const {
    selectedNodes,
    hoveredNode,
    selectNode,
    setHoveredNode,
    setFocusedNode,
  } = useSelectionStore();
  const { config: filterConfig } = useFilterStore();
  const { state: collapseState } = useCollapseStore();
  const { currentRootId, viewDepth, depthEnabled, navigateTo } = useNavigationStore();
  const controlsRef = useRef<any>(null);

  // Compute visible nodes and edges based on filters, collapse state, and navigation
  const { visibleNodes, visibleEdges } = useMemo(() => {
    if (!data || !index) {
      return { visibleNodes: new Set<string>(), visibleEdges: new Set<string>() };
    }

    const navigation = { currentRootId, viewDepth, depthEnabled };
    const visibleNodes = computeVisibleNodesWithNavigation(data, index, filterConfig, collapseState, navigation);
    const visibleEdges = computeVisibleEdges(data, filterConfig, visibleNodes);

    return { visibleNodes, visibleEdges };
  }, [data, index, filterConfig, collapseState, currentRootId, viewDepth, depthEnabled]);

  // Use keyboard shortcuts (needs visible nodes/edges for layout)
  useKeyboardShortcuts(visibleNodes, visibleEdges);

  // Re-run layout when visibility changes significantly or navigation changes
  const prevVisibleCountRef = useRef<number>(0);
  const prevRootRef = useRef<string | null>(null);
  useEffect(() => {
    const currentCount = visibleNodes.size;
    const prevCount = prevVisibleCountRef.current;
    const rootChanged = prevRootRef.current !== currentRootId;

    // Re-layout if count changed by more than 10%, first render, or root changed
    if (
      data &&
      index &&
      visibleNodes.size > 0 &&
      (prevCount === 0 || rootChanged || Math.abs(currentCount - prevCount) / prevCount > 0.1)
    ) {
      runLayout(visibleNodes, visibleEdges);
    }

    prevVisibleCountRef.current = currentCount;
    prevRootRef.current = currentRootId;
  }, [data, index, visibleNodes, visibleEdges, currentRootId, runLayout]);

  // Fit to view when bounds change initially
  const initialFitDone = useRef(false);
  useEffect(() => {
    if (!initialFitDone.current && bounds.maxX !== bounds.minX) {
      fitToView(bounds);
      initialFitDone.current = true;
    }
  }, [bounds]);

  // Handle double-click to navigate into a node
  const handleDoubleClick = useCallback(
    (nodeId: string) => {
      if (!index) return;

      const node = index.nodesById.get(nodeId);
      if (!node) return;

      // Only navigate if node has children
      if (node.childCount > 0) {
        // Build ancestors for breadcrumb
        const ancestorIds = getAncestors(nodeId, index);
        const ancestors: Array<{ id: string; name: string }> = [];

        for (const ancestorId of ancestorIds) {
          const ancestorNode = index.nodesById.get(ancestorId);
          if (ancestorNode) {
            ancestors.unshift({
              id: ancestorId,
              name: ancestorNode.name ?? ancestorNode.typeName ?? 'node',
            });
          }
        }

        navigateTo(nodeId, node.name ?? node.typeName ?? 'node', ancestors);
      }

      setFocusedNode(nodeId);

      const pos = positions.get(nodeId);
      if (pos) {
        // Animate camera to focus on the node
        animateTo({
          position: { x: pos.x, y: pos.y, z: pos.z + 150 },
          lookAt: { x: pos.x, y: pos.y, z: pos.z },
        });
      }
    },
    [positions, setFocusedNode, animateTo, index, navigateTo]
  );

  // Track zoom level from controls
  const { camera } = useThree();
  useEffect(() => {
    if (controlsRef.current) {
      const controls = controlsRef.current;

      const handleChange = () => {
        // Calculate zoom based on camera distance
        const distance = camera.position.length();
        const zoom = 500 / distance;
        setZoom(zoom);
      };

      controls.addEventListener('change', handleChange);
      return () => controls.removeEventListener('change', handleChange);
    }
  }, [camera, setZoom]);

  if (!data || !index) {
    return null;
  }

  return (
    <>
      <PerspectiveCamera
        makeDefault
        position={[cameraPosition.x, cameraPosition.y, cameraPosition.z]}
        fov={60}
        near={0.1}
        far={10000}
      />

      <OrbitControls
        ref={controlsRef}
        enableDamping
        dampingFactor={0.1}
        enablePan
        panSpeed={1}
        enableZoom
        zoomSpeed={0.6}
        enableRotate
        rotateSpeed={0.5}
        minDistance={20}
        maxDistance={3000}
        makeDefault
      />

      {/* Camera animation handler */}
      <CameraAnimator controlsRef={controlsRef} />

      {/* Lighting */}
      <ambientLight intensity={0.5} />
      <directionalLight position={[100, 100, 100]} intensity={0.6} />
      <directionalLight position={[-100, -100, 50]} intensity={0.3} />
      <hemisphereLight
        args={['#87ceeb', '#362107', 0.3]}
      />

      {/* Nodes */}
      <NodeMesh
        data={data}
        index={index}
        positions={positions}
        visibleNodes={visibleNodes}
        selectedNodes={selectedNodes}
        hoveredNode={hoveredNode}
        collapseState={collapseState}
        onSelect={selectNode}
        onHover={setHoveredNode}
        onDoubleClick={handleDoubleClick}
      />

      {/* Edges */}
      <EdgeLines
        data={data}
        index={index}
        positions={positions}
        visibleEdges={visibleEdges}
        selectedNodes={selectedNodes}
      />

      {/* Grid helper for orientation (subtle) */}
      <gridHelper
        args={[1000, 50, '#1e293b', '#0f172a']}
        position={[0, -50, 0]}
        rotation={[0, 0, 0]}
      />
    </>
  );
}

export function GraphScene() {
  const { data, isLoading, loadError } = useGraphStore();
  const { clearSelection } = useSelectionStore();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full bg-graph-bg">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-accent mx-auto mb-4"></div>
          <div className="text-text-secondary">Loading graph...</div>
        </div>
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="flex items-center justify-center h-full bg-graph-bg">
        <div className="text-center max-w-md p-6">
          <div className="text-red-400 text-4xl mb-4">!</div>
          <div className="text-lg font-medium text-text-primary mb-2">
            Failed to load graph
          </div>
          <div className="text-sm text-text-secondary mb-4">{loadError}</div>
          <div className="text-xs text-text-secondary">
            Make sure graph.json is available at the server root.
          </div>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex items-center justify-center h-full bg-graph-bg">
        <div className="text-text-secondary">No graph data loaded</div>
      </div>
    );
  }

  return (
    <Canvas
      className="w-full h-full"
      gl={{
        antialias: true,
        alpha: false,
        powerPreference: 'high-performance',
      }}
      onPointerMissed={() => clearSelection()}
    >
      <color attach="background" args={['#0f172a']} />
      <SceneContent />
    </Canvas>
  );
}
