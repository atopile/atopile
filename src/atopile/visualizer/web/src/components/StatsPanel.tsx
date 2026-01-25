/**
 * Statistics panel showing graph metrics and distribution information.
 *
 * Provides insights into the graph structure including node/edge counts,
 * type distributions, and depth statistics.
 */

import { useMemo, useState } from 'react';
import { useGraphStore } from '../stores/graphStore';
import { useFilterStore } from '../stores/filterStore';
import { useCollapseStore } from '../stores/collapseStore';
import { computeVisibleNodes, computeVisibleEdges } from '../lib/filterEngine';

interface StatItemProps {
  label: string;
  value: number | string;
  subtext?: string;
  color?: string;
}

function StatItem({ label, value, subtext, color }: StatItemProps) {
  return (
    <div className="flex justify-between items-baseline py-1">
      <span className="text-xs text-text-secondary">{label}</span>
      <div className="text-right">
        <span
          className="text-sm font-medium"
          style={{ color: color || 'inherit' }}
        >
          {typeof value === 'number' ? value.toLocaleString() : value}
        </span>
        {subtext && (
          <span className="text-[10px] text-text-secondary ml-1">
            {subtext}
          </span>
        )}
      </div>
    </div>
  );
}

interface DistributionBarProps {
  label: string;
  count: number;
  total: number;
  color: string;
}

function DistributionBar({ label, count, total, color }: DistributionBarProps) {
  const percentage = total > 0 ? (count / total) * 100 : 0;

  return (
    <div className="mb-2">
      <div className="flex justify-between text-[10px] mb-0.5">
        <span className="text-text-secondary truncate flex-1">{label}</span>
        <span className="text-text-primary ml-2">{count}</span>
      </div>
      <div className="h-1.5 bg-graph-bg rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-300"
          style={{
            width: `${percentage}%`,
            backgroundColor: color,
          }}
        />
      </div>
    </div>
  );
}

