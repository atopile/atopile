import { useState, useRef, useCallback } from "react";

/** Hook for a pointer-draggable vertical resize handle. */
export function useResizeHandle(initialHeight: number, minHeight: number) {
  const [height, setHeight] = useState(initialHeight);
  const dragging = useRef(false);
  const startY = useRef(0);
  const startH = useRef(0);

  const onPointerDown = useCallback(
    (e: React.PointerEvent) => {
      dragging.current = true;
      startY.current = e.clientY;
      startH.current = height;
      (e.target as HTMLElement).setPointerCapture(e.pointerId);
    },
    [height]
  );

  const onPointerMove = useCallback(
    (e: React.PointerEvent) => {
      if (!dragging.current) return;
      const delta = startY.current - e.clientY;
      setHeight(Math.max(minHeight, startH.current + delta));
    },
    [minHeight]
  );

  const onPointerUp = useCallback(() => {
    dragging.current = false;
  }, []);

  return { height, onPointerDown, onPointerMove, onPointerUp };
}
