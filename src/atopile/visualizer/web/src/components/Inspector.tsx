/**
 * Inspector panel for viewing node details.
 *
 * Shows properties, traits, attributes, and connected edges
 * for the currently selected or hovered node.
 */

import { useMemo, useCallback, useState } from 'react';
import { useGraphStore } from '../stores/graphStore';
import { useSelectionStore } from '../stores/selectionStore';
import { useCollapseStore } from '../stores/collapseStore';
import { useViewStore } from '../stores/viewStore';
import { useFilterStore } from '../stores/filterStore';
import { useNavigationStore } from '../stores/navigationStore';
import { computeVisibleNodesWithNavigation, computeVisibleEdges } from '../lib/filterEngine';
import type { EdgeTypeKey, GraphEdge } from '../types/graph';

const EDGE_TYPE_COLORS: Record<EdgeTypeKey, string> = {
  composition: 'text-green-400',
  trait: 'text-purple-400',
  pointer: 'text-orange-400',
  connection: 'text-blue-400',
  operand: 'text-red-400',
  type: 'text-gray-400',
  next: 'text-amber-700',
};

const NODE_TYPE_COLORS: Record<string, string> = {
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
  default: '#9ca3af',
};

function getNodeColor(typeName: string | null): string {
  if (!typeName) return NODE_TYPE_COLORS.default;
  if (NODE_TYPE_COLORS[typeName]) return NODE_TYPE_COLORS[typeName];
  for (const [key, color] of Object.entries(NODE_TYPE_COLORS)) {
    if (typeName.includes(key)) return color;
  }
  return NODE_TYPE_COLORS.default;
}

