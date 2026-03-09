import { memo, useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  Check,
  ChevronDown,
  ChevronRight,
  Copy,
  ExternalLink,
  Package,
  RefreshCw,
} from "lucide-react";
import { EmptyState, PanelSearchBox } from "../shared/components";
import { WebviewRpcClient, rpcClient } from "../shared/rpcClient";
import type { Build, UiBOMComponent } from "../../shared/generated-types";
import "./BOMPanel.css";

interface LcscPartData {
  manufacturer?: string | null;
  mpn?: string | null;
  description?: string | null;
  stock?: number | null;
  unit_cost?: number | null;
  is_basic?: boolean | null;
  is_preferred?: boolean | null;
}

interface UsageLocation {
  path: string;
  designator: string;
  line?: number;
}

interface UsageGroup {
  parentPath: string;
  parentLabel: string;
  instances: UsageLocation[];
}

interface BOMComponentUI {
  id: string;
  type: string;
  value: string;
  package: string;
  manufacturer?: string;
  mpn?: string;
  lcsc?: string;
  description?: string;
  quantity: number;
  unitCost?: number;
  totalCost?: number;
  inStock?: boolean;
  stockQuantity?: number;
  isBasic?: boolean;
  isPreferred?: boolean;
  lcscLoading?: boolean;
  parameters: UiBOMComponent["parameters"];
  source?: string;
  usages: UsageLocation[];
}

function normalizeUsagePath(path: string): string {
  const parts = path.split("::");
  const addressPart = parts.length > 1 ? parts[1] : path;
  return addressPart.split("|")[0] ?? addressPart;
}

function getUsageDisplayPath(path: string): string {
  const normalized = normalizeUsagePath(path);
  const segments = normalized.split(".");
  if (segments.length <= 1) {
    return normalized;
  }
  return segments.slice(1).join(".");
}

function resolveUsageFilePath(projectRoot: string | null, path: string): string | null {
  if (!path) {
    return null;
  }
  const primary = path.split("|")[0] ?? path;
  const filePart = primary.split("::")[0] ?? "";
  if (!filePart.endsWith(".ato")) {
    return null;
  }
  if (filePart.startsWith("/") || /^[A-Za-z]:[\\/]/.test(filePart)) {
    return filePart;
  }
  if (!projectRoot) {
    return filePart;
  }
  const separator = projectRoot.includes("\\") ? "\\" : "/";
  return `${projectRoot.replace(/[\\/]+$/, "")}${separator}${filePart.replace(/^[\\/]+/, "")}`;
}

function transformBOMComponent(apiComp: UiBOMComponent): BOMComponentUI {
  const unitCost = apiComp.unitCost ?? undefined;
  const totalCost = unitCost !== undefined ? unitCost * apiComp.quantity : undefined;
  const stock = apiComp.stock ?? undefined;

  return {
    id: apiComp.id,
    type: apiComp.type ?? "other",
    value: apiComp.value || apiComp.description || apiComp.mpn || apiComp.manufacturer || "-",
    package: apiComp.package,
    manufacturer: apiComp.manufacturer || undefined,
    mpn: apiComp.mpn || undefined,
    lcsc: apiComp.lcsc || undefined,
    description: apiComp.description || undefined,
    quantity: apiComp.quantity,
    unitCost,
    totalCost,
    inStock: stock != null ? stock > 0 : undefined,
    stockQuantity: stock,
    isBasic: apiComp.isBasic ?? undefined,
    isPreferred: apiComp.isPreferred ?? undefined,
    parameters: apiComp.parameters,
    source: apiComp.source || undefined,
    usages: apiComp.usages.map((usage) => ({
      path: usage.address,
      designator: usage.designator,
      line: usage.line ?? undefined,
    })),
  };
}

function getTypeLabel(type: string): string {
  switch (type) {
    case "resistor": return "R";
    case "capacitor": return "C";
    case "inductor": return "L";
    case "ic": return "IC";
    case "connector": return "J";
    case "led": return "LED";
    case "diode": return "D";
    case "transistor": return "Q";
    case "crystal": return "Y";
    default: return "X";
  }
}

