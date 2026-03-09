import { useState, useEffect, useMemo, useCallback } from "react";
import {
  ClipboardList,
  ChevronRight,
  AlertTriangle,
  ExternalLink,
} from "lucide-react";
import {
  EmptyState,
  CenteredSpinner,
  PanelSearchBox,
  Badge,
} from "../shared/components";
import { WebviewRpcClient, rpcClient } from "../shared/rpcClient";
import type { UiBOMComponent, UiBOMUsage } from "../../shared/generated-types";
import "./BOMPanel.css";

function typeBadgeVariant(type: string | null): string {
  switch (type?.toUpperCase()) {
    case "R": return "bom-type-R";
    case "C": return "bom-type-C";
    case "L": return "bom-type-L";
    case "IC": return "bom-type-IC";
    default: return "";
  }
}

function UsageRow({ usage }: { usage: UiBOMUsage }) {
  const handleGoTo = useCallback(() => {
    if (usage.file) {
      void rpcClient?.requestAction("vscode.openFile", { path: usage.file });
    }
  }, [usage.file]);

  return (
    <div className="bom-usage-row">
      <span className="bom-usage-module">{usage.module}</span>
      <span className="bom-usage-instance">{usage.instance}</span>
      {usage.file && (
        <span className="bom-usage-link" onClick={handleGoTo}>
          Go to source
        </span>
      )}
    </div>
  );
}

function BOMComponentRow({ component }: { component: UiBOMComponent }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="bom-component">
      <div className="bom-component-header" onClick={() => setExpanded(!expanded)}>
        <span className={`bom-chevron${expanded ? " expanded" : ""}`}>
          <ChevronRight size={14} />
        </span>
        {component.type && (
          <Badge variant="secondary" className={`bom-type-badge ${typeBadgeVariant(component.type)}`}>
            {component.type}
          </Badge>
        )}
        <span className="bom-component-mpn">{component.mpn || component.description}</span>
        <Badge variant="secondary" className="bom-component-qty">x{component.quantity}</Badge>
        {component.value && (
          <span className="bom-component-value">{component.value}</span>
        )}
      </div>
      {expanded && (
        <div className="bom-detail">
          <div className="bom-detail-grid">
            <span className="bom-detail-label">Manufacturer</span>
            <span className="bom-detail-value">{component.manufacturer}</span>
            <span className="bom-detail-label">MPN</span>
            <span className="bom-detail-value">{component.mpn}</span>
            {component.packageName && (
              <>
                <span className="bom-detail-label">Package</span>
                <span className="bom-detail-value">{component.packageName}</span>
              </>
            )}
            {component.lcsc && (
              <>
                <span className="bom-detail-label">LCSC</span>
                <span className="bom-detail-value">
                  <a
                    href={`https://jlcpcb.com/partdetail/${component.lcsc}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ color: "var(--accent)" }}
                  >
                    {component.lcsc} <ExternalLink size={10} style={{ verticalAlign: "middle" }} />
                  </a>
                </span>
              </>
            )}
            {component.stock != null && (
              <>
                <span className="bom-detail-label">Stock</span>
                <span className={`bom-detail-value ${component.stock > 0 ? "bom-stock-ok" : "bom-stock-none"}`}>
                  {component.stock.toLocaleString()}
                </span>
              </>
            )}
            {component.unitCost != null && (
              <>
                <span className="bom-detail-label">Unit Cost</span>
                <span className="bom-detail-value">${component.unitCost.toFixed(4)}</span>
              </>
            )}
          </div>

          {component.parameters.length > 0 && (
            <div className="bom-params">
              <div className="bom-params-title">Parameters</div>
              {component.parameters.map((p) => (
                <div key={p.name} className="bom-param-row">
                  <span className="bom-param-name">{p.name}</span>
                  <span className="bom-param-value">{p.value}</span>
                </div>
              ))}
            </div>
          )}

          {component.usages.length > 0 && (
            <div className="bom-usages">
              <div className="bom-usages-title">Used in ({component.usages.length})</div>
              {component.usages.map((u, i) => (
                <UsageRow key={i} usage={u} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function BOMPanel() {
  const { selectedProject: projectRoot, selectedTarget } = WebviewRpcClient.useSubscribe("projectState");
  const bomData = WebviewRpcClient.useSubscribe("bomData");
  const currentBuilds = WebviewRpcClient.useSubscribe("currentBuilds");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);

  const target = selectedTarget ?? "default";

  useEffect(() => {
    if (projectRoot) {
      setLoading(true);
      rpcClient?.sendAction("getBom", { projectRoot, target });
    }
  }, [projectRoot, target]);

  // Refresh after build completes
  useEffect(() => {
    if (
      projectRoot &&
      currentBuilds.every((b) => b.status !== "building" && b.status !== "queued")
    ) {
      rpcClient?.sendAction("getBom", { projectRoot, target });
    }
  }, [currentBuilds, projectRoot, target]);

  useEffect(() => {
    if (bomData.components.length > 0) setLoading(false);
  }, [bomData.components]);

  const filtered = useMemo(() => {
    if (!search) return bomData.components;
    const q = search.toLowerCase();
    return bomData.components.filter(
      (c) =>
        c.mpn.toLowerCase().includes(q) ||
        c.description.toLowerCase().includes(q) ||
        (c.value?.toLowerCase().includes(q) ?? false) ||
        (c.lcsc?.toLowerCase().includes(q) ?? false) ||
        (c.type?.toLowerCase().includes(q) ?? false) ||
        c.manufacturer.toLowerCase().includes(q),
    );
  }, [bomData.components, search]);

  if (!projectRoot) {
    return (
      <EmptyState
        icon={<ClipboardList size={24} />}
        title="No project selected"
        description="Select a project to view the bill of materials"
      />
    );
  }

  if (!loading && bomData.components.length === 0) {
    return (
      <EmptyState
        icon={<ClipboardList size={24} />}
        title="No BOM available"
        description="Run a build to generate the bill of materials"
      />
    );
  }

  return (
    <div className="sidebar-panel">
      <div className="bom-summary">
        <div className="bom-summary-item">
          <span className="bom-summary-value">{bomData.uniqueParts}</span> parts
        </div>
        <div className="bom-summary-item">
          <span className="bom-summary-value">{bomData.totalQuantity}</span> total
        </div>
        {bomData.estimatedCost != null && (
          <div className="bom-summary-item">
            ~$<span className="bom-summary-value">{bomData.estimatedCost.toFixed(2)}</span>
          </div>
        )}
        {bomData.outOfStock > 0 && (
          <div className="bom-summary-item bom-summary-warning">
            <AlertTriangle size={12} />
            <span>{bomData.outOfStock} out of stock</span>
          </div>
        )}
      </div>
      <PanelSearchBox value={search} onChange={setSearch} placeholder="Search BOM..." />
      <div className="sidebar-panel-scroll">
        {loading ? (
          <CenteredSpinner />
        ) : filtered.length === 0 ? (
          <EmptyState title="No matches" description={`No components match "${search}"`} />
        ) : (
          filtered.map((comp, i) => (
            <BOMComponentRow key={`${comp.mpn}-${i}`} component={comp} />
          ))
        )}
      </div>
    </div>
  );
}
