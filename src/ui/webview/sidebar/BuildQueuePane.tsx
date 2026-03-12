import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { useResizeHandle } from "../shared/components";
import { BuildQueueItem } from "./BuildQueueItem";
import type { Build, BuildStage } from "../../shared/generated-types";

interface BuildQueuePaneProps {
  builds: Array<Build & { currentStage: BuildStage | null }>;
}

export function BuildQueuePane({ builds }: BuildQueuePaneProps) {
  const [collapsed, setCollapsed] = useState(false);
  const resize = useResizeHandle(120, 60);

  return (
    <div
      className={`build-queue-panel-container${collapsed ? " collapsed" : ""}`}
      style={collapsed ? undefined : { height: resize.height }}
    >
      {!collapsed && (
        <div
          className="build-queue-resize-handle"
          onPointerDown={resize.onPointerDown}
          onPointerMove={resize.onPointerMove}
          onPointerUp={resize.onPointerUp}
        />
      )}
      <button
        type="button"
        className="build-queue-panel-header"
        onClick={() => setCollapsed((value) => !value)}
      >
        <ChevronDown
          size={12}
          className={`build-queue-chevron${collapsed ? "" : " open"}`}
        />
        <span className="build-queue-panel-title">Build Queue</span>
        {builds.length > 0 && (
          <span className="build-queue-panel-badge">{builds.length}</span>
        )}
      </button>
      {!collapsed && (
        <div className="build-queue-panel-content">
          {builds.length === 0 ? (
            <div className="build-queue-empty">No recent builds</div>
          ) : (
            builds.map((build) => (
              <BuildQueueItem
                key={build.buildId ?? build.name}
                build={build}
              />
            ))
          )}
        </div>
      )}
    </div>
  );
}
