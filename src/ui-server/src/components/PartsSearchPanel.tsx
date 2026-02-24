/**
 * PartsSearchPanel - Tab-based part search and project parts view.
 */

import { useEffect, useMemo, useRef, useState } from 'react'
import { ArrowDown, ArrowUp, CheckCircle, Loader2, Package, PackageSearch, Search } from 'lucide-react'
import type { PartSearchItem, InstalledPartItem } from '../types/build'
import type { SelectedPart } from './sidebar-modules'
import { api } from '../api/client'
import { PanelSearchBox } from './shared/PanelSearchBox'
import './PartsSearchPanel.css'

interface PartsSearchPanelProps {
  selectedProjectRoot: string | null
  onOpenPartDetail: (part: SelectedPart) => void
  isExpanded?: boolean
}

type TabId = 'search' | 'project'
type SortColumn = 'mpn' | 'description' | 'manufacturer' | 'stock' | 'price'
type SortDirection = 'asc' | 'desc'
interface SortState {
  column: SortColumn
  direction: SortDirection
}

function formatCurrency(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return '-'
  if (value < 0.01) return `$${value.toFixed(4)}`
  return `$${value.toFixed(2)}`
}

function formatStock(stock: number | null | undefined): string {
  if (stock == null) return '-'
  if (stock <= 0) return 'Out of stock'
  if (stock >= 1_000_000) return `${(stock / 1_000_000).toFixed(1)}M`
  if (stock >= 1_000) return `${(stock / 1_000).toFixed(1)}K`
  return stock.toLocaleString()
}

