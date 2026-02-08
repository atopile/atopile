/**
 * SchematicScene — main Three.js canvas for the hierarchical schematic viewer.
 *
 * Renders the current sheet's modules (as ModuleBlocks) and components
 * (as ComponentRenderers), with net lines connecting them.
 *
 * Performance notes:
 * - Camera auto-fit runs once per sheet navigation
 * - itemNetMaps is memoized on the current sheet
 * - Positions are read imperatively for camera fit (no React subscription)
 * - OrbitControls disabled during drag
 */

import { useMemo, useRef, useEffect, useCallback } from 'react';
import { Canvas, useThree } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import * as THREE from 'three';
import type { ThemeColors } from '../lib/theme';
import { useTheme } from '../lib/theme';
import {
  useSchematicStore,
  useCurrentSheet,
  useCurrentPorts,
} from '../stores/schematicStore';
import { DraggableComponent } from './DraggableComponent';
import { DraggableModule } from './DraggableModule';
import { DraggablePort } from './DraggablePort';
import { NetLines } from './NetLines';
import { GridBackground } from './GridBackground';

/** Stable singleton for items with no net connections. */
const EMPTY_NET_MAP = new Map<string, string>();

// ── Inner scene (has access to useThree) ───────────────────────

function SceneContent({ theme }: { theme: ThemeColors }) {
  const sheet = useCurrentSheet();
  const ports = useCurrentPorts();
  const currentPath = useSchematicStore((s) => s.currentPath);
  const dragComponentId = useSchematicStore((s) => s.dragComponentId);
  const selectedNetId = useSchematicStore((s) => s.selectedNetId);

  const controlsRef = useRef<any>(null);
  const { camera, gl } = useThree();
  const lastFitPath = useRef<string | null>(null);

  // ── Auto-fit camera when sheet changes ───────────────────────

  const fitCamera = useCallback(() => {
    const pk = currentPath.join('/') || '__root__';
    if (lastFitPath.current === pk) return;

    const positions = useSchematicStore.getState().positions;
    if (!sheet) return;

    // Collect all item IDs at this level (including ports)
    const allItems = [
      ...sheet.components.map((c) => ({
        id: c.id,
        w: c.bodyWidth,
        h: c.bodyHeight,
      })),
      ...sheet.modules.map((m) => ({
        id: m.id,
        w: m.bodyWidth,
        h: m.bodyHeight,
      })),
      ...ports.map((p) => ({
        id: p.id,
        w: p.bodyWidth,
        h: p.bodyHeight,
      })),
    ];

    if (allItems.length === 0) return;

    const prefix = pk + ':';
    let hasAny = false;
    let minX = Infinity,
      minY = Infinity,
      maxX = -Infinity,
      maxY = -Infinity;

    for (const item of allItems) {
      const p = positions[prefix + item.id];
      if (!p) continue;
      hasAny = true;
      const hW = item.w / 2 + 6;
      const hH = item.h / 2 + 6;
      minX = Math.min(minX, p.x - hW);
      maxX = Math.max(maxX, p.x + hW);
      minY = Math.min(minY, p.y - hH);
      maxY = Math.max(maxY, p.y + hH);
    }

    if (!hasAny) return;
    lastFitPath.current = pk;

    const cx = (minX + maxX) / 2;
    const cy = (minY + maxY) / 2;
    const range = Math.max(maxX - minX, maxY - minY);
    const distance = range * 0.65 + 30;

    camera.position.set(cx, cy, distance);
    camera.lookAt(cx, cy, 0);

    if (controlsRef.current) {
      controlsRef.current.target.set(cx, cy, 0);
      controlsRef.current.update();
    }
  }, [sheet, ports, currentPath, camera]);

  // Subscribe to positions to detect first layout completion
  useEffect(() => {
    fitCamera();
    const unsub = useSchematicStore.subscribe(
      (s) => s.positions,
      () => fitCamera(),
    );
    return unsub;
  }, [fitCamera]);

  // Reset camera fit when navigating
  useEffect(() => {
    const pk = currentPath.join('/') || '__root__';
    if (lastFitPath.current !== pk) {
      lastFitPath.current = null;
      fitCamera();
    }
  }, [currentPath, fitCamera]);

  // ── Disable orbit controls while dragging ────────────────────

  useEffect(() => {
    if (controlsRef.current) {
      controlsRef.current.enabled = !dragComponentId;
    }
  }, [dragComponentId]);

  // ── Zoom-to-cursor (replaces OrbitControls zoom) ─────────────
  // Projects a ray from the mouse to the z=0 plane before and after
  // changing the camera distance, then pans to compensate so the
  // world point under the cursor stays fixed.

  const zoomRaycaster = useRef(new THREE.Raycaster());
  const zoomPlane = useRef(new THREE.Plane(new THREE.Vector3(0, 0, 1), 0));
  const zoomNDC = useRef(new THREE.Vector2());
  const zoomWorldA = useRef(new THREE.Vector3());
  const zoomWorldB = useRef(new THREE.Vector3());

  useEffect(() => {
    const canvas = gl.domElement;

    const handleWheel = (e: WheelEvent) => {
      e.preventDefault();

      // If dragging a component, ignore zoom
      if (useSchematicStore.getState().dragComponentId) return;

      // Mouse position in NDC (-1 to +1)
      const rect = canvas.getBoundingClientRect();
      zoomNDC.current.set(
        ((e.clientX - rect.left) / rect.width) * 2 - 1,
        -((e.clientY - rect.top) / rect.height) * 2 + 1,
      );

      // World point under cursor BEFORE zoom
      zoomRaycaster.current.setFromCamera(zoomNDC.current, camera);
      zoomRaycaster.current.ray.intersectPlane(
        zoomPlane.current,
        zoomWorldA.current,
      );

      // Apply zoom (dolly camera along z)
      const zoomSpeed = 1.08;
      const factor = e.deltaY > 0 ? zoomSpeed : 1 / zoomSpeed;
      const newZ = THREE.MathUtils.clamp(
        camera.position.z * factor,
        5,
        800,
      );
      camera.position.z = newZ;
      camera.updateProjectionMatrix();

      // World point under cursor AFTER zoom
      zoomRaycaster.current.setFromCamera(zoomNDC.current, camera);
      zoomRaycaster.current.ray.intersectPlane(
        zoomPlane.current,
        zoomWorldB.current,
      );

      // Pan to keep the same world point under the cursor
      const dx = zoomWorldA.current.x - zoomWorldB.current.x;
      const dy = zoomWorldA.current.y - zoomWorldB.current.y;
      camera.position.x += dx;
      camera.position.y += dy;

      // Keep OrbitControls target in sync so panning stays correct
      if (controlsRef.current) {
        controlsRef.current.target.x += dx;
        controlsRef.current.target.y += dy;
        controlsRef.current.update();
      }
    };

    canvas.addEventListener('wheel', handleWheel, { passive: false });
    return () => canvas.removeEventListener('wheel', handleWheel);
  }, [camera, gl]);

  // ── Precompute pin→net lookup for all items at this level ────

  const itemNetMaps = useMemo(() => {
    if (!sheet) return new Map<string, Map<string, string>>();
    const maps = new Map<string, Map<string, string>>();

    // Components
    for (const comp of sheet.components) {
      maps.set(comp.id, new Map());
    }
    // Modules
    for (const mod of sheet.modules) {
      maps.set(mod.id, new Map());
    }
    // Ports
    for (const port of ports) {
      maps.set(port.id, new Map());
    }
    // Nets reference all item types
    for (const net of sheet.nets) {
      for (const pin of net.pins) {
        maps.get(pin.componentId)?.set(pin.pinNumber, net.id);
      }
    }
    return maps;
  }, [sheet, ports]);

  if (!sheet) return null;

  return (
    <>
      <ambientLight intensity={1} />

      <OrbitControls
        ref={controlsRef}
        enableRotate={false}
        enablePan
        enableZoom={false}
        mouseButtons={{
          LEFT: 0 as any,
          MIDDLE: 1 as any,
          RIGHT: 2 as any,
        }}
      />

      <GridBackground theme={theme} />

      {/* Nets behind everything */}
      <group position={[0, 0, -0.03]}>
        <NetLines theme={theme} />
      </group>

      {/* Modules (expandable blocks) */}
      {sheet.modules.map((mod) => (
        <DraggableModule
          key={mod.id}
          module={mod}
          theme={theme}
          selectedNetId={selectedNetId}
          netsForModule={
            itemNetMaps.get(mod.id) || EMPTY_NET_MAP
          }
        />
      ))}

      {/* Components (leaf parts) */}
      {sheet.components.map((comp) => (
        <DraggableComponent
          key={comp.id}
          component={comp}
          theme={theme}
          selectedNetId={selectedNetId}
          netsForComponent={
            itemNetMaps.get(comp.id) || EMPTY_NET_MAP
          }
        />
      ))}

      {/* Ports (external interface entries — only when inside a module) */}
      {ports.map((port) => {
        const portNets = itemNetMaps.get(port.id);
        // A port has a single pin "1" — get its net ID
        const netId = portNets?.get('1') ?? null;
        return (
          <DraggablePort
            key={port.id}
            port={port}
            theme={theme}
            selectedNetId={selectedNetId}
            netId={netId}
          />
        );
      })}
    </>
  );
}

// ── Outer wrapper (provides Canvas) ────────────────────────────

export function SchematicScene() {
  const theme = useTheme();

  return (
    <Canvas
      camera={{ position: [0, 0, 200], fov: 50, near: 0.1, far: 2000 }}
      style={{ background: theme.bgPrimary }}
      gl={{ antialias: true, powerPreference: 'high-performance' }}
      onPointerMissed={() => {
        useSchematicStore.getState().selectComponent(null);
        useSchematicStore.getState().selectNet(null);
      }}
    >
      <SceneContent theme={theme} />
    </Canvas>
  );
}
