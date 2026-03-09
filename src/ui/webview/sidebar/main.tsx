import { useEffect, useMemo, useState } from "react";
import { render } from "../shared/render";
import { WebviewRpcClient, rpcClient } from "../shared/rpcClient";
import { createWebviewLogger } from "../shared/logger";
import type { Build } from "../../shared/generated-types";
import { Spinner, Alert, AlertTitle, AlertDescription } from "../shared/components";
import { getCurrentStage } from "../shared/utils";
import { BuildQueuePane } from "./BuildQueuePane";
import { ProjectTargetSelector } from "./ProjectTargetSelector";
import { ActionBar } from "./ActionBar";
import { SidebarHeader } from "./SidebarHeader";
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
import { PackageDetailPanel } from "../sidebar-details/PackageDetailPanel";
import { PartsDetailPanel } from "../sidebar-details/PartsDetailPanel";
import { MigrateDialog } from "../sidebar-details/MigrateDialog";
import "./sidebar.css";

const POST_CONNECT_DISCONNECT_GRACE_MS = 5_000;
const logger = createWebviewLogger("Sidebar");

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
  const sidebarDetails = WebviewRpcClient.useSubscribe("sidebarDetails");
  const structureData = WebviewRpcClient.useSubscribe("structureData");

  const [activeTab, setActiveTab] = useState<TabId>("files");
  const [isPackageInstalling, setIsPackageInstalling] = useState(false);

  const isConnected = connected;
  const startupError = coreStatus.error;
  const [hasEverConnected, setHasEverConnected] = useState(false);

  useEffect(() => {
    if (isConnected) {
      setHasEverConnected(true);
    }
  }, [isConnected]);

  const selectedProject = useMemo(
    () => projects.find((project) => project.root === projectState.selectedProject) ?? null,
    [projects, projectState.selectedProject],
  );

  useEffect(() => {
    const firstProject = projects[0];
    if (!firstProject) {
      return;
    }

    if (!projectState.selectedProject) {
      rpcClient?.sendAction("selectProject", { projectRoot: firstProject.root });
      return;
    }

    if (!selectedProject) {
      return;
    }

    const firstTarget = selectedProject.targets[0]?.name;
    const hasSelectedTarget = selectedProject.targets.some(
      (target) => target.name === projectState.selectedTarget,
    );
    if (!hasSelectedTarget && firstTarget) {
      rpcClient?.sendAction("selectTarget", { target: firstTarget });
    }
  }, [projects, projectState.selectedTarget, selectedProject]);

  useEffect(() => {
    if (!projectState.selectedProject) {
      return;
    }
    rpcClient?.sendAction("getStructure", { projectRoot: projectState.selectedProject });
  }, [projectState.selectedProject]);

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

  const detailContent = useMemo(() => {
    switch (sidebarDetails.view) {
      case "package":
        if (!sidebarDetails.package.summary) {
          return null;
        }
        return (
          <PackageDetailPanel
            package={{
              name: sidebarDetails.package.summary.name,
              fullName: sidebarDetails.package.summary.identifier,
              version: sidebarDetails.package.summary.version ?? undefined,
              description: sidebarDetails.package.summary.description ?? undefined,
              installed: sidebarDetails.package.summary.installed,
              availableVersions: sidebarDetails.package.details?.versions.map((version) => ({
                version: version.version,
                released: version.releasedAt ?? "",
              })),
              homepage: sidebarDetails.package.summary.homepage ?? undefined,
              repository: sidebarDetails.package.summary.repository ?? undefined,
            }}
            packageDetails={sidebarDetails.package.details}
            isLoading={sidebarDetails.package.loading}
            isInstalling={isPackageInstalling}
            installError={sidebarDetails.package.actionError}
            error={sidebarDetails.package.error}
            onClose={() => rpcClient?.sendAction("closeSidebarDetails")}
            onInstall={(version) => {
              setIsPackageInstalling(true);
              rpcClient?.sendAction("installPackage", {
                projectRoot: sidebarDetails.package.projectRoot,
                packageId: sidebarDetails.package.summary?.identifier,
                version,
              });
            }}
            onUninstall={() => {
              setIsPackageInstalling(true);
              rpcClient?.sendAction("removePackage", {
                projectRoot: sidebarDetails.package.projectRoot,
                packageId: sidebarDetails.package.summary?.identifier,
              });
            }}
          />
        );
      case "part":
        if (!sidebarDetails.part.part) {
          return null;
        }
        return (
          <PartsDetailPanel
            part={sidebarDetails.part.part}
            projectRoot={sidebarDetails.part.projectRoot}
            onClose={() => rpcClient?.sendAction("closeSidebarDetails")}
          />
        );
      case "migration":
        if (!sidebarDetails.migration.projectRoot) {
          return null;
        }
        return (
          <MigrateDialog
            projectRoot={sidebarDetails.migration.projectRoot}
            actualVersion={coreStatus.version}
            onClose={() => rpcClient?.sendAction("closeSidebarDetails")}
          />
        );
      default:
        return null;
    }
  }, [coreStatus.version, isPackageInstalling, sidebarDetails]);

  useEffect(() => {
    if (!sidebarDetails.package.loading) {
      setIsPackageInstalling(false);
    }
  }, [sidebarDetails.package.loading, sidebarDetails.package.details?.installedVersion, sidebarDetails.package.actionError]);

  return (
    <div className="sidebar">
      <SidebarHeader
        coreStatus={coreStatus}
        connected={connected}
      />

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
              modules={structureData.modules}
              selectedProject={projectState.selectedProject}
              onSelectProject={(root) =>
                rpcClient?.sendAction("selectProject", { projectRoot: root })
              }
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
              onOpenManufacture={() => {
                logger.info("openPanel click panelId=panel-manufacture");
                void rpcClient?.requestAction("vscode.openPanel", {
                  panelId: "panel-manufacture",
                });
              }}
              buildDisabled={
                !projectState.selectedProject ||
                !projectState.selectedTarget ||
                Boolean(selectedProject?.needsMigration)
              }
              isBuilding={isBuilding}
              showMigration={Boolean(selectedProject?.needsMigration && projectState.selectedProject)}
              onOpenMigration={() => {
                if (!projectState.selectedProject) return;
                rpcClient?.sendAction("showMigrationDetails", {
                  projectRoot: projectState.selectedProject,
                });
              }}
            />
          </div>

          {detailContent ? (
            <div className="sidebar-tab-content sidebar-tab-content-detail">
              {detailContent}
            </div>
          ) : (
            <>
              <TabBar activeTab={activeTab} onTabChange={setActiveTab} />
              <div className="sidebar-tab-content">
                {panelMap[activeTab]}
              </div>
            </>
          )}

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
