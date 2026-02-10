/**
 * DraggableComponent — wraps ComponentRenderer with smooth drag handling.
 *
 * Performance architecture:
 * - During drag: position is written to `liveDrag` (shared mutable ref)
 *   and applied directly to the Three.js group via `useFrame`.
 *   No React state updates, no re-renders, no grid snapping.
 * - On drag end: final position is committed to the Zustand store
 *   (grid-snapped), triggering a single batch re-render.
 * - When not dragging: position comes from the committed Zustand store.
 * - Per-component boolean selectors ensure this only re-renders when
 *   THIS component's selected/hovered/dragged state changes, not when
 *   any component's state changes.
 */

import { useRef, useCallback, memo } from 'react';
import { useThree, useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import type { SchematicComponent } from '../types/schematic';
import type { ThemeColors } from '../lib/theme';
import { ComponentRenderer } from './ComponentRenderer';
import {
  useSchematicStore,
  useComponentPosition,
  useIsComponentSelected,
  useIsComponentHovered,
  useIsComponentDragging,
  liveDrag,
} from '../stores/schematicStore';

const DRAG_THRESHOLD = 3; // screen-px before we start dragging

interface Props {
  component: SchematicComponent;
  theme: ThemeColors;
  netsForComponent: Map<string, string>;
  selectedNetId: string | null;
  symbolTuningRevision?: number;
}

export const DraggableComponent = memo(function DraggableComponent({
  component,
  theme,
  netsForComponent,
  selectedNetId,
  symbolTuningRevision = 0,
}: Props) {
  const committedPos = useComponentPosition(component.id);

  // Granular boolean selectors — only re-render when THIS component changes
  const isSelected = useIsComponentSelected(component.id);
  const isHovered = useIsComponentHovered(component.id);
  const isDraggingSelf = useIsComponentDragging(component.id);

  // Actions (stable references from Zustand)
  const startDrag = useSchematicStore((s) => s.startDrag);
  const endDrag = useSchematicStore((s) => s.endDrag);
  const selectComponent = useSchematicStore((s) => s.selectComponent);
  const toggleComponentSelection = useSchematicStore((s) => s.toggleComponentSelection);
  const addToSelection = useSchematicStore((s) => s.addToSelection);
  const hoverComponent = useSchematicStore((s) => s.hoverComponent);
  const openContextMenu = useSchematicStore((s) => s.openContextMenu);

  const { camera, gl } = useThree();
  const groupRef = useRef<THREE.Group>(null);

  // Reusable math objects — zero GC pressure during drag
  const raycaster = useRef(new THREE.Raycaster());
  const zPlane = useRef(new THREE.Plane(new THREE.Vector3(0, 0, 1), 0));
  const worldTarget = useRef(new THREE.Vector3());
  const ndc = useRef(new THREE.Vector2());
  const dragOffset = useRef<{ x: number; y: number } | null>(null);

  /** Project screen coordinates onto the z = 0 world plane. */
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

  // ── useFrame: apply live drag position imperatively ───────────

  useFrame(() => {
    if (!groupRef.current) return;
    if (liveDrag.componentId === component.id) {
      groupRef.current.position.x = liveDrag.x;
      groupRef.current.position.y = liveDrag.y;
    } else if (liveDrag.componentId && liveDrag.groupOffsets[component.id]) {
      // This component is part of a group drag
      const off = liveDrag.groupOffsets[component.id];
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

  // ── Pointer down → start potential drag ──────────────────────

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
      const curPos =
        state.positions[`${pk}:${component.id}`] || { x: 0, y: 0 };
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
          // If not already selected, select (add to selection if shift)
          if (!st.selectedComponentIds.includes(component.id)) {
            if (shiftKey) {
              addToSelection(component.id);
            } else {
              selectComponent(component.id);
            }
          }
          // Populate group offsets for other selected items
          const latestState = useSchematicStore.getState();
          liveDrag.groupOffsets = {};
          for (const otherId of latestState.selectedComponentIds) {
            if (otherId === component.id) continue;
            const otherPos = latestState.positions[`${pk}:${otherId}`] || { x: 0, y: 0 };
            liveDrag.groupOffsets[otherId] = {
              x: otherPos.x - curPos.x,
              y: otherPos.y - curPos.y,
            };
          }
          liveDrag.componentId = component.id;
          liveDrag.x = curPos.x;
          liveDrag.y = curPos.y;
          liveDrag.version++;
          startDrag(component.id);
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
            toggleComponentSelection(component.id);
          } else {
            selectComponent(component.id);
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
    [component.id, screenToWorld, startDrag, endDrag, selectComponent, toggleComponentSelection, addToSelection, gl],
  );

  return (
    <group
      ref={groupRef}
      onPointerDown={handlePointerDown}
      onPointerEnter={() => {
        if (useSchematicStore.getState().portEditMode) {
          if (!useSchematicStore.getState().dragComponentId) {
            gl.domElement.style.cursor = 'not-allowed';
          }
          return;
        }
        hoverComponent(component.id);
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
        const state = useSchematicStore.getState();
        if (
          state.selectedComponentIds.length !== 1
          || state.selectedComponentIds[0] !== component.id
        ) {
          selectComponent(component.id);
        }
        openContextMenu(e.clientX, e.clientY, 'selection', component.id);
      }}
    >
      <ComponentRenderer
        component={component}
        theme={theme}
        isSelected={isSelected}
        isHovered={isHovered}
        isDragging={isDraggingSelf}
        selectedNetId={selectedNetId}
        netsForComponent={netsForComponent}
        rotation={committedPos.rotation}
        mirrorX={committedPos.mirrorX}
        mirrorY={committedPos.mirrorY}
        tuningRevision={symbolTuningRevision}
      />
    </group>
  );
});
