import { useEffect, useMemo, useState } from "react";
import { render, logoUrl } from "../shared/render";
import { WebviewRpcClient, rpcClient } from "../shared/rpcClient";
import type { Build } from "../../shared/types";
import { Spinner, Button, Alert, AlertTitle, AlertDescription } from "../shared/components";
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
import { Settings } from "lucide-react";
import "./sidebar.css";

const POST_CONNECT_DISCONNECT_GRACE_MS = 5_000;

function DisconnectedOverlay({
  isConnected,
  startupError,
  connected,
}: {
  isConnected: boolean;
  startupError: string | null;
  connected: boolean;
}) {
  const [hasEverConnected, setHasEverConnected] = useState(false);
  const [show, setShow] = useState(false);

  useEffect(() => {
    if (isConnected) {
      setHasEverConnected(true);
      setShow(false);
      return;
    }
    if (startupError) {
      setShow(true);
      return;
    }
    if (!hasEverConnected) {
      return;
    }
    const timeoutId = window.setTimeout(() => {
      setShow(true);
    }, POST_CONNECT_DISCONNECT_GRACE_MS);
    return () => window.clearTimeout(timeoutId);
  }, [isConnected, hasEverConnected, startupError]);

  if (isConnected || !show) return null;

  return (
    <div className="disconnected-overlay">
      <Alert variant={startupError ? "destructive" : "warning"}>
        <AlertTitle>
          {startupError ? "Failed to Start" : "Connection Lost"}
        </AlertTitle>
        <AlertDescription>
          {startupError ? (
            <code>{startupError}</code>
          ) : (
            !connected
              ? "Unable to connect to the core server."
              : "Disconnected from the extension bridge."
          )}
        </AlertDescription>
        <AlertDescription>
          Run <code>Restart Extension Host</code> from the command palette.
          Check the <code>atopile</code> output channel for errors.
        </AlertDescription>
        <AlertDescription>
          Need help?{" "}
          <a href="https://discord.gg/CRe5xaDBr3" target="_blank" rel="noopener noreferrer">
            Join our Discord
          </a>
        </AlertDescription>
      </Alert>
    </div>
  );
}

function App() {
  const projectState = WebviewRpcClient.useSubscribe("projectState");
  const projects = WebviewRpcClient.useSubscribe("projects");
  const connected = WebviewRpcClient.useSubscribe("connected");
  const coreStatus = WebviewRpcClient.useSubscribe("coreStatus");
  const currentBuilds = WebviewRpcClient.useSubscribe("currentBuilds");
  const previousBuilds = WebviewRpcClient.useSubscribe("previousBuilds");

  const [activeTab, setActiveTab] = useState<TabId>("files");

  const isConnected = connected;
  const startupError = coreStatus.error;
  const [hasEverConnected, setHasEverConnected] = useState(false);

  useEffect(() => {
    if (isConnected) {
      setHasEverConnected(true);
    }
  }, [isConnected]);

  const targets = useMemo(() => {
    const match = projects.find(
      (p) => p.root === projectState.selectedProject,
    );
    return match?.targets ?? [];
  }, [
    projects,
    projectState.selectedProject,
  ]);

  const projectBuilds = useMemo(() => {
    const project = projectState.selectedProject;
    // Active builds for this project
    const active = currentBuilds.filter((b) => b.projectRoot === project);
    const activeTargets = new Set(active.map((b) => b.name));

    // For targets without an active build, pick the latest previous build
    const latestPrevious = new Map<string, Build>();
    for (const b of previousBuilds) {
      if (b.projectRoot === project && !activeTargets.has(b.name) && !latestPrevious.has(b.name)) {
        latestPrevious.set(b.name, b);
      }
    }

    return [...active, ...latestPrevious.values()].map((b) => ({
      ...b,
      currentStage: getCurrentStage(b),
    }));
  }, [currentBuilds, previousBuilds, projectState.selectedProject]);

  const isBuilding = useMemo(
    () =>
      projectBuilds.some(
        (b) =>
          (b.status === "queued" || b.status === "building") &&
          b.name === projectState.selectedTarget,
      ),
    [projectBuilds, projectState.selectedTarget],
  );

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
      {/* Header: logo + title + version badge + settings */}
      <div className="sidebar-header">
        {logoUrl && (
          <img src={logoUrl} alt="atopile" className="sidebar-logo" />
        )}
        <span className="sidebar-title">atopile</span>
        {coreStatus.version && <span className="version-badge">v{coreStatus.version}</span>}
        <Button
          variant="ghost"
          size="icon"
          title="Settings"
          style={{ marginLeft: "auto" }}
          onClick={() => {
            void rpcClient?.requestAction("vscode.openPanel", { panelId: "panel-settings" });
          }}
        >
          <Settings size={14} />
        </Button>
      </div>

      {!isConnected && !hasEverConnected ? (
        <div className="sidebar-status">
          <Spinner size={14} />
          <span>Connecting...</span>
        </div>
      ) : (
        <>
          {/* Top section: selectors + action bar */}
          <div className="sidebar-top">
            <ProjectTargetSelector
              projects={projects}
              selectedProject={projectState.selectedProject}
              onSelectProject={(root) =>
                rpcClient?.sendAction("selectProject", { projectRoot: root })
              }
              targets={targets}
              selectedTarget={projectState.selectedTarget}
              onSelectTarget={(target) =>
                rpcClient?.sendAction("selectTarget", { target })
              }
            />
            <ActionBar
              onBuild={() =>
                rpcClient?.sendAction("startBuild", {
                  projectRoot: projectState.selectedProject,
                  targets: [projectState.selectedTarget],
                })
              }
              onOpenKicad={() =>
                void rpcClient?.requestAction("vscode.openKicad", {
                  projectRoot: projectState.selectedProject,
                  target: projectState.selectedTarget,
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
        </>
      )}

      <DisconnectedOverlay
        isConnected={isConnected}
        startupError={startupError}
        connected={connected}
      />
    </div>
  );
}

render(App);
