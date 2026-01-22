import { useState, memo, useCallback, useMemo, useEffect, useRef } from 'react'
import {
  ChevronDown, ChevronRight, Search, Package,
  ExternalLink, Copy, Check, AlertTriangle,
  RefreshCw
} from 'lucide-react'
import type {
  BOMComponent as BOMComponentAPI,
  BOMData,
  BOMComponentType,
  Project,
  LcscPartData
} from '../types/build'
import { api } from '../api/client'
import { ProjectDropdown, type ProjectOption } from './ProjectDropdown'

// Component types (local type alias for UI)
type ComponentType = BOMComponentType

// Parameter with optional constraint info for UI display
interface BOMParameterUI {
  name: string
  value: string
  unit?: string
  constraint?: string       // Design constraint (what user asked for)
  constraintUnit?: string   // Unit for constraint (if different)
}

// Transform API BOM component to UI component format
interface BOMComponentUI {
  id: string
  designators: string[]  // e.g., ['R1', 'R2', 'R5']
  type: ComponentType
  value: string          // e.g., '10kΩ', '100nF', 'STM32F405'
  package: string        // e.g., '0402', 'QFP-48'
  manufacturer?: string
  mpn?: string           // Manufacturer Part Number
  lcsc?: string          // LCSC Part Number
  description?: string
  quantity: number
  unitCost?: number      // in USD
  totalCost?: number
  inStock?: boolean
  stockQuantity?: number
  lcscLoading?: boolean
  parameters?: BOMParameterUI[]
  source?: string        // 'picked' | 'specified' | 'manual'
  path?: string          // Design path (primary/declaration)
  usages?: { path: string; designator: string; line?: number }[]
}

// Where a component is used in the design
interface UsageLocation {
  path: string           // Full atopile path e.g., "main.ato:App.power_supply.decoupling[0]"
  designator: string     // e.g., "C3"
  line?: number          // Line number in file
}

// Grouped usage for tree view
interface UsageGroup {
  parentPath: string      // e.g., "App.power_supply"
  parentLabel: string     // e.g., "power_supply"
  instances: UsageLocation[]
}

function normalizeUsagePath(path: string): string {
  const parts = path.split('::')
  const addressPart = parts.length > 1 ? parts[1] : path
  return addressPart.split('|')[0]
}

function getUsageDisplayPath(path: string): string {
  const normalized = normalizeUsagePath(path)
  const segments = normalized.split('.')
  if (segments.length <= 1) return normalized
  return segments.slice(1).join('.')
}

// Transform API response to UI format
function transformBOMComponent(apiComp: BOMComponentAPI): BOMComponentUI {
  const designators = apiComp.usages.map(u => u.designator)
  const unitCost = apiComp.unitCost ?? undefined
  const totalCost = unitCost !== undefined ? unitCost * apiComp.quantity : undefined
  const stock = apiComp.stock

  return {
    id: apiComp.id,
    designators,
    type: apiComp.type as ComponentType,
    value: apiComp.value,
    package: apiComp.package,
    manufacturer: apiComp.manufacturer ?? undefined,
    mpn: apiComp.mpn ?? undefined,
    lcsc: apiComp.lcsc ?? undefined,
    description: apiComp.description ?? undefined,
    quantity: apiComp.quantity,
    unitCost,
    totalCost,
    inStock: stock !== undefined && stock !== null ? stock > 0 : undefined,
    stockQuantity: stock ?? undefined,
    parameters: apiComp.parameters,
    source: apiComp.source,
    path: apiComp.usages[0]?.address,
    usages: apiComp.usages.map(u => ({
      path: u.address,
      designator: u.designator,
    })),
  }
}


// Get short type label
function getTypeLabel(type: ComponentType): string {
  switch (type) {
    case 'resistor': return 'R'
    case 'capacitor': return 'C'
    case 'inductor': return 'L'
    case 'ic': return 'IC'
    case 'connector': return 'J'
    case 'led': return 'LED'
    case 'diode': return 'D'
    case 'transistor': return 'Q'
    case 'crystal': return 'Y'
    default: return 'X'
  }
}

// Format currency
function formatCurrency(value: number): string {
  if (value < 0.01) return `$${value.toFixed(4)}`
  if (value < 1) return `$${value.toFixed(3)}`
  return `$${value.toFixed(2)}`
}

