import { Hammer, Compass, Box, Layout, Factory, RefreshCcw } from "lucide-react";
import { Button, Spinner } from "../shared/components";
import { rpcClient } from "../shared/rpcClient";
import { createWebviewLogger } from "../shared/logger";
import "./ActionBar.css";

const logger = createWebviewLogger("Sidebar");

async function requestPanel(panelId: string): Promise<void> {
  logger.info(`openPanel click panelId=${panelId}`);
  try {
    await rpcClient?.requestAction("vscode.openPanel", { panelId });
    logger.info(`openPanel resolved panelId=${panelId}`);
  } catch (error) {
    logger.error(
      `openPanel failed panelId=${panelId} error=${error instanceof Error ? error.message : String(error)}`,
    );
  }
}

interface ActionBarProps {
  onBuild: () => void;
  onOpenKicad: () => void;
  onOpenManufacture: () => void;
  buildDisabled: boolean;
  isBuilding: boolean;
  showMigration: boolean;
  onOpenMigration: () => void;
}

export function ActionBar({
  onBuild,
  onOpenKicad,
  onOpenManufacture,
  buildDisabled,
  isBuilding,
  showMigration,
  onOpenMigration,
}: ActionBarProps) {
  return (
    <div className="action-bar-wrapper">
      <div className="build-actions-row">
        {showMigration ? (
          <>
            <Button
              variant="ghost"
              size="sm"
              className="action-btn"
              onClick={onOpenMigration}
            >
              <RefreshCcw size={12} />
              <span className="action-label">Migrate</span>
            </Button>

            <div className="action-divider" />
          </>
        ) : null}

        {/* Build — wired */}
        <Button
          variant="ghost"
          size="sm"
          className="action-btn primary"
          onClick={onBuild}
          disabled={buildDisabled || isBuilding}
        >
          {isBuilding ? <Spinner size={12} /> : <Hammer size={12} />}
          <span className="action-label">{isBuilding ? "Building" : "Build"}</span>
        </Button>

        <div className="action-divider" />

        <Button
          variant="ghost"
          size="sm"
          className="action-btn"
          disabled={buildDisabled}
          onClick={onOpenKicad}
        >
          <Compass size={12} />
          <span className="action-label">KiCad</span>
        </Button>

        <div className="action-divider" />

        <Button
          variant="ghost"
          size="sm"
          className="action-btn"
          disabled={buildDisabled}
          onClick={() => {
            void requestPanel("panel-3d");
          }}
        >
          <Box size={12} />
          <span className="action-label">3D</span>
        </Button>

        <div className="action-divider" />

        <Button
          variant="ghost"
          size="sm"
          className="action-btn"
          disabled={buildDisabled}
          onClick={() => {
            void requestPanel("panel-layout");
          }}
        >
          <Layout size={12} />
          <span className="action-label">Layout</span>
        </Button>

        <div className="action-divider" />

        <Button
          variant="ghost"
          size="sm"
          className="action-btn"
          disabled={buildDisabled}
          onClick={onOpenManufacture}
        >
          <Factory size={12} />
          <span className="action-label">Manufacture</span>
        </Button>
      </div>
    </div>
  );
}
