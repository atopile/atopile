import { useMemo } from "react";
import { render, logoUrl } from "../shared/render";
import { useSubscribe, ws } from "../shared/webSocketProvider";
import { sendAction } from "../../shared/webSocketUtils";
import { useResizeHandle } from "../shared/components";
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

function App() {
  const projectState = useSubscribe("project_state");
  const hubStatus = useSubscribe("hub_status");

  const resize = useResizeHandle(200, 60);

  const targets = useMemo(() => {
    const match = projectState.projects.find(
      (p) => p.root === projectState.selectedProject,
    );
    return match?.targets ?? [];
  }, [
    projectState.projects,
    projectState.selectedProject,
  ]);

  const projectBuilds = useMemo(
    () =>
      getLatestPerTarget(
        projectState.builds,
        projectState.selectedProject,
      ),
    [
      projectState.builds,
      projectState.selectedProject,
    ],
  );

  const isBuilding = useMemo(
    () =>
      projectBuilds.some(
        (b) =>
          (b.status === "queued" || b.status === "building") &&
          b.name === projectState.selectedTarget,
      ),
    [projectBuilds, projectState.selectedTarget],
  );

  const projectItems = projectState.projects.map((p) => ({
    label: p.name,
    value: p.root,
  }));

  const targetItems = targets.map((t) => ({
    label: t,
    value: t,
  }));

  if (!hubStatus.connected) {
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
            {projectState.projects.length === 0 ? (
              <span className="sidebar-empty">No projects found</span>
            ) : (
              <Select
                items={projectItems}
                value={projectState.selectedProject}
                onValueChange={(v) =>
                  sendAction(ws,"select_project", { projectRoot: v })
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
        {projectState.selectedProject && (
          <div className="sidebar-field">
            <label className="sidebar-field-label">Target</label>
            <div className="sidebar-field-control">
              {targets.length === 0 ? (
                <span className="sidebar-empty">No targets</span>
              ) : (
                <Select
                  items={targetItems}
                  value={projectState.selectedTarget}
                  onValueChange={(v) =>
                    sendAction(ws,"select_target", { target: v })
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
              sendAction(ws,"start_build", {
                projectRoot: projectState.selectedProject,
                targets: [projectState.selectedTarget],
              })
            }
            disabled={
              !projectState.selectedProject ||
              !projectState.selectedTarget ||
              isBuilding
            }
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
      {projectState.selectedProject && (
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