// Group usages by a common module prefix for cleaner tree display
function groupUsagesByModule(usages: UsageLocation[]): UsageGroup[] {
  const groups: Map<string, UsageGroup> = new Map()

  for (const usage of usages) {
    // Extract the parent module path for grouping
    // e.g., "passives.ato::App.ad1938.decoupling[0]|Cap" -> group by "ad1938"
    const normalizedPath = normalizeUsagePath(usage.path)
    const segments = normalizedPath.split('.')

    let parentPath: string
    let parentLabel: string

    if (segments.length >= 3) {
      // Group by the module before the leaf (e.g., "App.ad1938" for "App.ad1938.cap")
      parentPath = segments.slice(0, -1).join('.')
      parentLabel = segments[segments.length - 2]
    } else if (segments.length === 2) {
      parentPath = segments[0]
      parentLabel = segments[0]
    } else {
      parentPath = normalizedPath
      parentLabel = normalizedPath
    }

    if (!groups.has(parentPath)) {
      groups.set(parentPath, {
        parentPath,
        parentLabel,
        instances: []
      })
    }
    groups.get(parentPath)!.instances.push(usage)
  }

  return Array.from(groups.values())
}

// Format stock number with K/M suffixes
function formatStock(stock: number): string {
  if (stock >= 1000000) {
    return `${(stock / 1000000).toFixed(1)}M`
  }
  if (stock >= 1000) {
    return `${(stock / 1000).toFixed(0)}K`
  }
  return stock.toString()
}

