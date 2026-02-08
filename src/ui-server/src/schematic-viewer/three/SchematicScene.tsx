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

import { useMemo, useRef, useEffect, useCallback, useState } from 'react';
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
import { ContextMenu } from './ContextMenu';

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
      // Must update the world matrix so the raycaster below sees the
      // new camera position (updateProjectionMatrix only updates the
      // projection, not the world-space transform).
      camera.updateMatrixWorld(true);

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

// ── Selection rectangle state ──────────────────────────────────

interface SelectionRect {
  startX: number;
  startY: number;
  curX: number;
  curY: number;
}

// ── Outer wrapper (provides Canvas + selection overlay) ─────────

export function SchematicScene() {
  const theme = useTheme();
  const containerRef = useRef<HTMLDivElement>(null);
  const [selRect, setSelRect] = useState<SelectionRect | null>(null);
  const selDragging = useRef(false);

  // Window select: pointer down on empty space starts marquee.
  // We check if a Three.js object is under the cursor first —
  // if so, skip the marquee since a component/module/port handler will take over.
  const handleContainerPointerDown = useCallback(
    (e: React.PointerEvent) => {
      // Only left button
      if (e.button !== 0) return;

      // Check if a Three.js object is under the cursor via R3F's raycaster
      const container = containerRef.current;
      if (container) {
        const canvas = container.querySelector('canvas');
        if (canvas) {
          const r3f = (canvas as any).__r3f;
          if (r3f?.store) {
            const state = r3f.store.getState();
            const rect = canvas.getBoundingClientRect();
            const pointer = new THREE.Vector2(
              ((e.clientX - rect.left) / rect.width) * 2 - 1,
              -((e.clientY - rect.top) / rect.height) * 2 + 1,
            );
            const raycaster = new THREE.Raycaster();
            raycaster.setFromCamera(pointer, state.camera);
            const hits = raycaster.intersectObjects(state.scene.children, true);
            // Filter out non-interactive meshes (grids, lines, etc.)
            const interactiveHit = hits.some(
              (h) => h.object.type === 'Mesh' && !(h.object as any).__nonInteractive,
            );
            if (interactiveHit) return; // Let the R3F event system handle it
          }
        }
      }

      selDragging.current = false;
      const startX = e.clientX;
      const startY = e.clientY;

      const onMove = (me: PointerEvent) => {
        // If a component drag is active, don't start window select
        if (useSchematicStore.getState().dragComponentId) return;
        const dx = me.clientX - startX;
        const dy = me.clientY - startY;
        if (!selDragging.current && Math.sqrt(dx * dx + dy * dy) < 5) return;
        selDragging.current = true;
        setSelRect({
          startX,
          startY,
          curX: me.clientX,
          curY: me.clientY,
        });
      };

      const onUp = (me: PointerEvent) => {
        if (selDragging.current && !useSchematicStore.getState().dragComponentId) {
          // Compute world-space bounding box from screen rect
          selectItemsInRect(startX, startY, me.clientX, me.clientY, me.shiftKey);
        }
        selDragging.current = false;
        setSelRect(null);
        window.removeEventListener('pointermove', onMove);
        window.removeEventListener('pointerup', onUp);
      };

      window.addEventListener('pointermove', onMove);
      window.addEventListener('pointerup', onUp);
    },
    [],
  );

  // Convert screen rect to world-space and select items within
  const selectItemsInRect = useCallback(
    (x1: number, y1: number, x2: number, y2: number, additive: boolean) => {
      const container = containerRef.current;
      if (!container) return;

      // Find the canvas element
      const canvas = container.querySelector('canvas');
      if (!canvas) return;

      const rect = canvas.getBoundingClientRect();

      // Convert screen corners to NDC
      const toNDC = (sx: number, sy: number) => ({
        x: ((sx - rect.left) / rect.width) * 2 - 1,
        y: -((sy - rect.top) / rect.height) * 2 + 1,
      });

      const ndc1 = toNDC(x1, y1);
      const ndc2 = toNDC(x2, y2);

      // We need the camera — read it from the Three.js state
      // The camera is stored on the canvas's __r3f state
      const r3f = (canvas as any).__r3f;
      if (!r3f?.store) return;
      const camera = r3f.store.getState().camera as THREE.PerspectiveCamera;

      // Project NDC corners to world-space z=0 plane
      const raycaster = new THREE.Raycaster();
      const plane = new THREE.Plane(new THREE.Vector3(0, 0, 1), 0);
      const target = new THREE.Vector3();

      const toWorld = (ndcX: number, ndcY: number) => {
        raycaster.setFromCamera(new THREE.Vector2(ndcX, ndcY), camera);
        raycaster.ray.intersectPlane(plane, target);
        return { x: target.x, y: target.y };
      };

      const w1 = toWorld(ndc1.x, ndc1.y);
      const w2 = toWorld(ndc2.x, ndc2.y);

      const minX = Math.min(w1.x, w2.x);
      const maxX = Math.max(w1.x, w2.x);
      const minY = Math.min(w1.y, w2.y);
      const maxY = Math.max(w1.y, w2.y);

      // Find all items within the box
      const store = useSchematicStore.getState();
      const pk =
        store.currentPath.length === 0
          ? '__root__'
          : store.currentPath.join('/');
      const prefix = pk + ':';

      const matchIds: string[] = [];
      for (const [key, pos] of Object.entries(store.positions)) {
        if (!key.startsWith(prefix)) continue;
        if (pos.x >= minX && pos.x <= maxX && pos.y >= minY && pos.y <= maxY) {
          matchIds.push(key.slice(prefix.length));
        }
      }

      if (additive) {
        const existing = store.selectedComponentIds;
        const merged = [...new Set([...existing, ...matchIds])];
        store.selectComponents(merged);
      } else {
        store.selectComponents(matchIds);
      }
    },
    [],
  );

  // Right-click context menu
  const handleContextMenu = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    const store = useSchematicStore.getState();
    if (store.selectedComponentIds.length >= 2) {
      store.openContextMenu(e.clientX, e.clientY);
    }
  }, []);

  // Compute the CSS rect for the selection marquee
  const marqueeStyle = useMemo(() => {
    if (!selRect) return null;
    const left = Math.min(selRect.startX, selRect.curX);
    const top = Math.min(selRect.startY, selRect.curY);
    const width = Math.abs(selRect.curX - selRect.startX);
    const height = Math.abs(selRect.curY - selRect.startY);
    return { left, top, width, height };
  }, [selRect]);

  return (
    <div
      ref={containerRef}
      style={{ width: '100%', height: '100%', position: 'relative' }}
      onPointerDown={handleContainerPointerDown}
      onContextMenu={handleContextMenu}
    >
      <Canvas
        camera={{ position: [0, 0, 200], fov: 50, near: 0.1, far: 2000 }}
        style={{ background: theme.bgPrimary }}
        gl={{ antialias: true, powerPreference: 'high-performance' }}
        onPointerMissed={() => {
          // Don't clear selection during window-select drag
          if (selDragging.current) return;
          useSchematicStore.getState().selectComponent(null);
          useSchematicStore.getState().selectNet(null);
          useSchematicStore.getState().closeContextMenu();
        }}
      >
        <SceneContent theme={theme} />
      </Canvas>

      {/* Selection marquee overlay */}
      {marqueeStyle && (
        <div
          style={{
            position: 'fixed',
            left: marqueeStyle.left,
            top: marqueeStyle.top,
            width: marqueeStyle.width,
            height: marqueeStyle.height,
            border: `1px solid ${theme.accent}`,
            background: `${theme.accent}22`,
            pointerEvents: 'none',
            zIndex: 100,
          }}
        />
      )}

      {/* Context menu */}
      <ContextMenu theme={theme} />
    </div>
  );
}
