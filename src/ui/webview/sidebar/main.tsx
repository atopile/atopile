import { useMemo, useState } from "react";
import { render, logoUrl } from "../shared/render";
import { useSubscribe, ws } from "../shared/webSocketProvider";
import { sendAction } from "../../shared/webSocketUtils";
import { Spinner } from "../shared/components";
import { getCurrentStage } from "../shared/utils";
import { BuildQueuePane } from "./BuildQueuePane";
import { ProjectTargetSelector } from "./ProjectTargetSelector";
import { ActionBar } from "./ActionBar";
import { TabBar, type TabId } from "./TabBar";
import {
  FilesPanel,
  PackagesPanel,
  PartsPanel,
  LibraryPanel,
  StructurePanel,
  ParametersPanel,
  BOMPanel,
} from "../sidebar-panels";
import "./sidebar.css";

function App() {
  const projectState = useSubscribe("projectState");
  const hubStatus = useSubscribe("hubStatus");
  const latestBuilds = useSubscribe("latestBuilds");

  const [activeTab, setActiveTab] = useState<TabId>("files");

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
      latestBuilds
        .filter((b) => b.projectRoot === projectState.selectedProject)
        .map((b) => ({ ...b, currentStage: getCurrentStage(b) })),
    [latestBuilds, projectState.selectedProject],
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

  const panelMap: Record<TabId, React.ReactNode> = {
    files: <FilesPanel />,
    packages: <PackagesPanel />,
    parts: <PartsPanel />,
    library: <LibraryPanel />,
    structure: <StructurePanel />,
    parameters: <ParametersPanel />,
    bom: <BOMPanel />,
  };

  return (
    <div className="sidebar">
      {/* Header: logo + title + version badge */}
      <div className="sidebar-header">
        {logoUrl && (
          <img src={logoUrl} alt="atopile" className="sidebar-logo" />
        )}
        <span className="sidebar-title">atopile</span>
        <span className="version-badge">v0.0.0</span>
      </div>

      {/* Top section: selectors + action bar */}
      <div className="sidebar-top">
        <ProjectTargetSelector
          projects={projectState.projects}
          selectedProject={projectState.selectedProject}
          onSelectProject={(root) =>
            sendAction(ws, "select_project", { projectRoot: root })
          }
          targets={targets}
          selectedTarget={projectState.selectedTarget}
          onSelectTarget={(target) =>
            sendAction(ws, "select_target", { target })
          }
        />
        <ActionBar
          onBuild={() =>
            sendAction(ws, "start_build", {
              projectRoot: projectState.selectedProject,
              targets: [projectState.selectedTarget],
            })
          }
          buildDisabled={
            !projectState.selectedProject || !projectState.selectedTarget
          }
          isBuilding={isBuilding}
        />
      </div>

      {/* Tab bar + panel content */}
      <TabBar activeTab={activeTab} onTabChange={setActiveTab} />
      <div className="sidebar-tab-content">
        {panelMap[activeTab]}
      </div>

      {/* Resizable builds pane at bottom */}
      <BuildQueuePane builds={projectBuilds} />
    </div>
  );
}

render(App);
