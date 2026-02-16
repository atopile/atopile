/**
 * Collapse panel - simplified for tree navigation system.
 *
 * Shows depth distribution and collapse/expand controls for individual nodes.
 */

import { useMemo } from 'react';
import { useGraphStore } from '../../stores/graphStore';
import { useCollapseStore } from '../../stores/collapseStore';

export function CollapsePanel() {
  const { data, index, minDepth, maxDepth } = useGraphStore();
  const {
    state,
    expandAllNodes,
    collapseAllNodes,
  } = useCollapseStore();

  // Count stats
  const stats = useMemo(() => {
    if (!data || !index) return null;
    const collapsedCount = state.collapsedNodes.size;
    const nodesByDepth = new Map<number, number>();

    for (const node of data.nodes) {
      nodesByDepth.set(node.depth, (nodesByDepth.get(node.depth) || 0) + 1);
    }

    return {
      collapsedCount,
      nodesByDepth,
      totalNodes: data.nodes.length,
    };
  }, [data, index, state.collapsedNodes]);

  if (!data || !stats) return null;

  return (
    <div className="space-y-4">
      {/* Quick actions */}
      <div className="space-y-2">
        <div className="text-sm font-medium text-text-primary">Quick Actions</div>
        <div className="flex gap-2">
          <button
            onClick={expandAllNodes}
            disabled={state.collapsedNodes.size === 0}
            className="flex-1 py-1.5 px-3 text-xs bg-panel-border rounded hover:bg-panel-border/80 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            Expand All
          </button>
          <button
            onClick={() => collapseAllNodes(data)}
            className="flex-1 py-1.5 px-3 text-xs bg-panel-border rounded hover:bg-panel-border/80 transition-colors"
          >
            Collapse All
          </button>
        </div>
      </div>

      {/* Info about tree navigation */}
      <div className="space-y-2 pt-2 border-t border-panel-border">
        <div className="text-sm font-medium text-text-primary">Tree Navigation</div>
        <div className="text-xs text-text-secondary space-y-1">
          <p>Use the breadcrumbs at the top to navigate the graph hierarchy.</p>
          <ul className="list-disc list-inside space-y-0.5 mt-2 text-[11px]">
            <li>Double-click a node to drill down</li>
            <li>Use Depth +/- to show more/less levels</li>
            <li>Click breadcrumb items to go back up</li>
          </ul>
        </div>
      </div>

      {/* Depth distribution */}
      <div className="space-y-2 pt-2 border-t border-panel-border">
        <div className="text-sm font-medium text-text-primary">
          Depth Distribution
        </div>
        <div className="text-xs text-text-secondary mb-2">
          Graph depth: {minDepth} - {maxDepth}
        </div>
        <div className="space-y-1 max-h-40 overflow-y-auto">
          {Array.from(stats.nodesByDepth.entries())
            .sort(([a], [b]) => a - b)
            .map(([depth, count]) => {
              const percentage = (count / stats.totalNodes) * 100;
              return (
                <div key={depth} className="flex items-center gap-2 text-xs">
                  <span className="w-8 text-text-secondary">D{depth}</span>
                  <div className="flex-1 h-1.5 bg-panel-border rounded overflow-hidden">
                    <div
                      className="h-full bg-accent/60 rounded"
                      style={{ width: `${percentage}%` }}
                    />
                  </div>
                  <span className="w-10 text-right text-text-secondary/60 tabular-nums">
                    {count}
                  </span>
                </div>
              );
            })}
        </div>
      </div>

      {/* Status */}
      <div className="space-y-2 pt-2 border-t border-panel-border">
        <div className="text-sm font-medium text-text-primary">Status</div>
        <div className="text-xs text-text-secondary space-y-1">
          <div className="flex justify-between">
            <span>Manually collapsed:</span>
            <span className="text-text-primary tabular-nums">
              {state.collapsedNodes.size}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
