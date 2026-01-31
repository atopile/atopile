/**
 * Tooltip component for showing detailed node/edge information on hover.
 *
 * Follows the cursor and displays contextual information about
 * the currently hovered graph element. Can be locked by clicking.
 */

import { useEffect, useState, useCallback } from 'react';
import { useSelectionStore } from '../stores/selectionStore';
import { useGraphStore } from '../stores/graphStore';

interface TooltipPosition {
  x: number;
  y: number;
}

export function Tooltip() {
  const { hoveredNode, lockedTooltipNode, lockTooltip } = useSelectionStore();
  const { data, index, positions } = useGraphStore();
  const [mousePosition, setMousePosition] = useState<TooltipPosition>({ x: 0, y: 0 });
  const [visible, setVisible] = useState(false);

  // The node to show in tooltip: locked node takes priority over hovered
  const displayNode = lockedTooltipNode ?? hoveredNode;
  const isLocked = lockedTooltipNode !== null;

  // Track mouse position
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      setMousePosition({ x: e.clientX + 16, y: e.clientY + 16 });
    };

    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  // Show/hide tooltip with delay (only for non-locked state)
  useEffect(() => {
    if (displayNode) {
      if (isLocked) {
        setVisible(true);
      } else {
        const timer = setTimeout(() => setVisible(true), 200);
        return () => clearTimeout(timer);
      }
    } else {
      setVisible(false);
    }
  }, [displayNode, isLocked]);

  // Handle click to lock/unlock
  const handleClick = useCallback(() => {
    if (hoveredNode) {
      lockTooltip(hoveredNode);
    } else if (isLocked) {
      lockTooltip(null);
    }
  }, [hoveredNode, isLocked, lockTooltip]);

  // Handle escape to unlock
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isLocked) {
        lockTooltip(null);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isLocked, lockTooltip]);

  if (!visible || !displayNode || !data || !index) {
    return null;
  }

  const node = index.nodesById.get(displayNode);
  if (!node) {
    return null;
  }

  // Get additional info
  const children = index.childrenByParent.get(displayNode);
  const childCount = children?.size ?? 0;
  const outgoing = index.outgoingEdges.get(displayNode);
  const edgeCounts: Record<string, number> = {};

  if (outgoing) {
    for (const [edgeType, edges] of outgoing.entries()) {
      edgeCounts[edgeType] = edges.length;
    }
  }

  // Get node position for locked tooltip
  const nodePos = positions.get(displayNode);

  // Determine tooltip position
  let tooltipX = mousePosition.x;
  let tooltipY = mousePosition.y;

  // For locked tooltips, try to position near the node (right side)
  if (isLocked && nodePos) {
    // Just use mouse position but make it sticky
    tooltipX = Math.min(mousePosition.x, window.innerWidth - 320);
    tooltipY = Math.min(mousePosition.y, window.innerHeight - 300);
  }

  // Keep tooltip on screen (z-index very high to be above Three.js Html labels)
  const tooltipStyle: React.CSSProperties = {
    position: 'fixed',
    left: Math.min(tooltipX, window.innerWidth - 320),
    top: Math.min(tooltipY, window.innerHeight - 300),
    zIndex: 10000,
    pointerEvents: isLocked ? 'auto' : 'none',
  };

  return (
    <div style={tooltipStyle} onClick={isLocked ? undefined : handleClick}>
      <div
        className={`bg-gray-900/95 backdrop-blur-sm border rounded-lg shadow-xl p-3 min-w-[220px] max-w-[300px] ${
          isLocked ? 'border-accent' : 'border-gray-700'
        }`}
      >
        {/* Lock indicator and close button */}
        {isLocked && (
          <div className="flex items-center justify-between mb-2 pb-2 border-b border-gray-700">
            <div className="flex items-center gap-1.5 text-[10px] text-accent">
              <span>📌</span>
              <span>Locked</span>
            </div>
            <button
              onClick={() => lockTooltip(null)}
              className="text-gray-500 hover:text-white transition-colors text-xs px-1"
            >
              ✕
            </button>
          </div>
        )}

        {/* Header */}
        <div className="flex items-center gap-2 mb-2 pb-2 border-b border-gray-700">
          <div
            className="w-3 h-3 rounded-full flex-shrink-0"
            style={{ backgroundColor: getTypeColor(node.typeName) }}
          />
          <span className="font-medium text-white truncate">
            {node.name || node.typeName || 'Unknown'}
          </span>
        </div>

        {/* Type */}
        {node.typeName && (
          <div className="flex justify-between text-xs mb-1">
            <span className="text-gray-400">Type</span>
            <span className="text-gray-200 truncate ml-2">{node.typeName}</span>
          </div>
        )}

        {/* ID */}
        <div className="flex justify-between text-xs mb-1">
          <span className="text-gray-400">ID</span>
          <span className="text-gray-200 font-mono text-[10px]">{node.id}</span>
        </div>

        {/* Depth */}
        <div className="flex justify-between text-xs mb-1">
          <span className="text-gray-400">Depth</span>
          <span className="text-gray-200">{node.depth}</span>
        </div>

        {/* Children */}
        {childCount > 0 && (
          <div className="flex justify-between text-xs mb-1">
            <span className="text-gray-400">Children</span>
            <span className="text-gray-200">{childCount}</span>
          </div>
        )}

        {/* Traits - show ALL */}
        {node.traits.length > 0 && (
          <div className="mt-2 pt-2 border-t border-gray-700">
            <div className="text-xs text-gray-400 mb-1">
              Traits ({node.traits.length})
            </div>
            <div className="flex flex-wrap gap-1 max-h-24 overflow-y-auto">
              {node.traits.map((trait) => (
                <span
                  key={trait}
                  className="px-1.5 py-0.5 text-[10px] bg-gray-700 text-gray-300 rounded"
                >
                  {trait}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Edges - show ALL */}
        {Object.keys(edgeCounts).length > 0 && (
          <div className="mt-2 pt-2 border-t border-gray-700">
            <div className="text-xs text-gray-400 mb-1">Outgoing Edges</div>
            <div className="grid grid-cols-2 gap-x-2 gap-y-0.5 text-[10px]">
              {Object.entries(edgeCounts)
                .filter(([_, count]) => count > 0)
                .sort((a, b) => b[1] - a[1])
                .map(([type, count]) => (
                  <div key={type} className="flex justify-between">
                    <span className="text-gray-400">{type}</span>
                    <span className="text-gray-300">{count}</span>
                  </div>
                ))}
            </div>
          </div>
        )}

        {/* Attributes if available */}
        {Object.keys(node.attributes).length > 0 && (
          <div className="mt-2 pt-2 border-t border-gray-700">
            <div className="text-xs text-gray-400 mb-1">Attributes</div>
            <div className="space-y-0.5 text-[10px] max-h-20 overflow-y-auto">
              {Object.entries(node.attributes).map(([key, value]) => (
                <div key={key} className="flex justify-between">
                  <span className="text-gray-400">{key}</span>
                  <span className="text-gray-300 truncate ml-2 max-w-[120px]">
                    {String(value)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Hint */}
        <div className="mt-2 pt-2 border-t border-gray-700 text-[10px] text-gray-500">
          {isLocked ? (
            'Press Esc or click × to unlock'
          ) : (
            'Click to lock • Double-click to focus'
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * Get color for node type (simplified version).
 */
function getTypeColor(typeName: string | null): string {
  const colors: Record<string, string> = {
    Resistor: '#22c55e',
    Capacitor: '#3b82f6',
    Inductor: '#a855f7',
    LED: '#eab308',
    Diode: '#f97316',
    Electrical: '#06b6d4',
    ElectricPower: '#ef4444',
    ElectricLogic: '#8b5cf6',
    I2C: '#ec4899',
    SPI: '#f43f5e',
    UART: '#84cc16',
    USB: '#6366f1',
  };

  if (!typeName) return '#9ca3af';

  // Try exact match
  if (colors[typeName]) return colors[typeName];

  // Try partial match
  for (const [key, color] of Object.entries(colors)) {
    if (typeName.includes(key)) return color;
  }

  return '#9ca3af';
}
