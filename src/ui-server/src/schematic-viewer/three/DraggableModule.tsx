/**
 * DraggableModule — wraps ModuleBlock with drag + double-click-to-enter.
 *
 * Same performance architecture as DraggableComponent:
 * - Imperative position updates via liveDrag + useFrame
 * - Per-component boolean selectors
 * - Double-click navigates into the module's sheet
 */

import { useRef, useCallback, useMemo, useState, memo } from 'react';
import { useThree, useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import type { SchematicModule } from '../types/schematic';
import type { ThemeColors } from '../lib/theme';
import { ModuleBlock } from './ModuleBlock';
import {
  useSchematicStore,
  useComponentPosition,
  useIsComponentSelected,
  useIsComponentHovered,
  useIsComponentDragging,
  liveDrag,
} from '../stores/schematicStore';
import {
  getModuleGridOffsetFromPins,
  getOrderedModuleInterfacePins,
  modulePinOrderKey,
  sortInterfacePinsForSide,
} from '../lib/moduleInterfaces';

const DRAG_THRESHOLD = 3;

interface Props {
  module: SchematicModule;
  theme: ThemeColors;
  netsForModule: Map<string, string>;
  selectedNetId: string | null;
}

export const DraggableModule = memo(function DraggableModule({
  module,
  theme,
  netsForModule,
  selectedNetId,
}: Props) {
  const committedPos = useComponentPosition(module.id);
  const currentPath = useSchematicStore((s) => s.currentPath);
  const isSelected = useIsComponentSelected(module.id);
  const isHovered = useIsComponentHovered(module.id);
  const isDraggingSelf = useIsComponentDragging(module.id);
  const portEditMode = useSchematicStore((s) => s.portEditMode);
  const portEditTargetId = useSchematicStore((s) => s.portEditTargetId);
  const orderKey = useMemo(
    () => modulePinOrderKey(currentPath, module.id),
    [currentPath, module.id],
  );
  const pinOrderOverride = useSchematicStore((s) => s.portSignalOrders[orderKey] ?? null);

  const startDrag = useSchematicStore((s) => s.startDrag);
  const endDrag = useSchematicStore((s) => s.endDrag);
  const selectComponent = useSchematicStore((s) => s.selectComponent);
  const toggleComponentSelection = useSchematicStore((s) => s.toggleComponentSelection);
  const addToSelection = useSchematicStore((s) => s.addToSelection);
  const hoverComponent = useSchematicStore((s) => s.hoverComponent);
  const navigateInto = useSchematicStore((s) => s.navigateInto);
  const openContextMenu = useSchematicStore((s) => s.openContextMenu);
  const reorderModulePins = useSchematicStore((s) => s.reorderModulePins);

  const { camera, gl } = useThree();
  const groupRef = useRef<THREE.Group>(null);
  const pinDragRef = useRef<{
    pinId: string;
    side: string;
    startIndex: number;
    targetIndex: number;
  } | null>(null);
  const [hoveredPinId, setHoveredPinId] = useState<string | null>(null);
  const [activePinId, setActivePinId] = useState<string | null>(null);
  const [targetPinId, setTargetPinId] = useState<string | null>(null);

  const raycaster = useRef(new THREE.Raycaster());
  const zPlane = useRef(new THREE.Plane(new THREE.Vector3(0, 0, 1), 0));
  const worldTarget = useRef(new THREE.Vector3());
  const ndc = useRef(new THREE.Vector2());
  const dragOffset = useRef<{ x: number; y: number } | null>(null);
  const isModuleEditTarget = portEditMode && portEditTargetId === module.id;

  const interfacePins = useMemo(
    () => getOrderedModuleInterfacePins(module, pinOrderOverride ?? undefined),
    [module, pinOrderOverride],
  );
  const moduleGridOffset = useMemo(
    () => getModuleGridOffsetFromPins(interfacePins),
    [interfacePins],
  );
  const pinById = useMemo(
    () => new Map(interfacePins.map((pin) => [pin.id, pin])),
    [interfacePins],
  );
  const orderedPinsBySide = useMemo(() => {
    const out = new Map<string, string[]>();
    for (const side of ['left', 'right', 'top', 'bottom'] as const) {
      const sidePins = sortInterfacePinsForSide(
        interfacePins.filter((pin) => pin.side === side),
        side,
      );
      out.set(side, sidePins.map((pin) => pin.id));
    }
    return out;
  }, [interfacePins]);
  const pinsBySideId = useMemo(() => {
    const out = new Map<string, Set<string>>();
    for (const [side, ids] of orderedPinsBySide.entries()) {
      out.set(side, new Set(ids));
    }
    return out;
  }, [orderedPinsBySide]);

  const screenToWorld = useCallback(
    (clientX: number, clientY: number) => {
      const rect = gl.domElement.getBoundingClientRect();
      ndc.current.set(
        ((clientX - rect.left) / rect.width) * 2 - 1,
        -((clientY - rect.top) / rect.height) * 2 + 1,
      );
      raycaster.current.setFromCamera(ndc.current, camera);
      const hit = raycaster.current.ray.intersectPlane(
        zPlane.current,
        worldTarget.current,
      );
      return hit
        ? { x: worldTarget.current.x, y: worldTarget.current.y }
        : { x: 0, y: 0 };
    },
    [camera, gl],
  );
  const screenToLocal = useCallback(
    (clientX: number, clientY: number): { x: number; y: number } | null => {
      const world = screenToWorld(clientX, clientY);
      if (!groupRef.current) return null;
      const local = groupRef.current.worldToLocal(
        new THREE.Vector3(world.x, world.y, 0),
      );
      return { x: local.x, y: local.y };
    },
    [screenToWorld],
  );

  const nearestPinIndexForSide = useCallback(
    (side: string, local: { x: number; y: number }): number => {
      const orderedIds = orderedPinsBySide.get(side) ?? [];
      if (orderedIds.length === 0) return 0;
      const axis =
        side === 'left' || side === 'right'
          ? local.y - moduleGridOffset.y
          : local.x - moduleGridOffset.x;
      let bestIdx = 0;
      let bestDist = Number.POSITIVE_INFINITY;
      for (let i = 0; i < orderedIds.length; i++) {
        const pin = pinById.get(orderedIds[i]);
        if (!pin) continue;
        const pinAxis = side === 'left' || side === 'right' ? pin.y : pin.x;
        const d = Math.abs(pinAxis - axis);
        if (d < bestDist) {
          bestDist = d;
          bestIdx = i;
        }
      }
      return bestIdx;
    },
    [orderedPinsBySide, pinById, moduleGridOffset.x, moduleGridOffset.y],
  );

  useFrame(() => {
    if (!groupRef.current) return;
    if (liveDrag.componentId === module.id) {
      groupRef.current.position.x = liveDrag.x;
      groupRef.current.position.y = liveDrag.y;
    } else if (liveDrag.componentId && liveDrag.groupOffsets[module.id]) {
      const off = liveDrag.groupOffsets[module.id];
      groupRef.current.position.x = liveDrag.x + off.x;
      groupRef.current.position.y = liveDrag.y + off.y;
    } else {
      groupRef.current.position.x = committedPos.x;
      groupRef.current.position.y = committedPos.y;
    }
    const rot = (committedPos.rotation || 0) * (Math.PI / 180);
    groupRef.current.rotation.z = rot;
    groupRef.current.scale.x = committedPos.mirrorX ? -1 : 1;
    groupRef.current.scale.y = committedPos.mirrorY ? -1 : 1;
  });

  const handlePointerDown = useCallback(
    (e: any) => {
      if (e.button !== 0) return;
      e.stopPropagation();

      const shiftKey = !!(e.nativeEvent?.shiftKey ?? e.shiftKey);
      const startX = (e.nativeEvent?.clientX ?? e.clientX) as number;
      const startY = (e.nativeEvent?.clientY ?? e.clientY) as number;

      const state = useSchematicStore.getState();
      if (state.portEditMode) return;
      const pk = state.currentPath.length === 0
        ? '__root__'
        : state.currentPath.join('/');
      const curPos = state.positions[`${pk}:${module.id}`] || { x: 0, y: 0 };
      const world0 = screenToWorld(startX, startY);
      dragOffset.current = {
        x: curPos.x - world0.x,
        y: curPos.y - world0.y,
      };

      let hasDragged = false;

      const onMove = (me: PointerEvent) => {
        const dx = me.clientX - startX;
        const dy = me.clientY - startY;
        if (!hasDragged && Math.sqrt(dx * dx + dy * dy) < DRAG_THRESHOLD)
          return;

        if (!hasDragged) {
          hasDragged = true;
          const st = useSchematicStore.getState();
          if (!st.selectedComponentIds.includes(module.id)) {
            if (shiftKey) {
              addToSelection(module.id);
            } else {
              selectComponent(module.id);
            }
          }
          const latestState = useSchematicStore.getState();
          liveDrag.groupOffsets = {};
          for (const otherId of latestState.selectedComponentIds) {
            if (otherId === module.id) continue;
            const otherPos = latestState.positions[`${pk}:${otherId}`] || { x: 0, y: 0 };
            liveDrag.groupOffsets[otherId] = {
              x: otherPos.x - curPos.x,
              y: otherPos.y - curPos.y,
            };
          }
          liveDrag.componentId = module.id;
          liveDrag.x = curPos.x;
          liveDrag.y = curPos.y;
          liveDrag.version++;
          startDrag(module.id);
          gl.domElement.style.cursor = 'grabbing';
        }

        if (dragOffset.current) {
          const w = screenToWorld(me.clientX, me.clientY);
          liveDrag.x = w.x + dragOffset.current.x;
          liveDrag.y = w.y + dragOffset.current.y;
          liveDrag.version++;
        }
      };

      const onUp = () => {
        if (!hasDragged) {
          if (shiftKey) {
            toggleComponentSelection(module.id);
          } else {
            selectComponent(module.id);
          }
        } else {
          endDrag();
        }
        dragOffset.current = null;
        gl.domElement.style.cursor = 'auto';
        window.removeEventListener('pointermove', onMove);
        window.removeEventListener('pointerup', onUp);
      };

      window.addEventListener('pointermove', onMove);
      window.addEventListener('pointerup', onUp);
    },
    [module.id, screenToWorld, startDrag, endDrag, selectComponent, toggleComponentSelection, addToSelection, gl],
  );

  const moveItem = useCallback((order: string[], from: number, to: number): string[] => {
    if (from === to) return order;
    const next = [...order];
    const [item] = next.splice(from, 1);
    next.splice(to, 0, item);
    return next;
  }, []);

  const handlePinHandlePointerDown = useCallback((pinId: string, e: any) => {
    if (e.button !== 0) return;
    if (!isModuleEditTarget) return;
    e.stopPropagation();
    selectComponent(module.id);

    const pin = pinById.get(pinId);
    if (!pin) return;
    const side = pin.side;
    const sideOrder = orderedPinsBySide.get(side) ?? [];
    const startIndex = sideOrder.indexOf(pinId);
    if (startIndex < 0) return;

    pinDragRef.current = {
      pinId,
      side,
      startIndex,
      targetIndex: startIndex,
    };
    setActivePinId(pinId);
    setTargetPinId(pinId);
    gl.domElement.style.cursor = side === 'top' || side === 'bottom' ? 'ew-resize' : 'ns-resize';

    const onMove = (me: PointerEvent) => {
      const drag = pinDragRef.current;
      if (!drag) return;
      const local = screenToLocal(me.clientX, me.clientY);
      if (!local) return;
      const idx = nearestPinIndexForSide(drag.side, local);
      drag.targetIndex = idx;
      const ids = orderedPinsBySide.get(drag.side) ?? [];
      setTargetPinId(ids[idx] ?? drag.pinId);
    };

    const onUp = () => {
      const drag = pinDragRef.current;
      if (drag && drag.startIndex !== drag.targetIndex) {
        const baseOrder = interfacePins.map((p) => p.id);
        const sideIds = orderedPinsBySide.get(drag.side) ?? [];
        const movedSideIds = moveItem(sideIds, drag.startIndex, drag.targetIndex);
        const sideSet = pinsBySideId.get(drag.side) ?? new Set<string>();
        let sideIdx = 0;
        const nextOrder = baseOrder.map((id) => {
          if (!sideSet.has(id)) return id;
          const nextId = movedSideIds[sideIdx];
          sideIdx++;
          return nextId ?? id;
        });
        reorderModulePins(module.id, nextOrder);
      }
      pinDragRef.current = null;
      setActivePinId(null);
      setTargetPinId(null);
      if (!useSchematicStore.getState().dragComponentId) {
        gl.domElement.style.cursor = 'default';
      }
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
    };

    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
  }, [
    isModuleEditTarget,
    selectComponent,
    module.id,
    pinById,
    orderedPinsBySide,
    gl,
    screenToLocal,
    nearestPinIndexForSide,
    interfacePins,
    moveItem,
    pinsBySideId,
    reorderModulePins,
  ]);

  const handleDoubleClick = useCallback(
    (e: any) => {
      if (useSchematicStore.getState().portEditMode) return;
      e.stopPropagation();
      navigateInto(module.id);
    },
    [module.id, navigateInto],
  );

  return (
    <group
      ref={groupRef}
      onPointerDown={(e) => {
        if (portEditMode) {
          e.stopPropagation();
          if (isModuleEditTarget) {
            selectComponent(module.id);
          }
          return;
        }
        handlePointerDown(e);
      }}
      onDoubleClick={handleDoubleClick}
      onPointerEnter={() => {
        if (portEditMode) {
          if (!useSchematicStore.getState().dragComponentId) {
            gl.domElement.style.cursor = isModuleEditTarget ? 'default' : 'not-allowed';
          }
          return;
        }
        hoverComponent(module.id);
        if (!useSchematicStore.getState().dragComponentId)
          gl.domElement.style.cursor = 'grab';
      }}
      onPointerLeave={() => {
        hoverComponent(null);
        if (!useSchematicStore.getState().dragComponentId)
          gl.domElement.style.cursor = 'auto';
      }}
      onContextMenu={(e) => {
        e.stopPropagation();
        e.nativeEvent.preventDefault();
        openContextMenu(e.clientX, e.clientY, 'port', module.id);
      }}
    >
      <ModuleBlock
        module={module}
        theme={theme}
        isSelected={isSelected}
        isHovered={isHovered}
        isDragging={isDraggingSelf}
        selectedNetId={selectedNetId}
        netsForModule={netsForModule}
        pinOrderOverride={pinOrderOverride}
        rotation={committedPos.rotation}
        mirrorX={committedPos.mirrorX}
        mirrorY={committedPos.mirrorY}
      />

      {isModuleEditTarget && interfacePins.map((pin) => {
        const isHoveredPin = hoveredPinId === pin.id;
        const isActivePin = activePinId === pin.id;
        const isTargetPin = targetPinId === pin.id;
        const glowOpacity = isActivePin ? 0.22 : isTargetPin ? 0.16 : isHoveredPin ? 0.12 : 0.07;
        const ringOpacity = isActivePin ? 0.88 : isTargetPin ? 0.74 : isHoveredPin ? 0.64 : 0.52;
        const coreOpacity = isActivePin ? 0.92 : isTargetPin ? 0.78 : isHoveredPin ? 0.66 : 0.54;
        const ringColor = isTargetPin ? theme.accent : theme.textPrimary;
        const cursor = pin.side === 'top' || pin.side === 'bottom' ? 'ew-resize' : 'ns-resize';
        return (
          <group
            key={`module-pin-${module.id}-${pin.id}`}
            position={[moduleGridOffset.x + pin.x, moduleGridOffset.y + pin.y, 0.04]}
            onPointerDown={(e) => handlePinHandlePointerDown(pin.id, e)}
            onPointerEnter={(e) => {
              e.stopPropagation();
              setHoveredPinId(pin.id);
              gl.domElement.style.cursor = cursor;
            }}
            onPointerLeave={(e) => {
              e.stopPropagation();
              setHoveredPinId((cur) => (cur === pin.id ? null : cur));
              if (!useSchematicStore.getState().dragComponentId && !pinDragRef.current) {
                gl.domElement.style.cursor = 'default';
              }
            }}
          >
            <mesh>
              <circleGeometry args={[0.74, 20]} />
              <meshBasicMaterial
                color={theme.accent}
                transparent
                opacity={glowOpacity}
                depthWrite={false}
              />
            </mesh>
            <mesh>
              <ringGeometry args={[0.46, 0.56, 22]} />
              <meshBasicMaterial
                color={ringColor}
                transparent
                opacity={ringOpacity}
                depthWrite={false}
              />
            </mesh>
            <mesh>
              <circleGeometry args={[0.18, 14]} />
              <meshBasicMaterial
                color={ringColor}
                transparent
                opacity={coreOpacity}
                depthWrite={false}
              />
            </mesh>
          </group>
        );
      })}
    </group>
  );
});