// Component row - cleaner table layout with improved tree structure
// Memoized to prevent unnecessary re-renders in list
const BOMRow = memo(function BOMRow({
  component,
  isExpanded,
  onToggle,
  onCopy,
  onGoToSource
}: {
  component: BOMComponentUI
  isExpanded: boolean
  onToggle: () => void
  onCopy: (text: string) => void
  onGoToSource: (path: string, line?: number) => void
}) {
  const [copiedField, setCopiedField] = useState<string | null>(null)
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(() => new Set())

  const handleCopy = (field: string, value: string, e: React.MouseEvent) => {
    e.stopPropagation()
    onCopy(value)
    setCopiedField(field)
    setTimeout(() => setCopiedField(null), 1500)
  }

  const handleUsageClick = (e: React.MouseEvent, usage: UsageLocation) => {
    e.stopPropagation()
    onGoToSource(usage.path, usage.line)
  }

  const toggleGroup = (groupPath: string, e: React.MouseEvent) => {
    e.stopPropagation()
    setExpandedGroups(prev => {
      const next = new Set(prev)
      if (next.has(groupPath)) {
        next.delete(groupPath)
      } else {
        next.add(groupPath)
      }
      return next
    })
  }

  const usageGroups = component.usages ? groupUsagesByModule(component.usages) : []

  return (
    <div className={`bom-row ${isExpanded ? 'expanded' : ''}`} onClick={onToggle}>
      {/* Compact header row: Type | Value | MPN | Qty | Cost */}
      <div className="bom-row-header">
        <span className="bom-expand">
          {isExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        </span>
        <span className={`bom-type-badge type-${component.type}`}>{getTypeLabel(component.type)}</span>
        <span className="bom-value">{component.value}</span>
        {component.mpn && (
          <span className="bom-mpn" title={component.mpn}>{component.mpn}</span>
        )}
        <span className="bom-quantity">×{component.quantity}</span>
        {component.totalCost !== undefined && (
          <span className="bom-cost">{formatCurrency(component.totalCost)}</span>
        )}
        {component.inStock === false && (
          <AlertTriangle size={12} className="bom-stock-warning" />
        )}
      </div>

      {isExpanded && (
        <div className="bom-row-details">
          {/* Part details - single column table layout */}
          <table className="bom-detail-table">
            <tbody>
              <tr>
                <td className="detail-cell-label">Manufacturer</td>
                <td className="detail-cell-value">{component.manufacturer || '-'}</td>
              </tr>
              <tr>
                <td className="detail-cell-label">Package</td>
                <td className="detail-cell-value">{component.package}</td>
              </tr>
              <tr>
                <td className="detail-cell-label">LCSC</td>
                <td className="detail-cell-value">
                  {component.lcsc ? (
                    <span
                      className="lcsc-link"
                      onClick={(e) => handleCopy('lcsc', component.lcsc!, e)}
                    >
                      <span className="mono">{component.lcsc}</span>
                      <a
                        href={`https://www.lcsc.com/product-detail/${component.lcsc}.html`}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="external-link"
                      >
                        <ExternalLink size={10} />
                      </a>
                      {copiedField === 'lcsc' ? (
                        <Check size={10} className="copy-icon copied" />
                      ) : (
                        <Copy size={10} className="copy-icon" />
                      )}
                    </span>
                  ) : '-'}
                </td>
              </tr>
              <tr>
                <td className="detail-cell-label">Stock</td>
                <td className={`detail-cell-value ${component.inStock === false ? 'out-of-stock' : 'in-stock'}`}>
                  {component.inStock === false ? (
                    <span className="stock-out"><AlertTriangle size={10} /> Out of stock</span>
                  ) : component.lcscLoading && component.stockQuantity == null ? (
                    <span className="inline-loading"><RefreshCw size={10} className="loading-spinner" /> Fetching...</span>
                  ) : (
                    component.stockQuantity ? formatStock(component.stockQuantity) : 'In stock'
                  )}
                </td>
              </tr>
              <tr>
                <td className="detail-cell-label">Unit Cost</td>
                <td className="detail-cell-value cost">
                  {component.unitCost != null ? (
                    formatCurrency(component.unitCost)
                  ) : component.lcscLoading ? (
                    <span className="inline-loading"><RefreshCw size={10} className="loading-spinner" /> Fetching...</span>
                  ) : (
                    '-'
                  )}
                </td>
              </tr>
              <tr>
                <td className="detail-cell-label">Source</td>
                <td className="detail-cell-value">
                  <span className={`source-badge source-${component.source}`}>
                    {component.source === 'picked' ? 'Auto-picked' :
                     component.source === 'specified' ? 'Specified' : 'Manual'}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>

          {/* Where used - tree view grouped by module */}
          {usageGroups.length > 0 && (
            <div className="bom-usages-tree">
              <div className="usages-header">
                <span>Used in design</span>
                <span className="usages-count">{component.quantity} instance{component.quantity !== 1 ? 's' : ''}</span>
              </div>
              <div className="usage-groups">
                {usageGroups.map((group) => (
                  <div key={group.parentPath} className="usage-group">
                    {group.instances.length > 1 ? (
                      <>
                        <div
                          className="usage-group-header"
                          onClick={(e) => toggleGroup(group.parentPath, e)}
                        >
                          <span className="usage-expand">
                            {expandedGroups.has(group.parentPath) ?
                              <ChevronDown size={11} /> : <ChevronRight size={11} />}
                          </span>
                          <span className="usage-module-name">{group.parentLabel}</span>
                          <span className="usage-count-badge">×{group.instances.length}</span>
                        </div>
                        {expandedGroups.has(group.parentPath) && (
                          <div className="usage-instances">
                            {group.instances.map((usage, idx) => {
                              // Extract just the leaf name (e.g., "decoupling[0]" from full path)
                              const leafName = getUsageDisplayPath(usage.path)
                              return (
                                <div
                                  key={idx}
                                  className="usage-instance"
                                  onClick={(e) => handleUsageClick(e, usage)}
                                  title={usage.path}
                                >
                                  <span className="usage-designator">{usage.designator}</span>
                                  <span className="usage-leaf">{leafName}</span>
                                  <ExternalLink size={9} className="usage-goto" />
                                </div>
                              )
                            })}
                          </div>
                        )}
                      </>
                    ) : (
                      <div
                        className="usage-single"
                        onClick={(e) => handleUsageClick(e, group.instances[0])}
                        title={group.instances[0].path}
                      >
                        <span className="usage-designator">{group.instances[0].designator}</span>
                        <span className="usage-module-path">
                          {getUsageDisplayPath(group.instances[0].path)}
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
  )
})

interface BOMPanelProps {
  // API data props - BOM follows the currently selected project
  bomData?: BOMData | null
  isLoading?: boolean
  error?: string | null
  onGoToSource?: (path: string, line?: number) => void
  projects?: Project[]
  selectedProjectRoot?: string | null
  selectedTargetNames?: string[]
  onSelectProject?: (projectRoot: string | null) => void
  onSelectTarget?: (projectRoot: string, targetName: string) => void
}

export function BOMPanel({
  bomData,
  isLoading = false,
  error = null,
  onGoToSource: externalGoToSource,
  projects,
  selectedProjectRoot,
  selectedTargetNames,
  onSelectProject,
  onSelectTarget,
}: BOMPanelProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set())
  const [copiedValue, setCopiedValue] = useState<string | null>(null)
  const [bomTargetsByProject, setBomTargetsByProject] = useState<Record<string, string[]>>({})
  const [lcscParts, setLcscParts] = useState<Record<string, LcscPartData | null>>({})
  const [lcscLoadingIds, setLcscLoadingIds] = useState<Set<string>>(new Set())
  const [latestBuildInfo, setLatestBuildInfo] = useState<{
    build_id?: string
    started_at?: number
    completed_at?: number
  } | null>(null)
  const [forceRefreshBuildId, setForceRefreshBuildId] = useState<string | null>(null)
  const lcscRequestIdRef = useRef(0)
  const lastLcscRefreshBuildIdRef = useRef<string | null>(null)
  const selectedTargetName = selectedTargetNames?.[0] ?? null

  useEffect(() => {
    if (!projects || projects.length === 0) {
      setBomTargetsByProject({})
      return
    }

    let cancelled = false
    Promise.all(
      projects.map(async (project) => {
        try {
          const result = await api.bom.targets(project.root)
          return [project.root, result.targets] as const
        } catch {
          return [project.root, [] as string[]] as const
        }
      })
    ).then((entries) => {
      if (cancelled) return
      const next: Record<string, string[]> = {}
      for (const [root, targets] of entries) {
        next[root] = [...targets]
      }
      setBomTargetsByProject(next)
    })

    return () => {
      cancelled = true
    }
  }, [projects])

  const sortedProjects = useMemo(() => {
    if (!projects) return []
    return [...projects].sort((a, b) => {
      const aHasBom = (bomTargetsByProject[a.root]?.length ?? 0) > 0
      const bHasBom = (bomTargetsByProject[b.root]?.length ?? 0) > 0
      if (aHasBom !== bHasBom) return aHasBom ? -1 : 1
      return a.name.localeCompare(b.name)
    })
  }, [projects, bomTargetsByProject])

  // Transform projects for ProjectDropdown
  const projectOptions: ProjectOption[] = useMemo(() => {
    return sortedProjects.map((project) => {
      const hasBom = (bomTargetsByProject[project.root]?.length ?? 0) > 0
      return {
        id: project.root,
        name: project.name,
        root: project.root,
        targets: project.targets?.map((target) => ({ name: target.name })) ?? [],
        badge: hasBom ? undefined : 'no BOM',
        badgeMuted: true,
      }
    })
  }, [sortedProjects, bomTargetsByProject])

  useEffect(() => {
    if (!selectedProjectRoot) {
      setLatestBuildInfo(null)
      setForceRefreshBuildId(null)
      lastLcscRefreshBuildIdRef.current = null
      return
    }

    api.builds
      .byProject(selectedProjectRoot, selectedTargetName ?? undefined, 1)
      .then((response) => {
        const build = response.builds?.[0]
        setLatestBuildInfo(build ? {
          build_id: build.buildId,
          started_at: build.startedAt,
          // completed_at not available on Build type, calculate from startedAt + elapsedSeconds
          completed_at: build.startedAt && build.elapsedSeconds
            ? build.startedAt + build.elapsedSeconds
            : undefined,
        } : null)
      })
      .catch((error) => {
        console.warn('Failed to load build info', error)
        setLatestBuildInfo(null)
      })
  }, [selectedProjectRoot, selectedTargetName])

  // Check if build is stale (older than 24 hours) to trigger LCSC refresh
  useEffect(() => {
    if (!latestBuildInfo?.build_id) return
    const timestamp = latestBuildInfo.completed_at ?? latestBuildInfo.started_at
    if (!timestamp) return
    const ageSeconds = Date.now() / 1000 - timestamp
    const isBuildStale = ageSeconds > 24 * 60 * 60
    if (!isBuildStale) return
    if (lastLcscRefreshBuildIdRef.current === latestBuildInfo.build_id) return
    setForceRefreshBuildId(latestBuildInfo.build_id)
  }, [latestBuildInfo])

  const lcscIds = useMemo(() => {
    if (!bomData?.components?.length) return []
    const ids = new Set<string>()
    for (const component of bomData.components) {
      if (!component.lcsc) continue
      ids.add(component.lcsc)
    }
    return Array.from(ids)
  }, [bomData?.components])

  const lcscIdsToFetch = useMemo(() => {
    if (!bomData?.components?.length) return []
    const ids = new Set<string>()
    for (const component of bomData.components) {
      if (!component.lcsc) continue
      if (component.unitCost != null && component.stock != null) continue
      ids.add(component.lcsc)
    }
    return Array.from(ids)
  }, [bomData?.components])

  useEffect(() => {
    const forceRefresh = !!forceRefreshBuildId
    const idsToRequest = forceRefresh ? lcscIds : lcscIdsToFetch
    if (idsToRequest.length === 0) return
    const missing = forceRefresh
      ? idsToRequest
      : idsToRequest.filter((id) => !(id in lcscParts))
    if (missing.length === 0) return

    const requestId = ++lcscRequestIdRef.current
    setLcscLoadingIds((prev) => {
      const next = new Set(prev)
      for (const id of missing) next.add(id)
      return next
    })
    api.parts
      .lcsc(missing, {
        projectRoot: selectedProjectRoot ?? undefined,
        target: selectedTargetName ?? undefined,
      })
      .then((response) => {
        if (requestId !== lcscRequestIdRef.current) return
        setLcscParts((prev) => ({ ...prev, ...response.parts }))
      })
      .catch((error) => {
        if (requestId !== lcscRequestIdRef.current) return
        console.warn('Failed to fetch LCSC data', error)
      })
      .finally(() => {
        setLcscLoadingIds((prev) => {
          const next = new Set(prev)
          for (const id of missing) next.delete(id)
          return next
        })
        if (forceRefresh && latestBuildInfo?.build_id) {
          lastLcscRefreshBuildIdRef.current = latestBuildInfo.build_id
          setForceRefreshBuildId(null)
        }
      })
  }, [
    lcscIdsToFetch,
    lcscIds,
    lcscParts,
    forceRefreshBuildId,
    latestBuildInfo,
    selectedProjectRoot,
    selectedTargetName,
  ])

  // Memoize API data transformation - no mock data fallback
  const bomComponents = useMemo((): BOMComponentUI[] => {
    if (!bomData?.components) return []
    return bomData.components.map((component) => {
      const uiComponent = transformBOMComponent(component)
      if (!component.lcsc) return uiComponent

      const lcscInfo = lcscParts[component.lcsc]
      uiComponent.lcscLoading = lcscLoadingIds.has(component.lcsc)
      if (!lcscInfo) return uiComponent

      if (uiComponent.unitCost == null && lcscInfo.unit_cost != null) {
        uiComponent.unitCost = lcscInfo.unit_cost
        uiComponent.totalCost = lcscInfo.unit_cost * uiComponent.quantity
      }
      if (uiComponent.inStock == null) {
        uiComponent.inStock = lcscInfo.stock > 0
        uiComponent.stockQuantity = lcscInfo.stock
      }
      if (!uiComponent.description && lcscInfo.description) {
        uiComponent.description = lcscInfo.description
      }
      if (!uiComponent.manufacturer && lcscInfo.manufacturer) {
        uiComponent.manufacturer = lcscInfo.manufacturer
      }
      if (!uiComponent.mpn && lcscInfo.mpn) {
        uiComponent.mpn = lcscInfo.mpn
      }

      return uiComponent
    })
  }, [bomData?.components, lcscParts])

  // Check if we have BOM data available
  const hasBOMData = bomData?.components && bomData.components.length > 0

  // Memoize callbacks to prevent child re-renders
  const handleToggle = useCallback((id: string) => {
    setExpandedIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }, [])

  const handleCopy = useCallback((value: string) => {
    navigator.clipboard.writeText(value)
    setCopiedValue(value)
    setTimeout(() => setCopiedValue(null), 2000)
  }, [])

  const handleGoToSource = useCallback((path: string, line?: number) => {
    if (externalGoToSource) {
      externalGoToSource(path, line)
    } else {
      console.log(`Navigate to: ${path}${line ? `:${line}` : ''}`)
    }
  }, [externalGoToSource])

  const toolbar = (
    <div className="panel-toolbar">
        <div className="panel-toolbar-row">
          <div className="search-box">
            <Search size={14} />
            <input
              type="text"
              placeholder="Search value, MPN..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <ProjectDropdown
            projects={projectOptions}
            selectedProjectRoot={selectedProjectRoot}
            selectedTargetName={selectedTargetNames?.[0] || null}
            onSelectProject={onSelectProject || (() => {})}
            onSelectTarget={onSelectTarget}
            showAllOption={false}
            placeholder="Select project"
          />
        </div>
      </div>
  )

  // Memoize filtered and sorted components
  const filteredComponents = useMemo(() => {
    const searchLower = searchQuery.toLowerCase()
    return bomComponents
      .filter(c => {
        // Search filter
        if (searchLower) {
          return (
            c.value.toLowerCase().includes(searchLower) ||
            c.mpn?.toLowerCase().includes(searchLower) ||
            c.lcsc?.toLowerCase().includes(searchLower) ||
            c.manufacturer?.toLowerCase().includes(searchLower) ||
            c.description?.toLowerCase().includes(searchLower)
          )
        }
        return true
      })
      .sort((a, b) => (b.totalCost || 0) - (a.totalCost || 0))
  }, [bomComponents, searchQuery])

  // Memoize totals calculation - single pass for efficiency
  const { totalComponents, totalCost, uniqueParts, outOfStock } = useMemo(() => {
    let total = 0
    let cost = 0
    let oos = 0
    for (const c of bomComponents) {
      total += c.quantity
      cost += c.totalCost || 0
      if (c.inStock === false) oos++
    }
    return {
      totalComponents: total,
      totalCost: cost,
      uniqueParts: bomComponents.length,
      outOfStock: oos
    }
  }, [bomComponents])

  // Extract short build ID for display (e.g., "build-42-1674520800" -> "#42")
  const buildIdShort = (() => {
    if (!bomData?.build_id) return null
    const match = bomData.build_id.match(/^build-(\d+)-/)
    return match ? `#${match[1]}` : bomData.build_id.substring(0, 12)
  })()

  // Loading state
  if (isLoading) {
    return (
      <div className="bom-panel">
        {toolbar}
        <div className="bom-loading">
          <RefreshCw size={24} className="loading-spinner" />
          <span>Loading BOM...</span>
        </div>
      </div>
    )
  }

  // Error state - but make 404 errors more user-friendly
  if (error) {
    const is404 = error.includes('404') || error.includes('not found') || error.includes("Run 'ato build'")
    return (
      <div className="bom-panel">
        {toolbar}
        <div className="bom-empty-state">
          {is404 ? (
            <>
              <span className="empty-title">No BOM data available</span>
              <span className="empty-description">
                Run a build to generate the Bill of Materials
              </span>
            </>
          ) : (
            <>
              <AlertTriangle size={24} />
              <span>{error}</span>
            </>
          )}
        </div>
      </div>
    )
  }

  // No data state (not loading, no error, but no BOM data)
  if (!hasBOMData) {
    return (
      <div className="bom-panel">
        {toolbar}
        <div className="bom-empty-state">
          <span className="empty-title">No BOM data available</span>
          <span className="empty-description">
            Select a project and run a build to generate the Bill of Materials
          </span>
        </div>
      </div>
    )
  }

  return (
    <div className="bom-panel">
      {/* Summary bar */}
      <div className="bom-summary">
        <div className="bom-summary-item">
          <span className="summary-value">{uniqueParts}</span>
          <span className="summary-label">unique</span>
        </div>
        <div className="bom-summary-item">
          <span className="summary-value">{totalComponents}</span>
          <span className="summary-label">total</span>
        </div>
        <div className="bom-summary-item primary">
          <span className="summary-value">{formatCurrency(totalCost)}</span>
          <span className="summary-label">cost</span>
        </div>
        {outOfStock > 0 && (
          <div className="bom-summary-item warning">
            <AlertTriangle size={12} />
            <span className="summary-value">{outOfStock}</span>
            <span className="summary-label">out of stock</span>
          </div>
        )}
        {buildIdShort && (
          <div className="bom-summary-item muted" title={`Build: ${bomData?.build_id}`}>
            <span className="summary-value">{buildIdShort}</span>
            <span className="summary-label">build</span>
          </div>
        )}
      </div>
      
      {/* Unified toolbar */}
      {toolbar}

      {/* Component list */}
      <div className="bom-list">
        {filteredComponents.map(component => (
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
      
      {/* Toast */}
      {copiedValue && (
        <div className="bom-toast">
          <Check size={10} />
          Copied: {copiedValue}
        </div>
      )}
    </div>
  )
}