export function Inspector() {
  const { data, index, positions } = useGraphStore();
  const { selectedNodes, hoveredNode, setFocusedNode } = useSelectionStore();
  const { state: collapseState } = useCollapseStore();
  const { animateTo } = useViewStore();
  const { config: filterConfig } = useFilterStore();
  const { currentRootId, viewDepth, depthEnabled, navigateTo } = useNavigationStore();
  const [copiedId, setCopiedId] = useState(false);
  const [edgeSearch, setEdgeSearch] = useState('');
  const [showHidden, setShowHidden] = useState(false);

  // Get the node to inspect (hovered takes priority, then first selected)
  const inspectedNodeId = hoveredNode || Array.from(selectedNodes)[0] || null;
  const inspectedNode = inspectedNodeId
    ? data?.nodes.find((n) => n.id === inspectedNodeId)
    : null;

  // Get position for inspected node
  const nodePosition = inspectedNodeId ? positions.get(inspectedNodeId) : null;

  // Compute visible nodes and edges
  const { visibleNodes, visibleEdges } = useMemo(() => {
    if (!data || !index) {
      return { visibleNodes: new Set<string>(), visibleEdges: new Set<string>() };
    }
    const navigation = { currentRootId, viewDepth, depthEnabled };
    const visibleNodes = computeVisibleNodesWithNavigation(data, index, filterConfig, collapseState, navigation);
    const visibleEdges = computeVisibleEdges(data, filterConfig, visibleNodes);
    return { visibleNodes, visibleEdges };
  }, [data, index, filterConfig, collapseState, currentRootId, viewDepth, depthEnabled]);

  // Copy node ID to clipboard
  const handleCopyId = useCallback(() => {
    if (inspectedNode) {
      navigator.clipboard.writeText(inspectedNode.id);
      setCopiedId(true);
      setTimeout(() => setCopiedId(false), 2000);
    }
  }, [inspectedNode]);

  // Focus on node with animation
  const handleFocus = useCallback(() => {
    if (inspectedNode && nodePosition) {
      setFocusedNode(inspectedNode.id);
      animateTo({
        position: { x: nodePosition.x, y: nodePosition.y, z: nodePosition.z + 150 },
        lookAt: { x: nodePosition.x, y: nodePosition.y, z: nodePosition.z },
      });
    }
  }, [inspectedNode, nodePosition, setFocusedNode, animateTo]);

  // Descend into node (same as double-click navigation)
  const handleDescend = useCallback(() => {
    if (!inspectedNode || !index) return;

    // Build ancestors list with names (walk from root to this node)
    const ancestors: Array<{ id: string; name: string }> = [];
    let currentId: string | null | undefined = inspectedNode.id;
    const ancestorList: string[] = [];

    while (currentId) {
      const node = index.nodesById.get(currentId);
      if (node?.parentId) {
        ancestorList.unshift(node.parentId);
        currentId = node.parentId;
      } else {
        break;
      }
    }

    for (const id of ancestorList) {
      const node = index.nodesById.get(id);
      if (node) {
        ancestors.push({ id, name: node.name || node.typeName || id });
      }
    }

    navigateTo(
      inspectedNode.id,
      inspectedNode.name || inspectedNode.typeName || inspectedNode.id,
      ancestors
    );
  }, [inspectedNode, index, navigateTo]);

  // Get connected edges for this node
  const connectedEdges = useMemo(() => {
    if (!data || !inspectedNodeId) return [];

    return data.edges.filter(
      (e) => e.source === inspectedNodeId || e.target === inspectedNodeId
    );
  }, [data, inspectedNodeId]);

  // Group edges by type, optionally filtering by visibility
  const edgesByType = useMemo(() => {
    const groups = new Map<EdgeTypeKey, Array<GraphEdge & { isOutgoing: boolean; isVisible: boolean }>>();

    for (const edge of connectedEdges) {
      const isOutgoing = edge.source === inspectedNodeId;
      const otherNodeId = isOutgoing ? edge.target : edge.source;
      const otherNodeVisible = visibleNodes.has(otherNodeId);
      const edgeVisible = visibleEdges.has(edge.id);
      const isVisible = otherNodeVisible && edgeVisible;

      // Skip hidden edges if showHidden is false
      if (!showHidden && !isVisible) continue;

      if (!groups.has(edge.type)) {
        groups.set(edge.type, []);
      }
      groups.get(edge.type)!.push({ ...edge, isOutgoing, isVisible });
    }
    return groups;
  }, [connectedEdges, inspectedNodeId, visibleNodes, visibleEdges, showHidden]);

  // Filter edges by search query
  const filteredEdgesByType = useMemo(() => {
    if (!edgeSearch.trim()) return edgesByType;
    const search = edgeSearch.toLowerCase();
    const filtered = new Map<EdgeTypeKey, Array<GraphEdge & { isOutgoing: boolean; isVisible: boolean }>>();
    for (const [type, edges] of edgesByType) {
      const matchingEdges = edges.filter((edge) => {
        const targetId = edge.isOutgoing ? edge.target : edge.source;
        const targetNode = data?.nodes.find((n) => n.id === targetId);
        const displayName = targetNode?.name || targetNode?.typeName || targetId;
        return displayName.toLowerCase().includes(search) || edge.name?.toLowerCase().includes(search);
      });
      if (matchingEdges.length > 0) {
        filtered.set(type, matchingEdges);
      }
    }
    return filtered;
  }, [edgesByType, edgeSearch, data]);

  // Count total and visible edges
  const edgeCounts = useMemo(() => {
    const total = connectedEdges.length;
    let visible = 0;
    for (const edge of connectedEdges) {
      const isOutgoing = edge.source === inspectedNodeId;
      const otherNodeId = isOutgoing ? edge.target : edge.source;
      if (visibleNodes.has(otherNodeId) && visibleEdges.has(edge.id)) {
        visible++;
      }
    }
    return { total, visible };
  }, [connectedEdges, inspectedNodeId, visibleNodes, visibleEdges]);

  if (!data || !index) {
    return (
      <div className="w-80 flex-shrink-0 bg-panel-bg border-l border-panel-border p-4">
        <div className="text-text-secondary text-sm">No graph loaded</div>
      </div>
    );
  }

  if (!inspectedNode) {
    return (
      <div className="w-80 flex-shrink-0 bg-panel-bg border-l border-panel-border p-4">
        <div className="text-text-secondary text-sm">
          Select or hover a node to inspect
        </div>
        <div className="mt-4 text-xs text-text-secondary">
          <div className="font-medium text-text-primary mb-2">Tips:</div>
          <ul className="space-y-1 list-disc list-inside">
            <li>Click a node to select it</li>
            <li>Shift+click to multi-select</li>
            <li>Double-click to navigate into</li>
            <li>Click empty space to deselect</li>
          </ul>
        </div>
      </div>
    );
  }

  const nodeColor = getNodeColor(inspectedNode.typeName);

  return (
    <div className="w-80 flex-shrink-0 bg-panel-bg border-l border-panel-border flex flex-col overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-panel-border">
        <div className="flex items-center gap-2 mb-1">
          <div
            className="w-3 h-3 rounded-full flex-shrink-0"
            style={{ backgroundColor: nodeColor }}
          />
          <div className="text-lg font-medium text-text-primary truncate flex-1">
            {inspectedNode.name || inspectedNode.typeName || 'Unnamed'}
          </div>
        </div>
        {inspectedNode.name && inspectedNode.typeName && (
          <div className="text-sm text-text-secondary truncate pl-5">
            {inspectedNode.typeName}
          </div>
        )}
        {hoveredNode === inspectedNode.id && (
          <div className="text-xs text-accent mt-1 pl-5">Hovering</div>
        )}
        {selectedNodes.has(inspectedNode.id) && !hoveredNode && (
          <div className="text-xs text-amber-400 mt-1 pl-5">Selected</div>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Basic info */}
        <Section title="Properties">
          <div className="mb-1.5">
            <div className="flex items-center justify-between gap-1 mb-0.5">
              <span className="text-xs text-text-secondary">ID:</span>
              <button
                onClick={handleCopyId}
                className="text-text-secondary hover:text-text-primary p-0.5 flex-shrink-0"
                title="Copy full ID"
              >
                {copiedId ? (
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                ) : (
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <rect x="9" y="9" width="13" height="13" rx="2" />
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                  </svg>
                )}
              </button>
            </div>
            <div className="text-[10px] text-text-primary font-mono break-all bg-graph-bg px-1.5 py-1 rounded select-all">
              {inspectedNode.id}
            </div>
          </div>
          <PropertyRow label="UUID" value={`0x${inspectedNode.uuid.toString(16)}`} />
          <PropertyRow label="Depth" value={inspectedNode.depth.toString()} />
          <PropertyRow
            label="Children"
            value={inspectedNode.childCount.toString()}
          />
          <PropertyRow label="Traits" value={inspectedNode.traitCount.toString()} />
          {inspectedNode.parentId && (
            <PropertyRow
              label="Parent"
              value="Go to parent"
              onClick={() => setFocusedNode(inspectedNode.parentId)}
            />
          )}
        </Section>

        {/* Traits */}
        {inspectedNode.traits.length > 0 && (
          <Section title={`Traits (${inspectedNode.traits.length})`}>
            <div className="space-y-1 max-h-32 overflow-y-auto">
              {inspectedNode.traits.map((trait, i) => (
                <div key={i} className="text-xs text-purple-400 truncate">
                  {trait}
                </div>
              ))}
            </div>
          </Section>
        )}

        {/* Attributes */}
        {Object.keys(inspectedNode.attributes).length > 0 && (
          <Section title="Attributes">
            {Object.entries(inspectedNode.attributes).map(([key, value]) => (
              <PropertyRow
                key={key}
                label={key}
                value={String(value)}
              />
            ))}
          </Section>
        )}

        {/* Connected edges */}
        <Section title={`Edges (${showHidden ? edgeCounts.total : edgeCounts.visible}${!showHidden && edgeCounts.total > edgeCounts.visible ? ` / ${edgeCounts.total}` : ''})`}>
          {/* Controls row */}
          <div className="flex items-center gap-2 mb-2">
            <input
              type="text"
              placeholder="Search edges..."
              value={edgeSearch}
              onChange={(e) => setEdgeSearch(e.target.value)}
              className="flex-1 px-2 py-1 text-xs bg-graph-bg border border-panel-border rounded text-text-primary placeholder:text-text-secondary/50"
            />
            <label className="flex items-center gap-1 text-[10px] text-text-secondary cursor-pointer whitespace-nowrap">
              <input
                type="checkbox"
                checked={showHidden}
                onChange={(e) => setShowHidden(e.target.checked)}
                className="w-3 h-3"
              />
              Hidden
            </label>
          </div>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {Array.from(filteredEdgesByType.entries()).map(([type, edges]) => (
              <div key={type}>
                <div className={`text-xs font-medium ${EDGE_TYPE_COLORS[type]}`}>
                  {type} ({edges.length})
                </div>
                <div className="ml-2 space-y-0.5">
                  {edges.map((edge) => {
                    const targetId = edge.isOutgoing ? edge.target : edge.source;
                    const targetNode = data.nodes.find((n) => n.id === targetId);
                    const arrow = edge.isOutgoing ? '→' : '←';
                    const dirLabel = edge.isOutgoing ? 'out' : 'in';
                    return (
                      <div
                        key={edge.id}
                        className={`text-xs hover:text-text-primary cursor-pointer truncate flex items-center gap-1 ${
                          edge.isVisible ? 'text-text-secondary' : 'text-text-secondary/40'
                        }`}
                        onClick={() => setFocusedNode(targetId)}
                        title={`${dirLabel}: ${targetNode?.name || targetNode?.typeName || targetId}`}
                      >
                        <span className={edge.isOutgoing ? 'text-green-400' : 'text-blue-400'}>{arrow}</span>
                        <span className="truncate">
                          {targetNode?.name || targetNode?.typeName || targetId}
                        </span>
                        {edge.name && <span className="text-text-secondary/50">({edge.name})</span>}
                        {!edge.isVisible && <span className="text-text-secondary/30 text-[9px]">[hidden]</span>}
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
            {filteredEdgesByType.size === 0 && (
              <div className="text-xs text-text-secondary py-2 text-center">
                {edgeSearch ? `No edges match "${edgeSearch}"` : 'No edges to show'}
              </div>
            )}
          </div>
        </Section>
      </div>

      {/* Actions */}
      <div className="p-4 border-t border-panel-border space-y-2">
        {inspectedNode.childCount > 0 && (
          <button
            onClick={handleDescend}
            className="w-full py-1.5 px-3 text-xs bg-panel-border rounded hover:bg-panel-border/80 transition-colors flex items-center justify-center gap-2"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 5v14M5 12l7 7 7-7" />
            </svg>
            Descend into Node
          </button>
        )}
        <button
          onClick={handleFocus}
          className="w-full py-1.5 px-3 text-xs bg-accent rounded hover:bg-accent/80 transition-colors flex items-center justify-center gap-2"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="3" />
            <path d="M12 2v4M12 18v4M2 12h4M18 12h4" />
          </svg>
          Focus on Node
        </button>
      </div>
    </div>
  );
}

interface SectionProps {
  title: string;
  children: React.ReactNode;
}

function Section({ title, children }: SectionProps) {
  return (
    <div>
      <div className="text-xs font-medium text-text-primary mb-2">{title}</div>
      {children}
    </div>
  );
}

interface PropertyRowProps {
  label: string;
  value: string;
  onClick?: () => void;
}

function PropertyRow({ label, value, onClick }: PropertyRowProps) {
  return (
    <div className="flex justify-between text-xs gap-2">
      <span className="text-text-secondary">{label}:</span>
      <span
        className={`text-text-primary truncate ${
          onClick ? 'cursor-pointer hover:text-accent' : ''
        }`}
        onClick={onClick}
      >
        {value}
      </span>
    </div>
  );
}
