/**
 * DraggablePowerPort — wraps PowerPortSymbol with drag handling.
 *
 * Same pattern as DraggablePort / DraggableComponent.
 */

import { useRef, useCallback, memo } from 'react';
import { useThree, useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import type { SchematicPowerPort } from '../types/schematic';
import type { ThemeColors } from '../lib/theme';
import { PowerPortSymbol } from './PowerPortSymbol';
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
  powerPort: SchematicPowerPort;
  theme: ThemeColors;
  selectedNetId: string | null;
}

export const DraggablePowerPort = memo(function DraggablePowerPort({
  powerPort,
  theme,
  selectedNetId,
}: Props) {
  const committedPos = useComponentPosition(powerPort.id);
  const isSelected = useIsComponentSelected(powerPort.id);
  const isHovered = useIsComponentHovered(powerPort.id);
  const isDraggingSelf = useIsComponentDragging(powerPort.id);

  const startDrag = useSchematicStore((s) => s.startDrag);
  const endDrag = useSchematicStore((s) => s.endDrag);
  const selectComponent = useSchematicStore((s) => s.selectComponent);
  const toggleComponentSelection = useSchematicStore((s) => s.toggleComponentSelection);
  const addToSelection = useSchematicStore((s) => s.addToSelection);
  const hoverComponent = useSchematicStore((s) => s.hoverComponent);

  const { camera, gl } = useThree();
  const groupRef = useRef<THREE.Group>(null);

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

  useFrame(() => {
    if (!groupRef.current) return;
    if (liveDrag.componentId === powerPort.id) {
      groupRef.current.position.x = liveDrag.x;
      groupRef.current.position.y = liveDrag.y;
    } else if (liveDrag.componentId && liveDrag.groupOffsets[powerPort.id]) {
      const off = liveDrag.groupOffsets[powerPort.id];
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
      const pk =
        state.currentPath.length === 0
          ? '__root__'
          : state.currentPath.join('/');
      const curPos =
        state.positions[`${pk}:${powerPort.id}`] || { x: 0, y: 0 };
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
          if (!st.selectedComponentIds.includes(powerPort.id)) {
            if (shiftKey) {
              addToSelection(powerPort.id);
            } else {
              selectComponent(powerPort.id);
            }
          }
          const latestState = useSchematicStore.getState();
          liveDrag.groupOffsets = {};
          for (const otherId of latestState.selectedComponentIds) {
            if (otherId === powerPort.id) continue;
            const otherPos = latestState.positions[`${pk}:${otherId}`] || { x: 0, y: 0 };
            liveDrag.groupOffsets[otherId] = {
              x: otherPos.x - curPos.x,
              y: otherPos.y - curPos.y,
            };
          }
          liveDrag.componentId = powerPort.id;
          liveDrag.x = curPos.x;
          liveDrag.y = curPos.y;
          liveDrag.version++;
          startDrag(powerPort.id);
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
            toggleComponentSelection(powerPort.id);
          } else {
            selectComponent(powerPort.id);
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
    [powerPort.id, screenToWorld, startDrag, endDrag, selectComponent, toggleComponentSelection, addToSelection, gl],
  );

  return (
    <group
      ref={groupRef}
      onPointerDown={handlePointerDown}
      onPointerEnter={() => {
        hoverComponent(powerPort.id);
        if (!useSchematicStore.getState().dragComponentId)
          gl.domElement.style.cursor = 'grab';
      }}
      onPointerLeave={() => {
        hoverComponent(null);
        if (!useSchematicStore.getState().dragComponentId)
          gl.domElement.style.cursor = 'auto';
      }}
    >
      <PowerPortSymbol
        powerPort={powerPort}
        theme={theme}
        isSelected={isSelected}
        isHovered={isHovered}
        isDragging={isDraggingSelf}
        selectedNetId={selectedNetId}
      />
    </group>
  );
});
