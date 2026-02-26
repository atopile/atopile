import { useResizeHandle } from "../shared/components";
import { BuildQueueItem } from "./BuildQueueItem";
import type { Build } from "../../shared/types";

interface BuildQueuePaneProps {
  builds: Build[];
}

export function BuildQueuePane({ builds }: BuildQueuePaneProps) {
  const resize = useResizeHandle(200, 60);

  return (
    <div className="sidebar-builds-pane">
      <div
        className="sidebar-resize-handle"
        onPointerDown={resize.onPointerDown}
        onPointerMove={resize.onPointerMove}
        onPointerUp={resize.onPointerUp}
      >
        <div className="sidebar-resize-grip" />
      </div>
      <div className="sidebar-builds-header">
        <label className="sidebar-label">Build Queue</label>
      </div>
      <div
        className="sidebar-builds-scroll"
        style={{ height: resize.height }}
      >
        {builds.length === 0 ? (
          <div className="sidebar-empty">No builds yet</div>
        ) : (
          <div className="bq-list">
            {builds.map((b) => (
              <BuildQueueItem key={b.buildId ?? b.name} build={b} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
