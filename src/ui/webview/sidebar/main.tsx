import { useMemo } from "react";
import { render, AppProps } from "../shared/render";
import { useWebSocket } from "../shared/webSocket";
import { useResizeHandle } from "../shared/components";
import type { Project, Build, ProjectState } from "../shared/types";
import { getLatestPerTarget } from "../shared/utils";
import { BuildQueueItem } from "./BuildQueueItem";
import "./sidebar.css";
import { Hammer, Code } from "lucide-react";
import {
  Button,
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
  Spinner,
} from "../shared/components";

const vscode = acquireVsCodeApi();

function openPanel(panelId: string) {
  vscode.postMessage({ type: "openPanel", panelId });
}

function App({ hubUrl, logoUrl }: AppProps) {
  const { connected, state, sendAction } = useWebSocket(hubUrl, [
    "core_status",
    "project_state",
  ]);

  const project = state.project_state as ProjectState | undefined;
  const projects = project?.projects ?? [];
  const builds = project?.builds ?? [];
  const selectedProject = project?.selected_project ?? null;
  const selectedTarget = project?.selected_target ?? null;

  const resize = useResizeHandle(200, 60);

  const targets = useMemo(() => {
    const match = projects.find((p) => p.root === selectedProject);
    return match?.targets ?? [];
  }, [projects, selectedProject]);

  const projectBuilds = useMemo(
    () => getLatestPerTarget(builds, selectedProject),
    [builds, selectedProject],
  );

  const isBuilding = useMemo(
    () =>
      projectBuilds.some(
        (b) =>
          (b.status === "queued" || b.status === "building") &&
          b.target === selectedTarget,
      ),
    [projectBuilds, selectedTarget],
  );

  const projectItems = projects.map((p) => ({
    label: p.name,
    value: p.root,
  }));

  const targetItems = targets.map((t) => ({
    label: t,
    value: t,
  }));

  if (!connected) {
    return (
      <div className="sidebar">
        <div className="sidebar-header">
          {logoUrl && (
            <img src={logoUrl} alt="atopile" className="sidebar-logo" />
          )}
          <span className="sidebar-title">atopile</span>
        </div>
        <div className="sidebar-status">
          <Spinner size={14} />
          <span>Connecting...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="sidebar">
      {/* Header: logo + title */}
      <div className="sidebar-header">
        {logoUrl && (
          <img src={logoUrl} alt="atopile" className="sidebar-logo" />
        )}
        <span className="sidebar-title">atopile</span>
      </div>

      {/* Top section: selectors + build button */}
      <div className="sidebar-top">
        {/* Project selector */}
        <div className="sidebar-field">
          <label className="sidebar-field-label">Project</label>
          <div className="sidebar-field-control">
            {projects.length === 0 ? (
              <span className="sidebar-empty">No projects found</span>
            ) : (
              <Select
                items={projectItems}
                value={selectedProject}
                onValueChange={(v) =>
                  sendAction("select_project", { projectRoot: v })
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select project..." />
                </SelectTrigger>
                <SelectContent>
                  {projectItems.map((item) => (
                    <SelectItem key={item.value} value={item.value}>
                      {item.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>
        </div>

        {/* Target selector */}
        {selectedProject && (
          <div className="sidebar-field">
            <label className="sidebar-field-label">Target</label>
            <div className="sidebar-field-control">
              {targets.length === 0 ? (
                <span className="sidebar-empty">No targets</span>
              ) : (
                <Select
                  items={targetItems}
                  value={selectedTarget}
                  onValueChange={(v) =>
                    sendAction("select_target", { target: v })
                  }
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select target..." />
                  </SelectTrigger>
                  <SelectContent>
                    {targetItems.map((item) => (
                      <SelectItem key={item.value} value={item.value}>
                        {item.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            </div>
          </div>
        )}

        {/* Action buttons */}
        <div className="sidebar-actions">
          <Button
            onClick={() =>
              sendAction("start_build", {
                projectRoot: selectedProject,
                targets: [selectedTarget],
              })
            }
            disabled={!selectedProject || !selectedTarget || isBuilding}
          >
            {isBuilding ? (
              <>
                <Spinner size={14} /> Building...
              </>
            ) : (
              <>
                <Hammer size={14} /> Build
              </>
            )}
          </Button>
          <Button
            variant="secondary"
            onClick={() => openPanel("panel-developer")}
          >
            <Code size={14} /> Developer
          </Button>
        </div>
      </div>

      {/* Resizable builds pane at bottom */}
      {selectedProject && (
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
            <label className="sidebar-label">Builds</label>
          </div>
          <div
            className="sidebar-builds-scroll"
            style={{ height: resize.height }}
          >
            {projectBuilds.length === 0 ? (
              <div className="sidebar-empty">No builds yet</div>
            ) : (
              <div className="bq-list">
                {projectBuilds.map((b) => (
                  <BuildQueueItem key={b.buildId ?? b.name} build={b} />
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

render(App);