export function StatsPanel() {
  const { data, index, minDepth, maxDepth, isLayoutRunning, layoutProgress } =
    useGraphStore();
  const { config } = useFilterStore();
  const { state: collapseState } = useCollapseStore();
  const [expanded, setExpanded] = useState<Record<string, boolean>>({
    overview: true,
    nodes: true,
    edges: true,
    depth: true,
  });

  // Calculate visible counts
  const { visibleNodes, visibleEdges, stats } = useMemo(() => {
    if (!data || !index) {
      return {
        visibleNodes: new Set<string>(),
        visibleEdges: new Set<string>(),
        stats: null,
      };
    }

    const visibleNodes = computeVisibleNodes(data, index, config, collapseState);
    const visibleEdges = computeVisibleEdges(data, config, visibleNodes);

    // Calculate type distributions
    const nodeTypeCount = new Map<string, number>();
    const edgeTypeCount = new Map<string, number>();
    const depthCount = new Map<number, number>();
    const traitCount = new Map<string, number>();

    for (const nodeId of visibleNodes) {
      const node = index.nodesById.get(nodeId);
      if (node) {
        const typeName = node.typeName || 'Unknown';
        nodeTypeCount.set(typeName, (nodeTypeCount.get(typeName) || 0) + 1);
        depthCount.set(node.depth, (depthCount.get(node.depth) || 0) + 1);

        for (const trait of node.traits) {
          traitCount.set(trait, (traitCount.get(trait) || 0) + 1);
        }
      }
    }

    for (const edgeId of visibleEdges) {
      const edge = data.edges.find((e) => e.id === edgeId);
      if (edge) {
        edgeTypeCount.set(edge.type, (edgeTypeCount.get(edge.type) || 0) + 1);
      }
    }

    return {
      visibleNodes,
      visibleEdges,
      stats: {
        nodeTypeCount,
        edgeTypeCount,
        depthCount,
        traitCount,
      },
    };
  }, [data, index, config, collapseState]);

  if (!data || !index || !stats) {
    return (
      <div className="p-3 text-xs text-text-secondary">No graph loaded</div>
    );
  }

  const toggleSection = (section: string) => {
    setExpanded((prev) => ({ ...prev, [section]: !prev[section] }));
  };

  // Sort distributions
  const sortedNodeTypes = [...stats.nodeTypeCount.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10);

  const sortedEdgeTypes = [...stats.edgeTypeCount.entries()].sort(
    (a, b) => b[1] - a[1]
  );

  const sortedDepths = [...stats.depthCount.entries()].sort(
    (a, b) => a[0] - b[0]
  );

  const typeColors: Record<string, string> = {
    composition: '#22c55e',
    connection: '#3b82f6',
    trait: '#a855f7',
    pointer: '#64748b',
    operand: '#f97316',
    type: '#06b6d4',
    next: '#eab308',
  };

  return (
    <div className="space-y-2">
      {/* Layout Status */}
      {isLayoutRunning && (
        <div className="p-2 bg-accent/10 rounded border border-accent/30">
          <div className="flex items-center gap-2 text-xs text-accent">
            <span className="w-3 h-3 border-2 border-accent border-t-transparent rounded-full animate-spin" />
            Computing layout... {Math.round(layoutProgress * 100)}%
          </div>
          <div className="mt-1 h-1 bg-graph-bg rounded-full overflow-hidden">
            <div
              className="h-full bg-accent transition-all duration-200"
              style={{ width: `${layoutProgress * 100}%` }}
            />
          </div>
        </div>
      )}

      {/* Overview Section */}
      <div className="border-b border-panel-border pb-2">
        <button
          onClick={() => toggleSection('overview')}
          className="w-full flex items-center justify-between py-1 text-xs font-medium text-text-primary hover:text-accent transition-colors"
        >
          <span>Overview</span>
          <svg
            className={`w-3 h-3 transition-transform ${expanded.overview ? 'rotate-180' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 9l-7 7-7-7"
            />
          </svg>
        </button>

        {expanded.overview && (
          <div className="pt-1">
            <StatItem
              label="Total Nodes"
              value={data.nodes.length}
              subtext={
                visibleNodes.size < data.nodes.length
                  ? `(${visibleNodes.size} visible)`
                  : undefined
              }
            />
            <StatItem
              label="Total Edges"
              value={data.edges.length}
              subtext={
                visibleEdges.size < data.edges.length
                  ? `(${visibleEdges.size} visible)`
                  : undefined
              }
            />
            <StatItem
              label="Depth Range"
              value={`${minDepth} - ${maxDepth}`}
            />
            <StatItem
              label="Node Types"
              value={stats.nodeTypeCount.size}
            />
            <StatItem
              label="Traits Used"
              value={stats.traitCount.size}
            />
          </div>
        )}
      </div>

      {/* Node Types Section */}
      <div className="border-b border-panel-border pb-2">
        <button
          onClick={() => toggleSection('nodes')}
          className="w-full flex items-center justify-between py-1 text-xs font-medium text-text-primary hover:text-accent transition-colors"
        >
          <span>Node Types ({stats.nodeTypeCount.size})</span>
          <svg
            className={`w-3 h-3 transition-transform ${expanded.nodes ? 'rotate-180' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 9l-7 7-7-7"
            />
          </svg>
        </button>

        {expanded.nodes && (
          <div className="pt-2">
            {sortedNodeTypes.map(([type, count], idx) => (
              <DistributionBar
                key={type}
                label={type}
                count={count}
                total={visibleNodes.size}
                color={`hsl(${(idx * 37) % 360}, 65%, 55%)`}
              />
            ))}
            {stats.nodeTypeCount.size > 10 && (
              <div className="text-[10px] text-text-secondary text-center">
                +{stats.nodeTypeCount.size - 10} more types
              </div>
            )}
          </div>
        )}
      </div>

      {/* Edge Types Section */}
      <div className="border-b border-panel-border pb-2">
        <button
          onClick={() => toggleSection('edges')}
          className="w-full flex items-center justify-between py-1 text-xs font-medium text-text-primary hover:text-accent transition-colors"
        >
          <span>Edge Types ({sortedEdgeTypes.length})</span>
          <svg
            className={`w-3 h-3 transition-transform ${expanded.edges ? 'rotate-180' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 9l-7 7-7-7"
            />
          </svg>
        </button>

        {expanded.edges && (
          <div className="pt-2">
            {sortedEdgeTypes.map(([type, count]) => (
              <DistributionBar
                key={type}
                label={type}
                count={count}
                total={visibleEdges.size}
                color={typeColors[type] || '#9ca3af'}
              />
            ))}
          </div>
        )}
      </div>

      {/* Depth Distribution Section */}
      <div className="pb-2">
        <button
          onClick={() => toggleSection('depth')}
          className="w-full flex items-center justify-between py-1 text-xs font-medium text-text-primary hover:text-accent transition-colors"
        >
          <span>Depth Distribution</span>
          <svg
            className={`w-3 h-3 transition-transform ${expanded.depth ? 'rotate-180' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 9l-7 7-7-7"
            />
          </svg>
        </button>

        {expanded.depth && (
          <div className="pt-2">
            {sortedDepths.map(([depth, count]) => (
              <DistributionBar
                key={depth}
                label={`Level ${depth}`}
                count={count}
                total={visibleNodes.size}
                color={`hsl(${200 + depth * 15}, 70%, 50%)`}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
