import { useEffect, useMemo, useRef, useState, type MouseEvent } from "react";
import {
  AlertCircle,
  ChevronDown,
  X,
} from "lucide-react";
import { Spinner } from "../shared/components";
import type { Build, BuildStage } from "../../shared/generated-types";
import { createWebviewLogger } from "../shared/logger";
import { rpcClient } from "../shared/rpcClient";
import { STATUS_ICONS, formatDuration, formatRelativeSeconds, getBuildCounter } from "../shared/utils";

const logger = createWebviewLogger("BuildQueue");
const recentlyCompletedBuilds = new Set<string>();
const lastSeenBuildStatuses = new Map<string, Build["status"]>();

function buildStatusIcon(status: Build["status"]) {
  const Icon = STATUS_ICONS[status];
  return Icon ? <Icon size={14} className={`status-icon ${status}`} /> : null;
}

function stageStatusIcon(status: string) {
  if (status === "running") return <Spinner size={12} />;
  const Icon = STATUS_ICONS[status] ?? AlertCircle;
  return <Icon size={12} className={`stage-icon-${status === "error" ? "failed" : status}`} />;
}

export function BuildQueueItem({
  build,
}: {
  build: Build & { currentStage: BuildStage | null };
}) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [justCompleted, setJustCompleted] = useState(false);
  const previousStatusRef = useRef<Build["status"] | null>(null);

  useEffect(() => {
    const previousStatus = build.buildId
      ? lastSeenBuildStatuses.get(build.buildId) ?? null
      : previousStatusRef.current;
    const currentStatus = build.status;
    const isComplete =
      currentStatus === "success" ||
      currentStatus === "failed" ||
      currentStatus === "warning";
    const wasActive = previousStatus === "building" || previousStatus === "queued";

    if (wasActive && isComplete && build.buildId && !recentlyCompletedBuilds.has(build.buildId)) {
      recentlyCompletedBuilds.add(build.buildId);
      setJustCompleted(true);

      const timer = window.setTimeout(() => {
        setJustCompleted(false);
        window.setTimeout(() => {
          recentlyCompletedBuilds.delete(build.buildId!);
        }, 5_000);
      }, 600);

      lastSeenBuildStatuses.set(build.buildId, currentStatus);
      previousStatusRef.current = currentStatus;
      return () => window.clearTimeout(timer);
    }

    if (build.buildId) {
      lastSeenBuildStatuses.set(build.buildId, currentStatus);
    }
    previousStatusRef.current = currentStatus;
    return undefined;
  }, [build.buildId, build.status]);

  const progress = useMemo(() => {
    if (!build.stages.length) return 0;
    const completedStages = build.stages.filter(
      (stage) => stage.status === "success" || stage.status === "warning",
    ).length;
    const totalStages = build.totalStages || Math.max(completedStages + 1, 10);
    return Math.round((completedStages / totalStages) * 100);
  }, [build.stages, build.totalStages]);

  const isComplete =
    build.status === "success" ||
    build.status === "failed" ||
    build.status === "warning" ||
    build.status === "cancelled";
  const hasStages = build.stages.length > 0;
  const hasFailedStage = build.stages.some(
    (stage) => stage.status === "failed" || stage.status === "error",
  );
  const buildCounter = useMemo(() => getBuildCounter(build.buildId), [build.buildId]);
  const runningStageElapsed = useMemo(() => {
    const runningStage = build.stages.find((stage) => stage.status === "running");
    return runningStage?.elapsedSeconds ?? null;
  }, [build.stages]);
  const completedAt = useMemo(() => {
    if (!build.startedAt || !build.elapsedSeconds) return null;
    return build.startedAt + build.elapsedSeconds;
  }, [build.elapsedSeconds, build.startedAt]);
  const statusLabel = useMemo(() => {
    switch (build.status) {
      case "queued":
        return "Queued";
      case "building":
        return "";
      case "success":
      case "failed":
      case "warning":
      case "cancelled":
        return completedAt ? formatRelativeSeconds(completedAt) : "";
      default:
        return build.status;
    }
  }, [build.status, completedAt]);

  const openLogs = async (stage?: string | null): Promise<void> => {
    if (build.projectRoot) {
      rpcClient?.sendAction("selectProject", { projectRoot: build.projectRoot });
    }
    if (build.target) {
      rpcClient?.sendAction("selectTarget", { target: build.target });
    }
    if (build.buildId) {
      rpcClient?.sendAction("setLogViewCurrentId", {
        buildId: build.buildId,
        stage: stage ?? null,
      });
    }
    try {
      await rpcClient?.requestAction("vscode.showLogsView");
    } catch (error) {
      logger.error(
        `openLogs failed buildId=${build.buildId ?? "unknown"} error=${error instanceof Error ? error.message : String(error)}`,
      );
    }
  };

  const cancelBuild = (event: MouseEvent<HTMLButtonElement>): void => {
    event.stopPropagation();
    if (!build.buildId) {
      return;
    }
    rpcClient?.sendAction("cancelBuild", { buildId: build.buildId });
  };

  return (
    <div
      className={`build-queue-item ${build.status}${isExpanded ? " expanded" : ""}${justCompleted ? " just-completed" : ""}`}
    >
      <div
        className="build-queue-header"
        onClick={() => {
          setIsExpanded((value) => !value);
          void openLogs();
        }}
      >
        <span className={`build-expand-icon${isExpanded ? " open" : ""}`}>
          <ChevronDown size={10} />
        </span>
        {isComplete ? (
          buildStatusIcon(build.status)
        ) : hasFailedStage ? (
          buildStatusIcon("failed")
        ) : build.status === "building" ? (
          <Spinner size={14} className="status-icon building" />
        ) : null}
        <span className="build-queue-info">
          <span className="build-queue-target">
            {build.name}
          </span>
          {build.status === "building" && !hasFailedStage && build.currentStage && (
            <span className="build-queue-stage" title={build.currentStage.name}>
              {build.currentStage.name}
            </span>
          )}
          {build.status === "failed" && (
            <span className="build-failed-hint">
              Build failed... <span className="show-logs-link">show logs</span>
            </span>
          )}
        </span>
        {statusLabel && (
          <span className="build-queue-meta">
            <span className="build-queue-status">{statusLabel}</span>
          </span>
        )}
        {build.status === "building" && !hasFailedStage && (
          <div className="build-queue-progress">
            <div
              className="build-queue-progress-bar"
              style={{ width: `${progress}%` }}
            />
          </div>
        )}
        {(build.status === "queued" || build.status === "building") && build.buildId && (
          <button
            type="button"
            className="build-queue-cancel"
            onClick={cancelBuild}
            title="Cancel build"
          >
            <X size={10} />
          </button>
        )}
      </div>

      {isExpanded && (
        <div className="build-stages">
          <div className="build-stages-header">
            <span className="build-stages-title">
              Steps ({build.stages.length})
            </span>
            <span className="build-stages-meta">
              {buildCounter && (
                <span className="build-queue-counter">{buildCounter}</span>
              )}
              {build.elapsedSeconds > 0 && (
                <span className="build-stages-total">
                  Total {formatDuration(build.elapsedSeconds)}
                </span>
              )}
            </span>
          </div>
          {hasStages ? (
            build.stages.map((stage, index) => (
              <button
                type="button"
                key={stage.stageId || index}
                className={`build-stage ${stage.status}`}
                onClick={() => {
                  void openLogs(stage.stageId || stage.name);
                }}
                title={`View logs for ${stage.name}`}
              >
                <span className="stage-icon">
                  {stageStatusIcon(stage.status)}
                </span>
                <span className="stage-name">{stage.name}</span>
                {(() => {
                  const elapsed =
                    stage.status === "running"
                      ? runningStageElapsed ?? stage.elapsedSeconds
                      : stage.elapsedSeconds;
                  if (elapsed == null || stage.status === "pending") {
                    return null;
                  }
                  return <span className="stage-time">{formatDuration(elapsed)}</span>;
                })()}
                {(stage.warnings ?? 0) > 0 && (
                  <span className="stage-badge warning">{stage.warnings}</span>
                )}
                {(stage.errors ?? 0) > 0 && (
                  <span className="stage-badge error">{stage.errors}</span>
                )}
              </button>
            ))
          ) : (
            <div className="build-stages-empty">No steps recorded</div>
          )}
        </div>
      )}
    </div>
  );
}
