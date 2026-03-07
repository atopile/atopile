import { useState, useEffect, useMemo, useCallback, useRef } from "react";
import { Cpu, Download, Trash2, Search } from "lucide-react";
import {
  EmptyState,
  CenteredSpinner,
  PanelSearchBox,
  PanelTabs,
  Button,
  Spinner,
} from "../shared/components";
import { WebviewRpcClient, rpcClient } from "../shared/rpcClient";
import type { PartSearchItem, InstalledPartItem } from "../../shared/types";
import "./PartsPanel.css";

type Tab = "find" | "project";

function stockClass(stock: number): string {
  if (stock <= 0) return "part-stock-none";
  if (stock < 100) return "part-stock-low";
  return "part-stock-ok";
}

function SearchResultRow({
  part,
  projectRoot,
}: {
  part: PartSearchItem;
  projectRoot: string;
}) {
  const [busy, setBusy] = useState(false);

  const handleInstall = useCallback(() => {
    setBusy(true);
    rpcClient?.sendAction("installPart", {
      projectRoot,
      lcsc: part.lcsc,
    });
    setTimeout(() => setBusy(false), 5000);
  }, [projectRoot, part.lcsc]);

  return (
    <div className="card-row">
      <div className="card-row-top">
        <span className="card-row-name">{part.mpn || part.lcsc}</span>
        <span className="card-row-secondary">{part.manufacturer}</span>
        <div className="card-row-actions">
          {busy ? (
            <Spinner size={12} />
          ) : (
            <Button size="sm" variant="outline" onClick={handleInstall}>
              <Download size={12} />
            </Button>
          )}
        </div>
      </div>
      <div className="card-row-description">{part.description}</div>
      <div className="card-row-meta">
        <span className={stockClass(part.stock)}>
          Stock: {part.stock.toLocaleString()}
        </span>
        {part.unit_cost != null && <span>${part.unit_cost.toFixed(4)}</span>}
        <span>{part.lcsc}</span>
      </div>
    </div>
  );
}

function InstalledPartRow({
  part,
  projectRoot,
}: {
  part: InstalledPartItem;
  projectRoot: string;
}) {
  const [busy, setBusy] = useState(false);

  const handleUninstall = useCallback(() => {
    setBusy(true);
    rpcClient?.sendAction("uninstallPart", {
      projectRoot,
      lcsc: part.lcsc ?? "",
    });
    setTimeout(() => setBusy(false), 5000);
  }, [projectRoot, part.lcsc]);

  return (
    <div className="card-row">
      <div className="card-row-top">
        <span className="card-row-name">{part.mpn || part.identifier}</span>
        <span className="card-row-secondary">{part.manufacturer}</span>
        <div className="card-row-actions">
          {busy ? (
            <Spinner size={12} />
          ) : (
            <Button size="sm" variant="ghost" onClick={handleUninstall}>
              <Trash2 size={12} />
            </Button>
          )}
        </div>
      </div>
      <div className="card-row-description">{part.description}</div>
      <div className="card-row-meta">
        {part.lcsc && <span>{part.lcsc}</span>}
      </div>
    </div>
  );
}

export function PartsPanel() {
  const { selectedProject: projectRoot } = WebviewRpcClient.useSubscribe("projectState");
  const partsSearch = WebviewRpcClient.useSubscribe("partsSearch");
  const installedParts = WebviewRpcClient.useSubscribe("installedParts");
  const [tab, setTab] = useState<Tab>("find");
  const [query, setQuery] = useState("");
  const [searching, setSearching] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  const tabs = useMemo(() => [
    { key: "find", label: "Find Parts" },
    { key: "project", label: `Project (${installedParts.parts.length})` },
  ], [installedParts.parts.length]);

  // Debounced search
  useEffect(() => {
    if (!query.trim()) {
      setSearching(false);
      return;
    }
    setSearching(true);
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      rpcClient?.sendAction("searchParts", { query: query.trim(), limit: 50 });
    }, 250);
    return () => clearTimeout(debounceRef.current);
  }, [query]);

  useEffect(() => {
    if (partsSearch.parts.length > 0 || partsSearch.error) {
      setSearching(false);
    }
  }, [partsSearch]);

  // Load installed parts on project tab
  useEffect(() => {
    if (tab === "project" && projectRoot) {
      rpcClient?.sendAction("getInstalledParts", { projectRoot });
    }
  }, [tab, projectRoot]);

  if (!projectRoot) {
    return (
      <EmptyState
        icon={<Cpu size={24} />}
        title="No project selected"
        description="Select a project to search and manage parts"
      />
    );
  }

  return (
    <div className="sidebar-panel">
      <PanelTabs tabs={tabs} activeTab={tab} onTabChange={(k) => setTab(k as Tab)} />

      {tab === "find" ? (
        <>
          <PanelSearchBox
            value={query}
            onChange={setQuery}
            placeholder="Search by MPN, LCSC ID, or description..."
          />
          <div className="sidebar-panel-scroll">
            {!query.trim() ? (
              <EmptyState
                icon={<Search size={24} />}
                title="Search for parts"
                description="Enter an MPN, LCSC number, or description to search"
              />
            ) : searching ? (
              <CenteredSpinner />
            ) : partsSearch.error ? (
              <EmptyState title="Search error" description={partsSearch.error} />
            ) : partsSearch.parts.length === 0 ? (
              <EmptyState title="No results" description={`No parts found for "${query}"`} />
            ) : (
              partsSearch.parts.map((part) => (
                <SearchResultRow
                  key={part.lcsc}
                  part={part}
                  projectRoot={projectRoot}
                />
              ))
            )}
          </div>
        </>
      ) : (
        <div className="sidebar-panel-scroll">
          {installedParts.parts.length === 0 ? (
            <EmptyState
              icon={<Cpu size={24} />}
              title="No installed parts"
              description="Search and install parts from the Find Parts tab"
            />
          ) : (
            installedParts.parts.map((part) => (
              <InstalledPartRow
                key={part.identifier}
                part={part}
                projectRoot={projectRoot}
              />
            ))
          )}
        </div>
      )}
    </div>
  );
}
