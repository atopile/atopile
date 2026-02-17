/**
 * DraggablePort — wraps PortSymbol with drag handling.
 *
 * Same performance architecture as DraggableComponent:
 * - During drag: position via `liveDrag` + `useFrame` (no React renders)
 * - On drag end: commit to Zustand store (grid-snapped)
 * - Granular selectors for minimal re-renders
 */

import { useRef, useCallback, useMemo, useState, memo } from 'react';
import { useThree, useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import type { SchematicPort } from '../types/schematic';
import { getPortGridAlignmentOffset } from '../types/schematic';
import type { ThemeColors } from '../utils/theme';
import { PortSymbol } from './PortSymbol';
import {
  useSchematicStore,
  useComponentPosition,
  useIsComponentSelected,
  useIsComponentHovered,
  useIsComponentDragging,
  liveDrag,
} from '../stores/schematicStore';

const DRAG_THRESHOLD = 3;

interface Props {
  port: SchematicPort;
  theme: ThemeColors;
  selectedNetId: string | null;
  netId: string | null;
}

function editCursorForSide(side: SchematicPort['side']): string {
  return side === 'top' || side === 'bottom' ? 'ew-resize' : 'ns-resize';
}

function moveSignal(order: string[], from: number, to: number): string[] {
  if (from === to) return order;
  const next = [...order];
  const [item] = next.splice(from, 1);
  next.splice(to, 0, item);
  return next;
}

export const DraggablePort = memo(function DraggablePort({
  port,
  theme,
  selectedNetId,
  netId,
}: Props) {
  const committedPos = useComponentPosition(port.id);
  const isSelected = useIsComponentSelected(port.id);
  const isHovered = useIsComponentHovered(port.id);
  const isDraggingSelf = useIsComponentDragging(port.id);
  const portEditMode = useSchematicStore((s) => s.portEditMode);
  const portEditTargetId = useSchematicStore((s) => s.portEditTargetId);

  const startDrag = useSchematicStore((s) => s.startDrag);
  const endDrag = useSchematicStore((s) => s.endDrag);
  const selectComponent = useSchematicStore((s) => s.selectComponent);
  const toggleComponentSelection = useSchematicStore((s) => s.toggleComponentSelection);
  const addToSelection = useSchematicStore((s) => s.addToSelection);
  const hoverComponent = useSchematicStore((s) => s.hoverComponent);
  const openContextMenu = useSchematicStore((s) => s.openContextMenu);
  const reorderPortSignals = useSchematicStore((s) => s.reorderPortSignals);

  const { camera, gl } = useThree();
  const groupRef = useRef<THREE.Group>(null);
  const signalDragRef = useRef<{
    signal: string;
    startIndex: number;
    targetIndex: number;
  } | null>(null);
  const [hoveredSignal, setHoveredSignal] = useState<string | null>(null);
  const [activeSignal, setActiveSignal] = useState<string | null>(null);
  const [targetSignal, setTargetSignal] = useState<string | null>(null);
  const gridOffset = getPortGridAlignmentOffset(port);
  const handleLocalX = port.pinX + gridOffset.x;
  const handleLocalY = port.pinY + gridOffset.y;
  const handleCursor = editCursorForSide(port.side);
  const isPortEditTarget = !portEditMode || portEditTargetId === port.id;
  const isBreakout = !!port.signals && !!port.signalPins && port.signals.length >= 2;
  const signalHandles = useMemo(() => {
    if (!isBreakout || !port.signals || !port.signalPins) return [];
    return port.signals
      .map((sig) => {
        const pin = port.signalPins?.[sig];
        if (!pin) return null;
        return {
          signal: sig,
          x: pin.x + gridOffset.x,
          y: pin.y + gridOffset.y,
        };
      })
      .filter((h): h is { signal: string; x: number; y: number } => h !== null);
  }, [isBreakout, port.signals, port.signalPins, gridOffset.x, gridOffset.y]);

  const raycaster = useRef(new THREE.Raycaster());
  const zPlane = useRef(new THREE.Plane(new THREE.Vector3(0, 0, 1), 0));
  const worldTarget = useRef(new THREE.Vector3());
  const ndc = useRef(new THREE.Vector2());
  const dragOffset = useRef<{ x: number; y: number } | null>(null);

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

  const nearestSignalIndexFromLocal = useCallback(
    (local: { x: number; y: number }): number => {
      if (!port.signals || !port.signalPins || port.signals.length === 0) return 0;
      const axisValue =
        port.side === 'left' || port.side === 'right' ? local.y : local.x;
      let bestIdx = 0;
      let bestDist = Number.POSITIVE_INFINITY;
      for (let i = 0; i < port.signals.length; i++) {
        const sig = port.signals[i];
        const sp = port.signalPins[sig];
        if (!sp) continue;
        const signalAxis =
          port.side === 'left' || port.side === 'right' ? sp.y + gridOffset.y : sp.x + gridOffset.x;
        const d = Math.abs(signalAxis - axisValue);
        if (d < bestDist) {
          bestDist = d;
          bestIdx = i;
        }
      }
      return bestIdx;
    },
    [port.signals, port.signalPins, port.side, gridOffset.x, gridOffset.y],
  );

  useFrame(() => {
    if (!groupRef.current) return;
    if (liveDrag.componentId === port.id) {
      groupRef.current.position.x = liveDrag.x;
      groupRef.current.position.y = liveDrag.y;
    } else if (liveDrag.componentId && liveDrag.groupOffsets[port.id]) {
      const off = liveDrag.groupOffsets[port.id];
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
      if (
        state.portEditMode &&
        state.portEditTargetId &&
        state.portEditTargetId !== port.id
      ) {
        return;
      }
      const pk =
        state.currentPath.length === 0
          ? '__root__'
          : state.currentPath.join('/');
      const curPos =
        state.positions[`${pk}:${port.id}`] || { x: 0, y: 0 };
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
          liveDrag.groupOffsets = {};
          if (st.portEditMode) {
            selectComponent(port.id);
          } else {
            if (!st.selectedComponentIds.includes(port.id)) {
              if (shiftKey) {
                addToSelection(port.id);
              } else {
                selectComponent(port.id);
              }
            }
            const latestState = useSchematicStore.getState();
            for (const otherId of latestState.selectedComponentIds) {
              if (otherId === port.id) continue;
              const otherPos = latestState.positions[`${pk}:${otherId}`] || { x: 0, y: 0 };
              liveDrag.groupOffsets[otherId] = {
                x: otherPos.x - curPos.x,
                y: otherPos.y - curPos.y,
              };
            }
          }
          liveDrag.componentId = port.id;
          liveDrag.x = curPos.x;
          liveDrag.y = curPos.y;
          liveDrag.version++;
          startDrag(port.id);
          gl.domElement.style.cursor = 'grabbing';
        }

        if (dragOffset.current) {
          const st = useSchematicStore.getState();
          const w = screenToWorld(me.clientX, me.clientY);
          if (st.portEditMode) {
            // In edit mode, constrain dragging to the side axis for reorder clarity.
            if (port.side === 'left' || port.side === 'right') {
              liveDrag.x = curPos.x;
              liveDrag.y = w.y + dragOffset.current.y;
            } else {
              liveDrag.x = w.x + dragOffset.current.x;
              liveDrag.y = curPos.y;
            }
          } else {
            liveDrag.x = w.x + dragOffset.current.x;
            liveDrag.y = w.y + dragOffset.current.y;
          }
          liveDrag.version++;
        }
      };

      const onUp = () => {
        if (!hasDragged) {
          if (shiftKey) {
            toggleComponentSelection(port.id);
          } else {
            selectComponent(port.id);
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
    [
      port.id,
      screenToWorld,
      startDrag,
      endDrag,
      selectComponent,
      toggleComponentSelection,
      addToSelection,
      gl,
    ],
  );

  const handleSignalHandlePointerDown = useCallback(
    (signal: string, e: any) => {
      if (e.button !== 0) return;
      const signals = port.signals;
      if (!portEditMode || !isPortEditTarget || !isBreakout || !signals) return;
      e.stopPropagation();
      selectComponent(port.id);

      const startIdx = signals.indexOf(signal);
      if (startIdx < 0) return;
      signalDragRef.current = {
        signal,
        startIndex: startIdx,
        targetIndex: startIdx,
      };
      setActiveSignal(signal);
      setTargetSignal(signal);
      gl.domElement.style.cursor = handleCursor;

      const onMove = (me: PointerEvent) => {
        const drag = signalDragRef.current;
        if (!drag) return;
        const local = screenToLocal(me.clientX, me.clientY);
        if (!local) return;
        const idx = nearestSignalIndexFromLocal(local);
        drag.targetIndex = idx;
        const sig = signals[idx] ?? signal;
        setTargetSignal(sig);
      };

      const onUp = () => {
        const drag = signalDragRef.current;
        if (drag) {
          const from = drag.startIndex;
          const to = drag.targetIndex;
          if (from !== to) {
            reorderPortSignals(port.id, moveSignal(signals, from, to));
          }
        }
        signalDragRef.current = null;
        setActiveSignal(null);
        setTargetSignal(null);
        if (!useSchematicStore.getState().dragComponentId) {
          gl.domElement.style.cursor = 'default';
        }
        window.removeEventListener('pointermove', onMove);
        window.removeEventListener('pointerup', onUp);
      };

      window.addEventListener('pointermove', onMove);
      window.addEventListener('pointerup', onUp);
    },
    [
      portEditMode,
      isPortEditTarget,
      isBreakout,
      port.signals,
      port.id,
      selectComponent,
      gl,
      handleCursor,
      screenToLocal,
      nearestSignalIndexFromLocal,
      reorderPortSignals,
    ],
  );

  return (
    <group
      ref={groupRef}
      onPointerDown={(e) => {
        if (!portEditMode) {
          handlePointerDown(e);
          return;
        }
        if (!isPortEditTarget) {
          if (e.button !== 0) return;
          e.stopPropagation();
          return;
        }
        // Edit mode: drag starts from the explicit handle only.
        if (e.button !== 0) return;
        e.stopPropagation();
        selectComponent(port.id);
      }}
      onPointerEnter={() => {
        hoverComponent(port.id);
        if (!useSchematicStore.getState().dragComponentId)
          gl.domElement.style.cursor = portEditMode
            ? (isPortEditTarget ? 'default' : 'not-allowed')
            : 'grab';
      }}
      onPointerLeave={() => {
        hoverComponent(null);
        if (!useSchematicStore.getState().dragComponentId)
          gl.domElement.style.cursor = 'auto';
      }}
      onContextMenu={(e) => {
        e.stopPropagation();
        e.nativeEvent.preventDefault();
        openContextMenu(e.clientX, e.clientY, 'port', port.id);
      }}
    >
      <PortSymbol
        port={port}
        theme={theme}
        isSelected={isSelected}
        isHovered={isHovered}
        isDragging={isDraggingSelf}
        selectedNetId={selectedNetId}
        netId={netId}
        rotation={committedPos.rotation}
        mirrorX={committedPos.mirrorX}
        mirrorY={committedPos.mirrorY}
      />

      {portEditMode && isPortEditTarget && isBreakout && signalHandles.map((handle) => {
        const isHoveredHandle = hoveredSignal === handle.signal;
        const isActiveHandle = activeSignal === handle.signal;
        const isTargetHandle = targetSignal === handle.signal;
        const glowOpacity = isActiveHandle ? 0.22 : isTargetHandle ? 0.16 : isHoveredHandle ? 0.12 : 0.07;
        const ringOpacity = isActiveHandle ? 0.88 : isTargetHandle ? 0.74 : isHoveredHandle ? 0.64 : 0.52;
        const coreOpacity = isActiveHandle ? 0.92 : isTargetHandle ? 0.78 : isHoveredHandle ? 0.66 : 0.54;
        const ringColor = isTargetHandle ? theme.accent : theme.textPrimary;
        return (
          <group
            key={`sig-handle-${handle.signal}`}
            position={[handle.x, handle.y, 0.035]}
            onPointerDown={(e) => handleSignalHandlePointerDown(handle.signal, e)}
            onPointerEnter={(e) => {
              e.stopPropagation();
              setHoveredSignal(handle.signal);
              gl.domElement.style.cursor = handleCursor;
            }}
            onPointerLeave={(e) => {
              e.stopPropagation();
              setHoveredSignal((cur) => (cur === handle.signal ? null : cur));
              if (!useSchematicStore.getState().dragComponentId && !signalDragRef.current) {
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

      {portEditMode && isPortEditTarget && !isBreakout && (
        <group
          position={[handleLocalX, handleLocalY, 0.03]}
          onPointerDown={handlePointerDown}
          onPointerEnter={(e) => {
            e.stopPropagation();
            gl.domElement.style.cursor = handleCursor;
          }}
          onPointerLeave={(e) => {
            e.stopPropagation();
            if (!useSchematicStore.getState().dragComponentId) {
              gl.domElement.style.cursor = 'default';
            }
          }}
        >
          <mesh>
            <circleGeometry args={[0.78, 20]} />
            <meshBasicMaterial
              color={theme.accent}
              transparent
              opacity={isHovered || isSelected || isDraggingSelf ? 0.16 : 0.08}
              depthWrite={false}
            />
          </mesh>
          <mesh>
            <ringGeometry args={[0.5, 0.6, 22]} />
            <meshBasicMaterial
              color={theme.textPrimary}
              transparent
              opacity={isHovered || isSelected || isDraggingSelf ? 0.78 : 0.56}
              depthWrite={false}
            />
          </mesh>
          <mesh>
            <circleGeometry args={[0.2, 14]} />
            <meshBasicMaterial
              color={theme.textPrimary}
              transparent
              opacity={0.62}
              depthWrite={false}
            />
          </mesh>
        </group>
      )}
    </group>
  );
});
