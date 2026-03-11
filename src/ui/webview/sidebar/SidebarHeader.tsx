import { useMemo } from "react";
import { AlertCircle, Check, Loader2, Settings, X } from "lucide-react";
import type { UiCoreStatus } from "../../shared/generated-types";
import { logoUrl } from "../shared/render";
import { rpcClient } from "../shared/rpcClient";
import "./SidebarHeader.css";

interface SidebarHeaderProps {
  coreStatus: UiCoreStatus;
  connected: boolean;
}

export function SidebarHeader({
  coreStatus,
  connected,
}: SidebarHeaderProps) {
  const health = useMemo(() => {
    if (!connected) {
      return {
        tone: "error",
        label: "Disconnected",
        icon: <X size={12} />,
      };
    }
    if (coreStatus.error) {
      return {
        tone: "warning",
        label: "Degraded",
        icon: <AlertCircle size={12} />,
      };
    }
    if (!coreStatus.version) {
      return {
        tone: "loading",
        label: "Starting",
        icon: <Loader2 size={12} className="spin" />,
      };
    }
    return {
      tone: "success",
      label: "Healthy",
      icon: <Check size={12} />,
    };
  }, [connected, coreStatus.error, coreStatus.version]);

  return (
    <div className="sidebar-header">
      {logoUrl ? <img src={logoUrl} alt="atopile" className="sidebar-logo" /> : null}
      <span className="sidebar-title">atopile</span>
      {coreStatus.version ? <span className="version-badge">v{coreStatus.version}</span> : null}
      <span className={`sidebar-health sidebar-health-${health.tone}`} title={health.label}>
        {health.icon}
        <span>{health.label}</span>
      </span>

      <button
        type="button"
        className="sidebar-settings-btn"
        title="Settings"
        onClick={() => {
          void rpcClient?.requestAction("vscode.openPanel", { panelId: "panel-settings" });
        }}
      >
        <Settings size={14} />
      </button>
    </div>
  );
}
