/**
 * Breadcrumb navigation component for tree walking.
 */

import { useNavigationStore } from '../stores/navigationStore';
import { useGraphStore } from '../stores/graphStore';

export function Breadcrumbs() {
  const { data } = useGraphStore();
  const { currentRootId, breadcrumbs, navigateUp, navigateToRoot, viewDepth, setViewDepth, depthEnabled, toggleDepthEnabled } =
    useNavigationStore();

  if (!data) return null;

  const rootName = data.metadata.rootNodeId
    ? data.nodes.find((n) => n.id === data.metadata.rootNodeId)?.name ?? 'Root'
    : 'Root';

  const isAtRoot = currentRootId === null;

  return (
    <div className="flex items-center gap-2 px-3 py-2 bg-panel-bg/50 border-b border-panel-border/50">
      {/* Breadcrumb trail */}
      <div className="flex items-center gap-1 flex-1 min-w-0 overflow-x-auto">
        {/* Root */}
        <button
          onClick={() => navigateToRoot()}
          className={`text-xs px-2 py-0.5 rounded transition-colors flex-shrink-0 ${
            isAtRoot
              ? 'bg-accent text-white font-medium'
              : 'text-text-secondary hover:text-text-primary hover:bg-panel-border/50'
          }`}
        >
          {rootName}
        </button>

        {/* Path nodes */}
        {breadcrumbs.slice(0, -1).map((crumb) => (
          <div key={crumb.id} className="flex items-center gap-1 flex-shrink-0">
            <span className="text-text-secondary/50">/</span>
            <button
              onClick={() => navigateUp(crumb.id)}
              className="text-xs px-2 py-0.5 rounded text-text-secondary hover:text-text-primary hover:bg-panel-border/50 transition-colors max-w-[100px] truncate"
              title={crumb.name}
            >
              {crumb.name}
            </button>
          </div>
        ))}

        {/* Current node (last breadcrumb) */}
        {breadcrumbs.length > 0 && (
          <div className="flex items-center gap-1 flex-shrink-0">
            <span className="text-text-secondary/50">/</span>
            <span className="text-xs px-2 py-0.5 rounded bg-accent/20 text-accent font-medium max-w-[120px] truncate">
              {breadcrumbs[breadcrumbs.length - 1].name}
            </span>
          </div>
        )}
      </div>

      {/* View depth control */}
      <div className="flex items-center gap-1.5 flex-shrink-0 ml-2 pl-2 border-l border-panel-border/50">
        <label className="flex items-center gap-1 cursor-pointer">
          <input
            type="checkbox"
            checked={depthEnabled}
            onChange={toggleDepthEnabled}
            className="w-3 h-3"
          />
          <span className="text-[10px] text-text-secondary">Depth:</span>
        </label>
        <div className={`flex items-center gap-0.5 ${!depthEnabled ? 'opacity-30' : ''}`}>
          <button
            onClick={() => setViewDepth(viewDepth - 1)}
            disabled={!depthEnabled || viewDepth <= 1}
            className="w-5 h-5 text-xs rounded bg-panel-border/50 hover:bg-panel-border disabled:opacity-30 disabled:cursor-not-allowed flex items-center justify-center"
          >
            -
          </button>
          <span className="text-xs text-text-primary w-6 text-center tabular-nums">
            {depthEnabled ? viewDepth : '∞'}
          </span>
          <button
            onClick={() => setViewDepth(viewDepth + 1)}
            disabled={!depthEnabled}
            className="w-5 h-5 text-xs rounded bg-panel-border/50 hover:bg-panel-border disabled:opacity-30 disabled:cursor-not-allowed flex items-center justify-center"
          >
            +
          </button>
        </div>
      </div>

      {/* Up button */}
      {!isAtRoot && (
        <button
          onClick={() => {
            if (breadcrumbs.length > 1) {
              navigateUp(breadcrumbs[breadcrumbs.length - 2].id);
            } else {
              navigateToRoot();
            }
          }}
          className="flex-shrink-0 px-2 py-1 text-xs rounded bg-panel-border/50 hover:bg-panel-border text-text-secondary hover:text-text-primary transition-colors flex items-center gap-1"
          title="Go up one level"
        >
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M15 18l-6-6 6-6" />
          </svg>
          Up
        </button>
      )}
    </div>
  );
}
