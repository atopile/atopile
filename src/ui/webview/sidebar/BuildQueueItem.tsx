import { useState } from "react";
import {
  ChevronDown,
  ChevronRight,
  Check,
  X,
  Clock,
  AlertTriangle,
} from "lucide-react";
import { Spinner } from "../shared/components";
import type { Build } from "../../shared/types";
import { formatDuration, formatTimeAgo } from "../shared/utils";

function stageStatusIcon(status: string) {
  switch (status) {
    case "running":
      return <Spinner size={12} />;
    case "success":
      return <Check size={12} className="stage-icon-success" />;
    case "warning":
      return <AlertTriangle size={12} className="stage-icon-warning" />;
    case "failed":
    case "error":
      return <X size={12} className="stage-icon-failed" />;
    default:
      return <Clock size={12} className="stage-icon-pending" />;
  }
}

export function BuildQueueItem({ build }: { build: Build }) {
  const [expanded, setExpanded] = useState(false);
  const currentStage = build.currentStage;
  const isActive = build.status === "building" || build.status === "queued";
  const stages = build.stages ?? [];

  const stageProgress =
    build.totalStages && build.totalStages > 0
      ? `${stages.filter((s) => s.status !== "pending" && s.status !== "skipped").length}/${build.totalStages}`
      : undefined;

  return (
    <div className={`bq-item bq-item-${build.status}`}>
      <button
        className="bq-item-header"
        onClick={() => setExpanded(!expanded)}
      >
        <span className="bq-item-chevron">
          {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        </span>
        <span className="bq-item-info">
          <span className="bq-item-target">
            {build.target ?? build.displayName}
          </span>
          {currentStage && isActive && (
            <span className="bq-item-stage">
              {currentStage.displayName ?? currentStage.name}
            </span>
          )}
        </span>
        <span className="bq-item-meta">
          {isActive && <Spinner size={12} />}
          {stageProgress && (
            <span className="bq-item-progress">{stageProgress}</span>
          )}
          {!isActive && build.startedAt && (
            <span className="bq-item-ago">
              {formatTimeAgo(build.startedAt)}
            </span>
          )}
        </span>
      </button>

      {expanded && (
        <div className="bq-item-details">
          {build.elapsedSeconds > 0 && (
            <div className="bq-item-elapsed">
              <Clock size={11} /> {formatDuration(build.elapsedSeconds)}
            </div>
          )}
          {(build.warnings ?? 0) > 0 && (
            <div className="bq-item-warnings">
              <AlertTriangle size={11} /> {build.warnings} warning
              {build.warnings !== 1 ? "s" : ""}
            </div>
          )}
          {build.error && (
            <div className="bq-item-error">{build.error}</div>
          )}

          {stages.length > 0 && (
            <div className="bq-stages">
              {stages.map((stage, i) => (
                <div
                  key={stage.stageId ?? i}
                  className={`bq-stage bq-stage-${stage.status}`}
                >
                  <span className="bq-stage-icon">
                    {stageStatusIcon(stage.status)}
                  </span>
                  <span className="bq-stage-name">
                    {stage.displayName ?? stage.name}
                  </span>
                  {stage.elapsedSeconds > 0 && (
                    <span className="bq-stage-time">
                      {formatDuration(stage.elapsedSeconds)}
                    </span>
                  )}
                  {(stage.warnings ?? 0) > 0 && (
                    <span className="bq-stage-badge bq-stage-badge-warning">
                      {stage.warnings}
                    </span>
                  )}
                  {(stage.errors ?? 0) > 0 && (
                    <span className="bq-stage-badge bq-stage-badge-error">
                      {stage.errors}
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