export function PartsSearchPanel({
  selectedProjectRoot,
  onOpenPartDetail,
  isExpanded = false,
}: PartsSearchPanelProps) {
  const [activeTab, setActiveTab] = useState<TabId>('search')
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<PartSearchItem[]>([])
  const [searchError, setSearchError] = useState<string | null>(null)
  const [searchLoading, setSearchLoading] = useState(false)
  const [installedParts, setInstalledParts] = useState<InstalledPartItem[]>([])
  const [installedError, setInstalledError] = useState<string | null>(null)
  const [enrichingLcscs, setEnrichingLcscs] = useState<Set<string>>(new Set())
  const [installedLoading, setInstalledLoading] = useState(false)
  const [sort, setSort] = useState<SortState>({ column: 'stock', direction: 'desc' })
  const [projectFilter, setProjectFilter] = useState('')

  const searchRequestId = useRef(0)
  const searchInputRef = useRef<HTMLInputElement>(null)
  const projectInputRef = useRef<HTMLInputElement>(null)

  // Focus search input when switching tabs
  useEffect(() => {
    if (activeTab === 'search' && searchInputRef.current) {
      searchInputRef.current.focus()
    } else if (activeTab === 'project' && projectInputRef.current) {
      projectInputRef.current.focus()
    }
  }, [activeTab])

  useEffect(() => {
    // Clear state immediately when project changes
    setInstalledParts([])
    setInstalledError(null)
    setEnrichingLcscs(new Set())
    setInstalledLoading(false)

    if (!selectedProjectRoot) {
      return
    }

    let active = true
    setInstalledLoading(true)
    api.parts.installed(selectedProjectRoot)
      .then((response) => {
        if (!active) return
        const parts = response.parts || []

        // Determine which parts need enrichment
        const lcscIds = parts
          .filter((p) => p.lcsc && (p.stock == null || p.unit_cost == null))
          .map((p) => p.lcsc!)

        // Show parts immediately with spinners for those being enriched
        const enrichingSet = new Set(lcscIds.map((id) => id.toUpperCase()))
        setEnrichingLcscs(enrichingSet)
        setInstalledParts(parts)
        setInstalledLoading(false)

        // Start enrichment in background
        if (lcscIds.length > 0) {
          api.parts.lcsc(lcscIds, { projectRoot: selectedProjectRoot })
            .then((enrichResponse) => {
              if (!active) return
              const enrichedParts = enrichResponse.parts || {}
              setInstalledParts((prev) =>
                prev.map((part) => {
                  if (!part.lcsc) return part
                  const key = part.lcsc.toUpperCase()
                  const enriched = enrichedParts[key]
                  if (!enriched) return part
                  return {
                    ...part,
                    stock: enriched.stock ?? part.stock,
                    unit_cost: enriched.unit_cost ?? part.unit_cost,
                    description: part.description || enriched.description,
                    package: part.package || enriched.package,
                  }
                })
              )
            })
            .catch((err) => {
              // Log but don't block - parts still display with basic info
              console.warn('Parts enrichment failed:', err)
            })
            .finally(() => {
              if (!active) return
              setEnrichingLcscs(new Set())
            })
        } else {
          // No enrichment needed, clear any spinners
          setEnrichingLcscs(new Set())
        }
      })
      .catch((error) => {
        if (!active) return
        setInstalledError(error instanceof Error ? error.message : 'Failed to load installed parts')
        setInstalledLoading(false)
      })

    return () => {
      active = false
    }
  }, [selectedProjectRoot])

  // Listen for parts_changed events to refresh installed parts list
  useEffect(() => {
    const handlePartsChanged = (event: CustomEvent<{ projectRoot?: string; lcscId?: string; installed?: boolean }>) => {
      // Only refresh if the event is for our project
      if (selectedProjectRoot && event.detail.projectRoot === selectedProjectRoot) {
        // Refetch installed parts
        api.parts.installed(selectedProjectRoot)
          .then((response) => {
            setInstalledParts(response.parts || [])
          })
          .catch((error) => {
            console.warn('Failed to refresh installed parts:', error)
          })
      }
    }

    window.addEventListener('atopile:parts_changed', handlePartsChanged as EventListener)
    return () => {
      window.removeEventListener('atopile:parts_changed', handlePartsChanged as EventListener)
    }
  }, [selectedProjectRoot])

  useEffect(() => {
    const query = searchQuery.trim()
    if (!query) {
      setSearchResults([])
      setSearchError(null)
      setSearchLoading(false)
      return
    }

    const requestId = ++searchRequestId.current
    const timer = setTimeout(() => {
      setSearchLoading(true)
      setSearchError(null)
      api.parts.search(query, 50)
        .then((response) => {
          if (requestId !== searchRequestId.current) return
          if (response.error) {
            setSearchError(response.error)
          }
          setSearchResults(response.parts || [])
        })
        .catch((error) => {
          if (requestId !== searchRequestId.current) return
          setSearchError(error instanceof Error ? error.message : 'Search failed')
          setSearchResults([])
        })
        .finally(() => {
          if (requestId !== searchRequestId.current) return
          setSearchLoading(false)
        })
    }, 250)

    return () => clearTimeout(timer)
  }, [searchQuery])

  const installedLcscIds = useMemo(() => {
    return new Set(
      installedParts
        .map((part) => part.lcsc?.toUpperCase())
        .filter((lcsc): lcsc is string => !!lcsc)
    )
  }, [installedParts])

  const filteredAndSortedInstalledParts = useMemo(() => {
    const filter = projectFilter.trim().toLowerCase()
    const filtered = filter
      ? installedParts.filter((part) => {
          const searchable = [
            part.mpn,
            part.identifier,
            part.manufacturer,
            part.description,
            part.lcsc,
          ].filter(Boolean).join(' ').toLowerCase()
          return searchable.includes(filter)
        })
      : installedParts

    return [...filtered].sort((a, b) => {
      let cmp = 0
      switch (sort.column) {
        case 'mpn':
          cmp = (a.mpn || a.identifier || '').localeCompare(b.mpn || b.identifier || '')
          break
        case 'description':
          cmp = (a.description || '').localeCompare(b.description || '')
          break
        case 'manufacturer':
          cmp = (a.manufacturer || '').localeCompare(b.manufacturer || '')
          break
        case 'stock':
          cmp = (a.stock ?? -1) - (b.stock ?? -1)
          break
        case 'price':
          cmp = (a.unit_cost ?? Infinity) - (b.unit_cost ?? Infinity)
          break
      }
      return sort.direction === 'desc' ? -cmp : cmp
    })
  }, [installedParts, sort, projectFilter])

  const sortedSearchResults = useMemo(() => {
    return [...searchResults].sort((a, b) => {
      let cmp = 0
      switch (sort.column) {
        case 'mpn':
          cmp = (a.mpn || '').localeCompare(b.mpn || '')
          break
        case 'description':
          cmp = (a.description || '').localeCompare(b.description || '')
          break
        case 'manufacturer':
          cmp = (a.manufacturer || '').localeCompare(b.manufacturer || '')
          break
        case 'stock':
          cmp = (a.stock ?? -1) - (b.stock ?? -1)
          break
        case 'price':
          cmp = (a.unit_cost ?? Infinity) - (b.unit_cost ?? Infinity)
          break
      }
      return sort.direction === 'desc' ? -cmp : cmp
    })
  }, [searchResults, sort])

  const toggleSort = (column: SortColumn) => {
    setSort((prev) => ({
      column,
      direction: prev.column === column && prev.direction === 'desc' ? 'asc' : 'desc',
    }))
  }

  const hasSearchQuery = searchQuery.trim().length > 0

  const SortIcon = ({ column }: { column: SortColumn }) => {
    if (sort.column !== column) return null
    return sort.direction === 'desc' ? <ArrowDown size={10} /> : <ArrowUp size={10} />
  }

  const renderSortHeader = () => (
    <div className="parts-results-header">
      <button className="parts-sort-btn left" onClick={() => toggleSort('mpn')}>
        PN <SortIcon column="mpn" />
      </button>
      <button className="parts-sort-btn left" onClick={() => toggleSort('description')}>
        Description <SortIcon column="description" />
      </button>
      <button className="parts-sort-btn left" onClick={() => toggleSort('manufacturer')}>
        Mfr <SortIcon column="manufacturer" />
      </button>
      <button className="parts-sort-btn" onClick={() => toggleSort('stock')}>
        Stock <SortIcon column="stock" />
      </button>
      <button className="parts-sort-btn" onClick={() => toggleSort('price')}>
        Price <SortIcon column="price" />
      </button>
    </div>
  )

  return (
    <div className="parts-panel">
      <div className="parts-tabs">
        <button
          className={`parts-tab ${activeTab === 'search' ? 'active' : ''}`}
          onClick={() => setActiveTab('search')}
        >
          <Search size={14} />
          Find Parts
        </button>
        <button
          className={`parts-tab ${activeTab === 'project' ? 'active' : ''}`}
          onClick={() => setActiveTab('project')}
        >
          <Package size={14} />
          Project
          {installedParts.length > 0 && (
            <span className="parts-tab-count">{installedParts.length}</span>
          )}
        </button>
      </div>

      {activeTab === 'search' && (
        <div className="parts-tab-content">
          <PanelSearchBox
            value={searchQuery}
            onChange={setSearchQuery}
            placeholder="Search JLCPCB parts..."
            autoFocus={isExpanded && activeTab === 'search'}
          />

          {searchError && (
            <div className="parts-error">{searchError}</div>
          )}

          <div className="parts-results-container">
            {searchLoading && (
              <div className="parts-empty-state">
                <Loader2 size={24} className="parts-spinner" />
                <span>Searching...</span>
              </div>
            )}
            {!searchLoading && !hasSearchQuery && (
              <div className="parts-empty-state">
                <PackageSearch size={32} />
                <span>Search JLCPCB parts by name, description, or part number</span>
              </div>
            )}
            {!searchLoading && hasSearchQuery && searchResults.length === 0 && (
              <div className="parts-empty-state">
                <PackageSearch size={24} />
                <span>No parts found</span>
              </div>
            )}
            {!searchLoading && searchResults.length > 0 && (
              <div className="parts-results-table">
                {renderSortHeader()}
                {sortedSearchResults.map((part) => {
                  const isInstalled = installedLcscIds.has(part.lcsc.toUpperCase())
                  return (
                    <div
                      key={part.lcsc}
                      className={`parts-results-row ${isInstalled ? 'installed' : ''}`}
                      onClick={() => onOpenPartDetail({
                        lcsc: part.lcsc,
                        mpn: part.mpn,
                        manufacturer: part.manufacturer,
                        description: part.description,
                        package: part.package,
                        datasheet_url: part.datasheet_url,
                        image_url: part.image_url || undefined,
                        installed: isInstalled,
                      })}
                    >
                      <span className="parts-cell parts-cell-primary">
                        {part.mpn}
                        {isInstalled && <CheckCircle size={12} className="parts-installed-badge" />}
                      </span>
                      <span className="parts-cell parts-cell-description">{part.description}</span>
                      <span className="parts-cell parts-cell-mfr">{part.manufacturer}</span>
                      <span className="parts-cell parts-cell-stock">{formatStock(part.stock)}</span>
                      <span className="parts-cell parts-cell-price">{formatCurrency(part.unit_cost)}</span>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'project' && (
        <div className="parts-tab-content">
          <PanelSearchBox
            value={projectFilter}
            onChange={setProjectFilter}
            placeholder="Filter project parts..."
            autoFocus={isExpanded && activeTab === 'project'}
          />
          <div className="parts-results-container">
            {!selectedProjectRoot && (
              <div className="parts-empty-state">
                <Package size={32} />
                <span>Select a project to view installed parts</span>
              </div>
            )}
            {selectedProjectRoot && installedLoading && (
              <div className="parts-empty-state">
                <Loader2 size={24} className="parts-spinner" />
                <span>Loading project parts...</span>
              </div>
            )}
            {selectedProjectRoot && !installedLoading && installedError && (
              <div className="parts-empty-state">
                <span>{installedError}</span>
              </div>
            )}
            {selectedProjectRoot && !installedLoading && !installedError && installedParts.length === 0 && (
              <div className="parts-empty-state">
                <Package size={32} />
                <span>No parts installed in this project</span>
                <button
                  className="parts-empty-action"
                  onClick={() => setActiveTab('search')}
                >
                  Find parts to add
                </button>
              </div>
            )}
            {selectedProjectRoot && !installedLoading && installedParts.length > 0 && filteredAndSortedInstalledParts.length === 0 && (
              <div className="parts-empty-state">
                <Package size={24} />
                <span>No parts match "{projectFilter}"</span>
              </div>
            )}
            {selectedProjectRoot && !installedLoading && filteredAndSortedInstalledParts.length > 0 && (
              <div className="parts-results-table">
                {renderSortHeader()}
                {filteredAndSortedInstalledParts.map((part) => {
                  const isEnriching = part.lcsc ? enrichingLcscs.has(part.lcsc.toUpperCase()) : false
                  return (
                    <div
                      key={part.identifier}
                      className="parts-results-row"
                      onClick={() => {
                        if (!part.lcsc) return
                        onOpenPartDetail({
                          lcsc: part.lcsc,
                          mpn: part.mpn,
                          manufacturer: part.manufacturer,
                          description: part.description || '',
                          package: part.package || undefined,
                          datasheet_url: part.datasheet_url || undefined,
                          image_url: part.image_url || undefined,
                          installed: true,
                        })
                      }}
                    >
                      <span className="parts-cell parts-cell-primary">
                        {part.mpn || part.identifier}
                      </span>
                      <span className="parts-cell parts-cell-description">
                        {part.description || '-'}
                      </span>
                      <span className="parts-cell parts-cell-mfr">{part.manufacturer || '-'}</span>
                      <span className="parts-cell parts-cell-stock">
                        {isEnriching ? <Loader2 size={12} className="parts-spinner" /> : formatStock(part.stock)}
                      </span>
                      <span className="parts-cell parts-cell-price">
                        {isEnriching ? <Loader2 size={12} className="parts-spinner" /> : formatCurrency(part.unit_cost)}
                      </span>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
