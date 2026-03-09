import { useState, useEffect, useMemo, useCallback } from "react";
import { Package, Download, Trash2 } from "lucide-react";
import {
  EmptyState,
  CenteredSpinner,
  Spinner,
  PanelSearchBox,
  PanelTabs,
  Badge,
  Button,
} from "../shared/components";
import { formatDownloads } from "../shared/utils/packageUtils";
import { WebviewRpcClient, rpcClient } from "../shared/rpcClient";
import type { PackageSummaryItem } from "../../shared/generated-types";
import "./PackagesPanel.css";

type Tab = "browse" | "project";

function PackageRow({
  pkg,
  projectRoot,
  tab,
}: {
  pkg: PackageSummaryItem;
  projectRoot: string;
  tab: Tab;
}) {
  const [busy, setBusy] = useState(false);

  const handleInstall = useCallback(() => {
    setBusy(true);
    rpcClient?.sendAction("installPackage", {
      projectRoot,
      packageId: pkg.identifier,
    });
    setTimeout(() => setBusy(false), 5000);
  }, [projectRoot, pkg.identifier]);

  const handleRemove = useCallback(() => {
    setBusy(true);
    rpcClient?.sendAction("removePackage", {
      projectRoot,
      packageId: pkg.identifier,
    });
    setTimeout(() => setBusy(false), 5000);
  }, [projectRoot, pkg.identifier]);

  const openDetails = useCallback(() => {
    rpcClient?.sendAction("showPackageDetails", {
      projectRoot,
      packageId: pkg.identifier,
    });
  }, [projectRoot, pkg.identifier]);

  return (
    <div
      className="card-row"
      role="button"
      tabIndex={0}
      onClick={openDetails}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          openDetails();
        }
      }}
    >
      <div className="card-row-top">
        <span className="card-row-name">{pkg.name}</span>
        <span className="card-row-secondary">{pkg.publisher}</span>
        <div className="card-row-actions">
          {busy ? (
            <Spinner size={12} />
          ) : tab === "browse" ? (
            pkg.installed ? (
              <Badge variant="success">Installed</Badge>
            ) : (
              <Button size="sm" variant="outline" onClick={(event) => {
                event.stopPropagation();
                handleInstall();
              }}>
                <Download size={12} /> Install
              </Button>
            )
          ) : (
            <Button size="sm" variant="ghost" onClick={(event) => {
              event.stopPropagation();
              handleRemove();
            }}>
              <Trash2 size={12} />
            </Button>
          )}
        </div>
      </div>
      {pkg.summary && <div className="card-row-description">{pkg.summary}</div>}
      <div className="card-row-meta">
        {pkg.version && (
          <span className="package-version-info">
            v{pkg.version}
            {pkg.hasUpdate && (
              <>
                <span className="package-update-dot" title="Update available" />
                <span>{pkg.latestVersion}</span>
              </>
            )}
          </span>
        )}
        {pkg.downloads != null && (
          <span>{formatDownloads(pkg.downloads)} downloads</span>
        )}
      </div>
    </div>
  );
}

export function PackagesPanel() {
  const { selectedProject: projectRoot } = WebviewRpcClient.useSubscribe("projectState");
  const packagesSummary = WebviewRpcClient.useSubscribe("packagesSummary");
  const [tab, setTab] = useState<Tab>("browse");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);

  const tabs = useMemo(() => [
    { key: "browse", label: "Browse" },
    { key: "project", label: `Project (${packagesSummary.installedCount})` },
  ], [packagesSummary.installedCount]);

  useEffect(() => {
    if (projectRoot) {
      setLoading(true);
      rpcClient?.sendAction("getPackagesSummary", { projectRoot });
    }
  }, [projectRoot]);

  useEffect(() => {
    if (packagesSummary.packages.length > 0 || packagesSummary.total > 0) {
      setLoading(false);
    }
  }, [packagesSummary]);

  const filtered = useMemo(() => {
    let items = packagesSummary.packages;
    if (tab === "project") {
      items = items.filter((p) => p.installed);
    }
    if (!search) return items;
    const q = search.toLowerCase();
    return items.filter(
      (p) =>
        p.name.toLowerCase().includes(q) ||
        p.publisher.toLowerCase().includes(q) ||
        (p.summary?.toLowerCase().includes(q) ?? false),
    );
  }, [packagesSummary.packages, tab, search]);

  if (!projectRoot) {
    return (
      <EmptyState
        icon={<Package size={24} />}
        title="No project selected"
        description="Select a project to browse packages"
      />
    );
  }

  return (
    <div className="sidebar-panel">
      <PanelTabs tabs={tabs} activeTab={tab} onTabChange={(k) => setTab(k as Tab)} />
      <PanelSearchBox value={search} onChange={setSearch} placeholder="Search packages..." />
      <div className="sidebar-panel-scroll">
        {loading ? (
          <CenteredSpinner />
        ) : filtered.length === 0 ? (
          <EmptyState
            title={search ? "No matches" : "No packages"}
            description={search ? `No packages match "${search}"` : undefined}
          />
        ) : (
          filtered.map((pkg) => (
            <PackageRow
              key={pkg.identifier}
              pkg={pkg}
              projectRoot={projectRoot}
              tab={tab}
            />
          ))
        )}
      </div>
    </div>
  );
}
