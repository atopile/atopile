/**
 * Minimap component for graph navigation overview.
 *
 * Shows a small 2D overview of the entire graph with the current
 * viewport highlighted. Clicking navigates to that location.
 */

import { useCallback, useMemo, useRef } from 'react';
import { useGraphStore } from '../stores/graphStore';
import { useViewStore } from '../stores/viewStore';
import { useFilterStore } from '../stores/filterStore';
import { useCollapseStore } from '../stores/collapseStore';
import { computeVisibleNodes } from '../lib/filterEngine';

const MINIMAP_SIZE = 140;
const MINIMAP_PADDING = 10;

export function Minimap() {
  const { data, index, positions, bounds } = useGraphStore();
  const { animateTo, zoom, center } = useViewStore();
  const { config } = useFilterStore();
  const { state: collapseState } = useCollapseStore();
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // Compute visible nodes
  const visibleNodes = useMemo(() => {
    if (!data || !index) return new Set<string>();
    return computeVisibleNodes(data, index, config, collapseState);
  }, [data, index, config, collapseState]);

  // Calculate scale factor
  const scale = useMemo(() => {
    const width = bounds.maxX - bounds.minX || 1;
    const height = bounds.maxY - bounds.minY || 1;
    const maxDim = Math.max(width, height);
    return (MINIMAP_SIZE - MINIMAP_PADDING * 2) / maxDim;
  }, [bounds]);

  // Convert world coordinates to minimap coordinates
  const worldToMinimap = useCallback(
    (x: number, y: number): [number, number] => {
      const mx = MINIMAP_PADDING + (x - bounds.minX) * scale;
      const my = MINIMAP_PADDING + (y - bounds.minY) * scale;
      return [mx, my];
    },
    [bounds, scale]
  );

  // Convert minimap coordinates to world coordinates
  const minimapToWorld = useCallback(
    (mx: number, my: number): [number, number] => {
      const x = bounds.minX + (mx - MINIMAP_PADDING) / scale;
      const y = bounds.minY + (my - MINIMAP_PADDING) / scale;
      return [x, y];
    },
    [bounds, scale]
  );

  // Handle click to navigate
  const handleClick = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const rect = canvasRef.current?.getBoundingClientRect();
      if (!rect) return;

      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;
      const [worldX, worldY] = minimapToWorld(mx, my);

      // Calculate camera distance based on current zoom
      const cameraZ = 500 / zoom;

      animateTo({
        position: { x: worldX, y: worldY, z: cameraZ },
        lookAt: { x: worldX, y: worldY, z: 0 },
      });
    },
    [minimapToWorld, animateTo, zoom]
  );

  // Draw minimap
  const drawMinimap = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || !data) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Clear
    ctx.fillStyle = '#0f172a';
    ctx.fillRect(0, 0, MINIMAP_SIZE, MINIMAP_SIZE);

    // Draw border
    ctx.strokeStyle = '#334155';
    ctx.lineWidth = 1;
    ctx.strokeRect(0.5, 0.5, MINIMAP_SIZE - 1, MINIMAP_SIZE - 1);

    // Draw nodes
    for (const nodeId of visibleNodes) {
      const pos = positions.get(nodeId);
      if (!pos) continue;

      const [mx, my] = worldToMinimap(pos.x, pos.y);

      // Clip to bounds
      if (mx < 0 || mx > MINIMAP_SIZE || my < 0 || my > MINIMAP_SIZE) continue;

      ctx.fillStyle = '#64748b';
      ctx.beginPath();
      ctx.arc(mx, my, 1, 0, Math.PI * 2);
      ctx.fill();
    }

    // Draw viewport indicator
    const viewportSize = 500 / zoom;
    const [vx1, vy1] = worldToMinimap(
      center.x - viewportSize / 2,
      center.y - viewportSize / 2
    );
    const [vx2, vy2] = worldToMinimap(
      center.x + viewportSize / 2,
      center.y + viewportSize / 2
    );

    ctx.strokeStyle = '#3b82f6';
    ctx.lineWidth = 1.5;
    ctx.strokeRect(vx1, vy1, vx2 - vx1, vy2 - vy1);
  }, [data, positions, visibleNodes, worldToMinimap, zoom, center]);

  // Redraw when dependencies change
  useMemo(() => {
    // Use requestAnimationFrame for smoother updates
    requestAnimationFrame(drawMinimap);
  }, [drawMinimap]);

  if (!data || visibleNodes.size === 0) {
    return null;
  }

  return (
    <div className="absolute bottom-4 right-4 z-40">
      <div className="bg-panel-bg/90 backdrop-blur-sm border border-panel-border rounded-lg overflow-hidden shadow-lg">
        <canvas
          ref={canvasRef}
          width={MINIMAP_SIZE}
          height={MINIMAP_SIZE}
          onClick={handleClick}
          className="cursor-crosshair"
          title="Click to navigate"
        />
      </div>
    </div>
  );
}
