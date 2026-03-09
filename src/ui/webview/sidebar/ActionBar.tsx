import { Hammer, Compass, Box, Layout, Code, RefreshCcw } from "lucide-react";
import { Button, Spinner } from "../shared/components";
import { rpcClient } from "../shared/rpcClient";
import "./ActionBar.css";

interface ActionBarProps {
  onBuild: () => void;
  onOpenKicad: () => void;
  buildDisabled: boolean;
  isBuilding: boolean;
  showMigration: boolean;
  onOpenMigration: () => void;
}

export function ActionBar({
  onBuild,
  onOpenKicad,
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
          onClick={() => {
            void rpcClient?.requestAction("vscode.openPanel", { panelId: "panel-layout" });
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
          onClick={() => {
            void rpcClient?.requestAction("vscode.openPanel", { panelId: "panel-3d" });
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
          onClick={onOpenKicad}
        >
          <Compass size={12} />
          <span className="action-label">KiCad</span>
        </Button>

        <div className="action-divider" />

        {/* Developer — wired */}
        <Button
          variant="ghost"
          size="sm"
          className="action-btn"
          onClick={() => {
            void rpcClient?.requestAction("vscode.openPanel", { panelId: "panel-developer" });
          }}
        >
          <Code size={12} />
          <span className="action-label">Developer</span>
        </Button>
      </div>
    </div>
  );
}
