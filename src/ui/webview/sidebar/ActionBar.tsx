import { Hammer, Compass, Box, Layout, Code } from "lucide-react";
import { Button, Spinner } from "../shared/components";
import { vscode } from "../shared/vscodeApi";
import "./ActionBar.css";

interface ActionBarProps {
  onBuild: () => void;
  buildDisabled: boolean;
  isBuilding: boolean;
}

export function ActionBar({ onBuild, buildDisabled, isBuilding }: ActionBarProps) {
  return (
    <div className="action-bar-wrapper">
      <div className="build-actions-row">
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

        {/* KiCad — placeholder */}
        <Button variant="ghost" size="sm" className="action-btn" disabled>
          <Compass size={12} />
          <span className="action-label">KiCad</span>
        </Button>

        <div className="action-divider" />

        {/* 3D — placeholder */}
        <Button variant="ghost" size="sm" className="action-btn" disabled>
          <Box size={12} />
          <span className="action-label">3D</span>
        </Button>

        <div className="action-divider" />

        {/* Layout — placeholder */}
        <Button variant="ghost" size="sm" className="action-btn" disabled>
          <Layout size={12} />
          <span className="action-label">Layout</span>
        </Button>

        <div className="action-divider" />

        {/* Developer — wired */}
        <Button
          variant="ghost"
          size="sm"
          className="action-btn"
          onClick={() =>
            vscode.postMessage({ type: "openPanel", panelId: "panel-developer" })
          }
        >
          <Code size={12} />
          <span className="action-label">Developer</span>
        </Button>
      </div>
    </div>
  );
}