function formatCurrency(value: number): string {
  if (value < 0.01) {
    return `$${value.toFixed(4)}`;
  }
  if (value < 1) {
    return `$${value.toFixed(3)}`;
  }
  return `$${value.toFixed(2)}`;
}

function groupUsagesByModule(usages: UsageLocation[]): UsageGroup[] {
  const groups = new Map<string, UsageGroup>();

  for (const usage of usages) {
    const normalizedPath = normalizeUsagePath(usage.path);
    const segments = normalizedPath.split(".");

    let parentPath: string;
    let parentLabel: string;

    if (segments.length >= 3) {
      parentPath = segments.slice(0, -1).join(".");
      parentLabel = segments[segments.length - 2] ?? normalizedPath;
    } else if (segments.length === 2) {
      parentPath = segments[0] ?? normalizedPath;
      parentLabel = segments[0] ?? normalizedPath;
    } else {
      parentPath = normalizedPath;
      parentLabel = normalizedPath;
    }

    const group = groups.get(parentPath) ?? {
      parentPath,
      parentLabel,
      instances: [],
    };
    group.instances.push(usage);
    groups.set(parentPath, group);
  }

  return Array.from(groups.values());
}

function formatStock(stock: number): string {
  if (stock >= 1_000_000) {
    return `${(stock / 1_000_000).toFixed(1)}M`;
  }
  if (stock >= 1_000) {
    return `${(stock / 1_000).toFixed(0)}K`;
  }
  return stock.toString();
}

