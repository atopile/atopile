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
import type { ThemeColors } from '../utils/theme';
import { useTheme } from '../utils/theme';
import {
  getRootSheet,
  resolveSheet,
  derivePortsFromModule,
  derivePowerPorts,
  getPortPinNumbers,
} from '../types/schematic';
import {
  useSchematicStore,
  useCurrentSheet,
  useCurrentPorts,
  useCurrentPowerPorts,
} from '../stores/schematicStore';
import { DraggableComponent } from './DraggableComponent';
import { DraggableModule } from './DraggableModule';
import { DraggablePort } from './DraggablePort';
import { DraggablePowerPort } from './DraggablePowerPort';
import { NetLines } from './NetLines';
import { GridBackground } from './GridBackground';
import { ContextMenu } from './ContextMenu';
import { getModuleRenderSize } from '../utils/moduleInterfaces';

/** Stable singleton for items with no net connections. */
const EMPTY_NET_MAP = new Map<string, string>();

function scenePathKey(path: string[]): string {
  return path.length === 0 ? '__root__' : path.join('/');
}

// ── Inner scene (has access to useThree) ───────────────────────

function SceneContent({
  theme,
  onSceneReady,
}: {
  theme: ThemeColors;
  onSceneReady?: (scene: THREE.Scene, camera: THREE.Camera, canvas: HTMLCanvasElement) => void;
}) {
  const sheet = useCurrentSheet();
  const ports = useCurrentPorts();
  const powerPorts = useCurrentPowerPorts();
  const currentPath = useSchematicStore((s) => s.currentPath);
  const dragComponentId = useSchematicStore((s) => s.dragComponentId);
  const selectedNetId = useSchematicStore((s) => s.selectedNetId);
  const focusRequest = useSchematicStore((s) => s.focusRequest);

  const controlsRef = useRef<any>(null);
  const { camera, gl, scene } = useThree();
  const lastFitPath = useRef<string | null>(null);

  useEffect(() => {
    onSceneReady?.(scene, camera, gl.domElement);
  }, [onSceneReady, scene, camera, gl]);

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
        w: getModuleRenderSize(m).width,
        h: getModuleRenderSize(m).height,
      })),
      ...ports.map((p) => ({
        id: p.id,
        w: p.bodyWidth,
        h: p.bodyHeight,
      })),
      ...powerPorts.map((p) => ({
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
  }, [sheet, ports, powerPorts, currentPath, camera]);

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

  // ── Explicit camera focus for "Show in Schematic" actions ───

  useEffect(() => {
    if (!focusRequest) return;

    const activePathKey = scenePathKey(currentPath);
    const requestPathKey = scenePathKey(focusRequest.path);
    if (activePathKey !== requestPathKey) return;

    const pos = useSchematicStore.getState().positions[`${activePathKey}:${focusRequest.id}`];
    if (!pos) return;

    const keepZ = camera.position.z;
    camera.position.set(pos.x, pos.y, keepZ);
    camera.lookAt(pos.x, pos.y, 0);

    if (controlsRef.current) {
      controlsRef.current.target.set(pos.x, pos.y, 0);
      controlsRef.current.update();
    }
  }, [focusRequest?.nonce, currentPath, camera]);

  // ── Zoom-to-cursor (KiCad-style) ────────────────────────────
  // Smooth zoom using continuous delta normalization. The world point
  // under the cursor stays fixed by reprojecting before/after the
  // camera distance change and panning to compensate.

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

      // KiCad-style zoom: normalize deltaY to a continuous scale factor.
      // Typical deltaY values: ±100 (pixel mode), ±3 (line mode).
      // Normalize to a small step then exponentiate for proportional feel.
      const rawDelta = e.deltaMode === 1 ? e.deltaY * 33 : e.deltaY;
      const step = rawDelta * 0.002; // ~0.2 per 100px scroll
      const factor = Math.exp(step);
      const newZ = THREE.MathUtils.clamp(
        camera.position.z * factor,
        2,
        1500,
      );
      camera.position.z = newZ;
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
    // Power ports
    for (const pp of powerPorts) {
      maps.set(pp.id, new Map());
    }
    // Nets reference all item types
    for (const net of sheet.nets) {
      for (const pin of net.pins) {
        maps.get(pin.componentId)?.set(pin.pinNumber, net.id);
      }
    }
    return maps;
  }, [sheet, ports, powerPorts]);

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
        const netId =
          (portNets
            ? getPortPinNumbers(port).map((pin) => portNets.get(pin)).find((id) => !!id) ?? null
            : null);
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

      {/* Power/ground symbols (movable) */}
      {powerPorts.map((pp) => (
        <DraggablePowerPort
          key={pp.id}
          powerPort={pp}
          theme={theme}
          selectedNetId={selectedNetId}
        />
      ))}
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
  const portEditMode = useSchematicStore((s) => s.portEditMode);
  const portEditTargetId = useSchematicStore((s) => s.portEditTargetId);
  const setPortEditMode = useSchematicStore((s) => s.setPortEditMode);
  const currentSheet = useCurrentSheet();
  const ports = useCurrentPorts();
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const cameraRef = useRef<THREE.Camera | null>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const selectRaycasterRef = useRef(new THREE.Raycaster());
  const selectNdcRef = useRef(new THREE.Vector2());
  const projectVecRef = useRef(new THREE.Vector3());
  const projectCornerMinRef = useRef(new THREE.Vector3());
  const projectCornerMaxRef = useRef(new THREE.Vector3());
  const [selRect, setSelRect] = useState<SelectionRect | null>(null);
  const selDragging = useRef(false);
  const portEditTargetPortName = useMemo(
    () => ports.find((p) => p.id === portEditTargetId)?.name ?? null,
    [ports, portEditTargetId],
  );
  const portEditTargetModuleName = useMemo(
    () => currentSheet?.modules.find((m) => m.id === portEditTargetId)?.name ?? null,
    [currentSheet, portEditTargetId],
  );
  const isEditingModulePorts = !!portEditTargetModuleName;
  const portEditTargetName = portEditTargetPortName
    ?? portEditTargetModuleName
    ?? portEditTargetId
    ?? 'port';

  const handleSceneReady = useCallback(
    (scene: THREE.Scene, camera: THREE.Camera, canvas: HTMLCanvasElement) => {
      sceneRef.current = scene;
      cameraRef.current = camera;
      canvasRef.current = canvas;
    },
    [],
  );

  // Window select: pointer down on empty space starts marquee.
  // We check if a Three.js object is under the cursor first —
  // if so, skip the marquee since a component/module/port handler will take over.
  const handleContainerPointerDown = useCallback(
    (e: React.PointerEvent) => {
      // Only left button
      if (e.button !== 0) return;
      if (useSchematicStore.getState().portEditMode) return;

      // Check if a Three.js object is under the cursor via R3F's raycaster
      const container = containerRef.current;
      if (container) {
        const canvas = canvasRef.current ?? container.querySelector('canvas');
        const camera = cameraRef.current;
        const scene = sceneRef.current;
        if (canvas && camera && scene) {
          const rect = canvas.getBoundingClientRect();
          selectNdcRef.current.set(
            ((e.clientX - rect.left) / rect.width) * 2 - 1,
            -((e.clientY - rect.top) / rect.height) * 2 + 1,
          );
          selectRaycasterRef.current.setFromCamera(selectNdcRef.current, camera);
          const hits = selectRaycasterRef.current.intersectObjects(scene.children, true);
          // Filter out non-interactive meshes (grids, lines, etc.)
          const interactiveHit = hits.some(
            (h) => h.object.type === 'Mesh' && !(h.object as any).__nonInteractive,
          );
          if (interactiveHit) return; // Let the R3F event system handle it
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
        const wasSelecting = selDragging.current;
        if (wasSelecting && !useSchematicStore.getState().dragComponentId) {
          // Compute world-space bounding box from screen rect
          selectItemsInRect(startX, startY, me.clientX, me.clientY, me.shiftKey);
        }
        setSelRect(null);
        window.removeEventListener('pointermove', onMove);
        window.removeEventListener('pointerup', onUp);
        // After a window selection, leave selDragging=true so onPointerMissed
        // (which fires asynchronously via R3F) sees the guard and doesn't clear
        // the just-set selection. The flag gets reset at the start of the next
        // handleContainerPointerDown, so click-to-deselect still works.
        if (!wasSelecting) {
          selDragging.current = false;
        }
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

      const canvas = canvasRef.current ?? container.querySelector('canvas');
      if (!canvas) return;

      const cam = cameraRef.current;
      if (!cam) return;
      cam.updateMatrixWorld(true);

      const canvasRect = canvas.getBoundingClientRect();
      const minSelX = Math.min(x1, x2);
      const maxSelX = Math.max(x1, x2);
      const minSelY = Math.min(y1, y2);
      const maxSelY = Math.max(y1, y2);

      // Find all items within the box
      const store = useSchematicStore.getState();
      const pk =
        store.currentPath.length === 0
          ? '__root__'
          : store.currentPath.join('/');
      const prefix = pk + ':';
      const itemDims = new Map<string, { w: number; h: number }>();
      if (store.schematic) {
        const root = getRootSheet(store.schematic);
        const sheet = resolveSheet(root, store.currentPath);
        if (sheet) {
          for (const comp of sheet.components) {
            itemDims.set(comp.id, { w: comp.bodyWidth, h: comp.bodyHeight });
          }
          for (const mod of sheet.modules) {
            const size = getModuleRenderSize(mod);
            itemDims.set(mod.id, { w: size.width, h: size.height });
          }
          const pports = derivePowerPorts(sheet);
          for (const pp of pports) {
            itemDims.set(pp.id, { w: pp.bodyWidth, h: pp.bodyHeight });
          }
          if (store.currentPath.length > 0) {
            const parentPath = store.currentPath.slice(0, -1);
            const parentSheet = resolveSheet(root, parentPath);
            const modId = store.currentPath[store.currentPath.length - 1];
            const mod = parentSheet?.modules.find((m) => m.id === modId);
            if (mod) {
              const scopedSignalOrders: Record<string, string[]> = {};
              const prefix = (store.currentPath.length === 0
                ? '__root__'
                : store.currentPath.join('/')) + ':';
              for (const [k, order] of Object.entries(store.portSignalOrders)) {
                if (!k.startsWith(prefix)) continue;
                scopedSignalOrders[k.slice(prefix.length)] = order;
              }
              const ports = derivePortsFromModule(mod, scopedSignalOrders);
              for (const port of ports) {
                itemDims.set(port.id, { w: port.bodyWidth, h: port.bodyHeight });
              }
            }
          }
        }
      }

      const matchIds: string[] = [];
      for (const [key, pos] of Object.entries(store.positions)) {
        if (!key.startsWith(prefix)) continue;
        const id = key.slice(prefix.length);
        const dim = itemDims.get(id);

        const px = projectVecRef.current.set(pos.x, pos.y, 0).project(cam);
        if (!Number.isFinite(px.x) || !Number.isFinite(px.y) || px.z < -1 || px.z > 1) continue;
        const centerX = canvasRect.left + ((px.x + 1) * 0.5) * canvasRect.width;
        const centerY = canvasRect.top + ((-px.y + 1) * 0.5) * canvasRect.height;

        if (!dim || dim.w <= 0 || dim.h <= 0) {
          if (
            centerX >= minSelX &&
            centerX <= maxSelX &&
            centerY >= minSelY &&
            centerY <= maxSelY
          ) {
            matchIds.push(id);
          }
          continue;
        }

        const rot = ((pos.rotation || 0) % 360 + 360) % 360;
        const swapped = rot === 90 || rot === 270;
        const w = swapped ? dim.h : dim.w;
        const h = swapped ? dim.w : dim.h;

        const pMin = projectCornerMinRef.current
          .set(pos.x - w / 2, pos.y - h / 2, 0)
          .project(cam);
        const pMax = projectCornerMaxRef.current
          .set(pos.x + w / 2, pos.y + h / 2, 0)
          .project(cam);
        const minX = canvasRect.left + ((Math.min(pMin.x, pMax.x) + 1) * 0.5) * canvasRect.width;
        const maxX = canvasRect.left + ((Math.max(pMin.x, pMax.x) + 1) * 0.5) * canvasRect.width;
        const minY = canvasRect.top + ((-Math.max(pMin.y, pMax.y) + 1) * 0.5) * canvasRect.height;
        const maxY = canvasRect.top + ((-Math.min(pMin.y, pMax.y) + 1) * 0.5) * canvasRect.height;

        const overlap =
          maxX >= minSelX &&
          minX <= maxSelX &&
          maxY >= minSelY &&
          minY <= maxSelY;
        if (overlap) matchIds.push(id);
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
    if (store.portEditMode) {
      store.openContextMenu(e.clientX, e.clientY, 'port');
      return;
    }
    if (store.selectedComponentIds.length === 1) {
      store.openContextMenu(
        e.clientX,
        e.clientY,
        'selection',
        store.selectedComponentIds[0],
      );
      return;
    }
    if (store.selectedComponentIds.length >= 2) {
      store.openContextMenu(e.clientX, e.clientY, 'align');
      return;
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
          if (useSchematicStore.getState().portEditMode) {
            useSchematicStore.getState().closeContextMenu();
            return;
          }
          // Don't clear selection during window-select drag
          if (selDragging.current) return;
          useSchematicStore.getState().selectComponent(null);
          useSchematicStore.getState().selectNet(null);
          useSchematicStore.getState().closeContextMenu();
        }}
      >
        <SceneContent
          theme={theme}
          onSceneReady={handleSceneReady}
        />
      </Canvas>

      {/* Port edit mode dimmer */}
      {portEditMode && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background: 'rgba(6, 8, 14, 0.34)',
            pointerEvents: 'none',
            zIndex: 110,
          }}
        />
      )}

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

      {/* Port edit controls */}
      {portEditMode && (
        <>
          <div
            style={{
              position: 'absolute',
              left: 12,
              top: 12,
              zIndex: 220,
              background: theme.bgSecondary,
              border: `1px solid ${theme.borderColor}`,
              borderRadius: 8,
              padding: '8px 12px',
              color: theme.textPrimary,
              fontSize: 12,
              fontFamily: 'system-ui, -apple-system, sans-serif',
              boxShadow: '0 2px 10px rgba(0,0,0,0.28)',
              pointerEvents: 'auto',
              display: 'flex',
              alignItems: 'center',
              gap: 10,
            }}
          >
            <span>
              {isEditingModulePorts ? 'Editing module ports' : 'Editing port'}{' '}
              <strong>{portEditTargetName}</strong>
            </span>
            <button
              type="button"
              onClick={() => setPortEditMode(false)}
              style={{
                border: `1px solid ${theme.borderColor}`,
                background: theme.bgTertiary,
                color: theme.textPrimary,
                borderRadius: 6,
                fontSize: 12,
                padding: '3px 10px',
                cursor: 'pointer',
                fontFamily: 'inherit',
              }}
            >
              Exit
            </button>
          </div>
          <div
            style={{
              position: 'absolute',
              left: 12,
              top: 54,
              zIndex: 220,
              color: theme.textMuted,
              fontSize: 11,
              fontFamily: 'system-ui, -apple-system, sans-serif',
              pointerEvents: 'none',
            }}
          >
            {isEditingModulePorts
              ? 'Drag pin handles to reorder module ports.'
              : 'Drag pin handles to reorder breakout signals.'}
          </div>
        </>
      )}
    </div>
  );
}