const BOMRow = memo(function BOMRow({
  component,
  isExpanded,
  onToggle,
  onCopy,
  onGoToSource,
}: {
  component: BOMComponentUI;
  isExpanded: boolean;
  onToggle: () => void;
  onCopy: (text: string) => void;
  onGoToSource: (path: string, line?: number) => void;
}) {
  const [copiedField, setCopiedField] = useState<string | null>(null);
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(() => new Set());

  const handleCopy = (field: string, value: string, event: React.MouseEvent) => {
    event.stopPropagation();
    onCopy(value);
    setCopiedField(field);
    window.setTimeout(() => setCopiedField(null), 1500);
  };

  const handleUsageClick = (event: React.MouseEvent, usage: UsageLocation) => {
    event.stopPropagation();
    onGoToSource(usage.path, usage.line);
  };

  const toggleGroup = (groupPath: string, event: React.MouseEvent) => {
    event.stopPropagation();
    setExpandedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(groupPath)) {
        next.delete(groupPath);
      } else {
        next.add(groupPath);
      }
      return next;
    });
  };

  const usageGroups = component.usages.length > 0 ? groupUsagesByModule(component.usages) : [];

  return (
    <div className={`bom-row ${isExpanded ? "expanded" : ""}`} onClick={onToggle}>
      <div className="bom-row-header">
        <span className="bom-expand">
          {isExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        </span>
        <span className={`bom-type-badge type-${component.type}`}>{getTypeLabel(component.type)}</span>
        <span className="bom-value">{component.value}</span>
        {component.mpn && (
          <span className="bom-mpn" title={component.mpn}>
            {component.mpn}
          </span>
        )}
        <span className="bom-quantity">x{component.quantity}</span>
        {component.totalCost !== undefined && (
          <span className="bom-cost">{formatCurrency(component.totalCost)}</span>
        )}
        {component.inStock === false && <AlertTriangle size={12} className="bom-stock-warning" />}
      </div>

      {isExpanded && (
        <div className="bom-row-details">
          <table className="bom-detail-table">
            <tbody>
              <tr>
                <td className="detail-cell-label">Manufacturer</td>
                <td className="detail-cell-value">{component.manufacturer || "-"}</td>
              </tr>
              <tr>
                <td className="detail-cell-label">Package</td>
                <td className="detail-cell-value">{component.package || "-"}</td>
              </tr>
              <tr>
                <td className="detail-cell-label">LCSC</td>
                <td className="detail-cell-value">
                  {component.lcsc ? (
                    <span
                      className="lcsc-link"
                      onClick={(event) => handleCopy("lcsc", component.lcsc!, event)}
                    >
                      <span className="mono">{component.lcsc}</span>
                      <button
                        type="button"
                        className="external-link"
                        onClick={(event) => {
                          event.stopPropagation();
                          window.open(
                            `https://www.lcsc.com/product-detail/${component.lcsc}.html`,
                            "_blank",
                            "noopener,noreferrer",
                          );
                        }}
                        aria-label="Open LCSC part in browser"
                      >
                        <ExternalLink size={10} />
                      </button>
                      {copiedField === "lcsc" ? (
                        <Check size={10} className="copy-icon copied" />
                      ) : (
                        <Copy size={10} className="copy-icon" />
                      )}
                    </span>
                  ) : "-"}
                </td>
              </tr>
              <tr>
                <td className="detail-cell-label">Stock</td>
                <td className={`detail-cell-value ${component.inStock === false ? "out-of-stock" : "in-stock"}`}>
                  {component.inStock === false ? (
                    <span className="stock-out">
                      <AlertTriangle size={10} />
                      Out of stock
                    </span>
                  ) : component.lcscLoading && component.stockQuantity == null ? (
                    <span className="inline-loading">
                      <RefreshCw size={10} className="loading-spinner" />
                      Fetching...
                    </span>
                  ) : component.stockQuantity != null ? (
                    formatStock(component.stockQuantity)
                  ) : (
                    "In stock"
                  )}
                </td>
              </tr>
              <tr>
                <td className="detail-cell-label">Unit Cost</td>
                <td className="detail-cell-value cost">
                  {component.unitCost != null ? (
                    formatCurrency(component.unitCost)
                  ) : component.lcscLoading ? (
                    <span className="inline-loading">
                      <RefreshCw size={10} className="loading-spinner" />
                      Fetching...
                    </span>
                  ) : (
                    "-"
                  )}
                </td>
              </tr>
              <tr>
                <td className="detail-cell-label">Source</td>
                <td className="detail-cell-value">
                  <span className={`source-badge source-${component.source ?? "manual"}`}>
                    {component.source === "picked"
                      ? "Auto-picked"
                      : component.source === "specified"
                        ? "Specified"
                        : "Manual"}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>

          {usageGroups.length > 0 && (
            <div className="bom-usages-tree">
              <div className="usages-header">
                <span>Used in design</span>
                <span className="usages-count">
                  {component.quantity} instance{component.quantity !== 1 ? "s" : ""}
                </span>
              </div>
              <div className="usage-groups">
                {usageGroups.map((group) => (
                  <div key={group.parentPath} className="usage-group">
                    {group.instances.length > 1 ? (
                      <>
                        <div
                          className="usage-group-header"
                          onClick={(event) => toggleGroup(group.parentPath, event)}
                        >
                          <span className="usage-expand">
                            {expandedGroups.has(group.parentPath) ? (
                              <ChevronDown size={11} />
                            ) : (
                              <ChevronRight size={11} />
                            )}
                          </span>
                          <span className="usage-module-name">{group.parentLabel}</span>
                          <span className="usage-count-badge">x{group.instances.length}</span>
                        </div>
                        {expandedGroups.has(group.parentPath) && (
                          <div className="usage-instances">
                            {group.instances.map((usage, index) => (
                              <div
                                key={`${usage.path}-${index}`}
                                className="usage-instance"
                                onClick={(event) => handleUsageClick(event, usage)}
                                title={usage.path}
                              >
                                <span className="usage-designator">{usage.designator}</span>
                                <span className="usage-leaf">{getUsageDisplayPath(usage.path)}</span>
                                <ExternalLink size={9} className="usage-goto" />
                              </div>
                            ))}
                          </div>
                        )}
                      </>
                    ) : (
                      <div
                        className="usage-single"
                        onClick={(event) => handleUsageClick(event, group.instances[0]!)}
                        title={group.instances[0]!.path}
                      >
                        <span className="usage-designator">{group.instances[0]!.designator}</span>
                        <span className="usage-module-path">
                          {getUsageDisplayPath(group.instances[0]!.path)}
                        </span>
                        <ExternalLink size={10} className="usage-goto" />
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
});

export function BOMPanel() {
  const { selectedProject: projectRoot, selectedTarget } = WebviewRpcClient.useSubscribe("projectState");
  const bomData = WebviewRpcClient.useSubscribe("bomData");
  const currentBuilds = WebviewRpcClient.useSubscribe("currentBuilds");
  const [searchQuery, setSearchQuery] = useState("");
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const [copiedValue, setCopiedValue] = useState<string | null>(null);
  const [lcscParts, setLcscParts] = useState<Record<string, LcscPartData | null>>({});
  const [lcscLoadingIds, setLcscLoadingIds] = useState<Set<string>>(new Set());
  const [latestBuildInfo, setLatestBuildInfo] = useState<Build | null>(null);
  const [forceRefreshBuildId, setForceRefreshBuildId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const lcscRequestIdRef = useRef(0);
  const lastLcscRefreshBuildIdRef = useRef<string | null>(null);

  const target = selectedTarget ?? "default";

  const refreshBom = useCallback(() => {
    if (!projectRoot) {
      setIsLoading(false);
      setError(null);
      return;
    }
    const client = rpcClient;
    if (!client) {
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    setError(null);
    void client
      .requestAction("getBom", { projectRoot, target })
      .catch((requestError: unknown) => {
        setError(requestError instanceof Error ? requestError.message : "Failed to load BOM");
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, [projectRoot, target]);

  useEffect(() => {
    setExpandedIds(new Set());
    setLcscParts({});
    setLcscLoadingIds(new Set());
    setLatestBuildInfo(null);
    setForceRefreshBuildId(null);
    lastLcscRefreshBuildIdRef.current = null;
    refreshBom();
  }, [refreshBom]);

  useEffect(() => {
    if (
      projectRoot &&
      currentBuilds.every((build) => build.status !== "building" && build.status !== "queued")
    ) {
      refreshBom();
    }
  }, [currentBuilds, projectRoot, refreshBom]);

  useEffect(() => {
    if (!projectRoot) {
      return;
    }
    const client = rpcClient;
    if (!client) {
      return;
    }
    void client.requestAction<{ builds: Build[] }>("getBuildsByProject", {
        projectRoot,
        target,
        limit: 1,
      })
      .then((result) => {
        setLatestBuildInfo(result.builds[0] ?? null);
      })
      .catch(() => {
        setLatestBuildInfo(null);
      });
  }, [projectRoot, target]);

  useEffect(() => {
    const buildId = latestBuildInfo?.buildId;
    const startedAt = latestBuildInfo?.startedAt;
    if (!buildId || !startedAt) {
      return;
    }
    const completedAt = startedAt + (latestBuildInfo?.elapsedSeconds ?? 0);
    const ageSeconds = Date.now() / 1000 - completedAt;
    if (ageSeconds <= 24 * 60 * 60) {
      return;
    }
    if (lastLcscRefreshBuildIdRef.current === buildId) {
      return;
    }
    setForceRefreshBuildId(buildId);
  }, [latestBuildInfo]);

  const lcscIds = useMemo(() => {
    const ids = new Set<string>();
    for (const component of bomData.components) {
      if (component.lcsc) {
        ids.add(component.lcsc);
      }
    }
    return Array.from(ids);
  }, [bomData.components]);

  const lcscIdsToFetch = useMemo(() => {
    const ids = new Set<string>();
    for (const component of bomData.components) {
      if (!component.lcsc) {
        continue;
      }
      if (component.unitCost != null && component.stock != null) {
        continue;
      }
      ids.add(component.lcsc);
    }
    return Array.from(ids);
  }, [bomData.components]);

  useEffect(() => {
    const forceRefresh = !!forceRefreshBuildId;
    const idsToRequest = forceRefresh ? lcscIds : lcscIdsToFetch;
    if (!projectRoot || idsToRequest.length === 0) {
      return;
    }
    const missing = forceRefresh
      ? idsToRequest
      : idsToRequest.filter((id) => !(id in lcscParts));
    if (missing.length === 0) {
      return;
    }
    const client = rpcClient;
    if (!client) {
      return;
    }

    const requestId = ++lcscRequestIdRef.current;
    setLcscLoadingIds((prev) => {
      const next = new Set(prev);
      for (const id of missing) {
        next.add(id);
      }
      return next;
    });

    void client.requestAction<{ parts: Record<string, LcscPartData | null> }>("fetchLcscParts", {
        lcscIds: missing,
        projectRoot,
        target,
      })
      .then((result) => {
        if (requestId !== lcscRequestIdRef.current) {
          return;
        }
        setLcscParts((prev) => ({ ...prev, ...result.parts }));
      })
      .catch(() => {
        if (requestId !== lcscRequestIdRef.current) {
          return;
        }
      })
      .finally(() => {
        setLcscLoadingIds((prev) => {
          const next = new Set(prev);
          for (const id of missing) {
            next.delete(id);
          }
          return next;
        });
        if (forceRefresh && latestBuildInfo?.buildId) {
          lastLcscRefreshBuildIdRef.current = latestBuildInfo.buildId;
          setForceRefreshBuildId(null);
        }
      });
  }, [forceRefreshBuildId, latestBuildInfo?.buildId, lcscIds, lcscIdsToFetch, lcscParts, projectRoot, target]);

  const bomComponents = useMemo((): BOMComponentUI[] => {
    return bomData.components.map((component) => {
      const uiComponent = transformBOMComponent(component);
      if (!component.lcsc) {
        return uiComponent;
      }

      const lcscInfo = lcscParts[component.lcsc];
      uiComponent.lcscLoading = lcscLoadingIds.has(component.lcsc);
      if (!lcscInfo) {
        return uiComponent;
      }

      if (uiComponent.unitCost == null && lcscInfo.unit_cost != null) {
        uiComponent.unitCost = lcscInfo.unit_cost;
        uiComponent.totalCost = lcscInfo.unit_cost * uiComponent.quantity;
      }
      if (uiComponent.inStock == null && lcscInfo.stock != null) {
        uiComponent.inStock = lcscInfo.stock > 0;
        uiComponent.stockQuantity = lcscInfo.stock;
      }
      if (!uiComponent.description && lcscInfo.description) {
        uiComponent.description = lcscInfo.description;
      }
      if (!uiComponent.manufacturer && lcscInfo.manufacturer) {
        uiComponent.manufacturer = lcscInfo.manufacturer;
      }
      if (!uiComponent.mpn && lcscInfo.mpn) {
        uiComponent.mpn = lcscInfo.mpn;
      }
      if (uiComponent.isBasic == null && lcscInfo.is_basic != null) {
        uiComponent.isBasic = lcscInfo.is_basic;
      }
      if (uiComponent.isPreferred == null && lcscInfo.is_preferred != null) {
        uiComponent.isPreferred = lcscInfo.is_preferred;
      }

      return uiComponent;
    });
  }, [bomData.components, lcscLoadingIds, lcscParts]);

  const handleToggle = useCallback((id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  const handleCopy = useCallback((value: string) => {
    void navigator.clipboard.writeText(value);
    setCopiedValue(value);
    window.setTimeout(() => setCopiedValue(null), 2000);
  }, []);

  const handleGoToSource = useCallback((address: string, line?: number) => {
    const filePath = resolveUsageFilePath(projectRoot, address);
    if (!filePath) {
      return;
    }
    void rpcClient?.requestAction("vscode.openFile", { path: filePath, line });
  }, [projectRoot]);

  const filteredComponents = useMemo(() => {
    const searchLower = searchQuery.toLowerCase();
    return bomComponents
      .filter((component) => {
        if (!searchLower) {
          return true;
        }
        return (
          component.value.toLowerCase().includes(searchLower) ||
          component.mpn?.toLowerCase().includes(searchLower) ||
          component.lcsc?.toLowerCase().includes(searchLower) ||
          component.manufacturer?.toLowerCase().includes(searchLower) ||
          component.description?.toLowerCase().includes(searchLower)
        );
      })
      .sort((left, right) => (right.totalCost || 0) - (left.totalCost || 0));
  }, [bomComponents, searchQuery]);

  const EXTENDED_LOADING_FEE = 3;
  const { totalComponents, partsCost, setupFees, extendedPartCount, totalCost, uniqueParts, outOfStock } = useMemo(() => {
    let total = 0;
    let cost = 0;
    let out = 0;
    let extendedParts = 0;

    for (const component of bomComponents) {
      total += component.quantity;
      cost += component.totalCost || 0;
      if (component.inStock === false) {
        out += 1;
      }
      if (component.isBasic !== true && component.isPreferred !== true) {
        extendedParts += 1;
      }
    }

    const setup = extendedParts * EXTENDED_LOADING_FEE;
    return {
      totalComponents: total,
      partsCost: cost,
      setupFees: setup,
      extendedPartCount: extendedParts,
      totalCost: cost + setup,
      uniqueParts: bomComponents.length,
      outOfStock: out,
    };
  }, [bomComponents]);

  const buildIdShort = useMemo(() => {
    if (!bomData.buildId) {
      return null;
    }
    const match = bomData.buildId.match(/^build-(\d+)-/);
    return match ? `#${match[1]}` : bomData.buildId.substring(0, 12);
  }, [bomData.buildId]);

  if (!projectRoot) {
    return (
      <EmptyState
        icon={<Package size={24} />}
        title="No project selected"
        description="Select a project to view the Bill of Materials"
      />
    );
  }

  const getEmptyDescription = () => {
    if (target) {
      return `Run a build for "${target}" to generate the Bill of Materials`;
    }
    return "Run a build to generate the Bill of Materials";
  };

  if (isLoading) {
    return (
      <div className="bom-panel">
        <PanelSearchBox value={searchQuery} onChange={setSearchQuery} placeholder="Search value, MPN..." />
        <div className="bom-loading">
          <RefreshCw size={24} className="loading-spinner" />
          <span>Loading BOM...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bom-panel">
        <PanelSearchBox value={searchQuery} onChange={setSearchQuery} placeholder="Search value, MPN..." />
        <EmptyState title="Error loading BOM" description={error} />
      </div>
    );
  }

  if (bomComponents.length === 0) {
    return (
      <div className="bom-panel">
        <PanelSearchBox value={searchQuery} onChange={setSearchQuery} placeholder="Search value, MPN..." />
        <EmptyState title="No BOM data available" description={getEmptyDescription()} />
      </div>
    );
  }

  return (
    <div className="bom-panel">
      <div className="bom-summary">
        <div className="bom-summary-item">
          <span className="summary-value">{uniqueParts}</span>
          <span className="summary-label">unique</span>
        </div>
        <div className="bom-summary-item">
          <span className="summary-value">{totalComponents}</span>
          <span className="summary-label">total</span>
        </div>
        <div className="bom-summary-item">
          <span className="summary-value">{formatCurrency(partsCost)}</span>
          <span className="summary-label">parts</span>
        </div>
        {setupFees > 0 && (
          <div
            className="bom-summary-item"
            title={`${extendedPartCount} extended part${extendedPartCount !== 1 ? "s" : ""} x $${EXTENDED_LOADING_FEE} loading fee`}
          >
            <span className="summary-value">+{formatCurrency(setupFees)}</span>
            <span className="summary-label">setup</span>
          </div>
        )}
        <div className="bom-summary-item primary">
          <span className="summary-value">{formatCurrency(totalCost)}</span>
          <span className="summary-label">total</span>
        </div>
        {outOfStock > 0 && (
          <div className="bom-summary-item warning">
            <AlertTriangle size={12} />
            <span className="summary-value">{outOfStock}</span>
            <span className="summary-label">out of stock</span>
          </div>
        )}
        {buildIdShort && (
          <div className="bom-summary-item muted" title={`Build: ${bomData.buildId}`}>
            <span className="summary-value">{buildIdShort}</span>
            <span className="summary-label">build</span>
          </div>
        )}
      </div>

      <PanelSearchBox value={searchQuery} onChange={setSearchQuery} placeholder="Search value, MPN..." />

      <div className="bom-list">
        {filteredComponents.map((component) => (
          <BOMRow
            key={component.id}
            component={component}
            isExpanded={expandedIds.has(component.id)}
            onToggle={() => handleToggle(component.id)}
            onCopy={handleCopy}
            onGoToSource={handleGoToSource}
          />
        ))}

        {filteredComponents.length === 0 && (
          <div className="bom-empty">
            <Package size={24} />
            <span>No components found</span>
          </div>
        )}
      </div>

      {copiedValue && (
        <div className="bom-toast">
          <Check size={10} />
          Copied: {copiedValue}
        </div>
      )}
    </div>
  );
}
