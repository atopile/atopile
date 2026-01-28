/**
 * PartsSearchPanel - Part search with installed section and results table.
 */

import { useEffect, useMemo, useRef, useState } from 'react'
import { CheckCircle, ChevronDown, ChevronRight, Cpu, PackageSearch, Search } from 'lucide-react'
import type { PartSearchItem, InstalledPartItem } from '../types/build'
import type { SelectedPart } from './sidebar-modules'
import { api } from '../api/client'
import './PartsSearchPanel.css'

interface PartsSearchPanelProps {
  selectedProjectRoot: string | null
  onOpenPartDetail: (part: SelectedPart) => void
}

function formatCurrency(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return '-'
  return `$${value.toFixed(4)}`
}

function formatStock(stock: number | null | undefined): string {
  if (stock == null) return '-'
  if (stock <= 0) return 'Out of stock'
  return stock.toLocaleString()
}

export function PartsSearchPanel({
  selectedProjectRoot,
  onOpenPartDetail,
}: PartsSearchPanelProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<PartSearchItem[]>([])
  const [searchError, setSearchError] = useState<string | null>(null)
  const [searchLoading, setSearchLoading] = useState(false)
  const [installedOpen, setInstalledOpen] = useState(true)
  const [installedParts, setInstalledParts] = useState<InstalledPartItem[]>([])
  const [installedError, setInstalledError] = useState<string | null>(null)

  const searchRequestId = useRef(0)

  useEffect(() => {
    if (!selectedProjectRoot) {
      setInstalledParts([])
      setInstalledError(null)
      return
    }

    let active = true
    setInstalledError(null)
    api.parts.installed(selectedProjectRoot)
      .then((response) => {
        if (!active) return
        setInstalledParts(response.parts || [])
      })
      .catch((error) => {
        if (!active) return
        setInstalledError(error instanceof Error ? error.message : 'Failed to load installed parts')
      })

    return () => {
      active = false
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

  const hasSearchQuery = searchQuery.trim().length > 0

  return (
    <div className="parts-panel">
      <div className="parts-search-bar">
        <Search size={14} />
        <input
          type="text"
          placeholder="Search parts (LCSC ID or Manufacturer:PartNumber)..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
      </div>

      {searchError && (
        <div className="parts-error">{searchError}</div>
      )}

      <div className="parts-sections">
        <div className="parts-section">
          <button
            className="parts-section-header"
            onClick={() => setInstalledOpen((prev) => !prev)}
          >
            <span className="section-toggle">
              {installedOpen ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
            </span>
            <span className="section-title">INSTALLED</span>
            <span className="section-count">{installedParts.length}</span>
          </button>

          {installedOpen && (
            <div className="parts-section-content">
              {!selectedProjectRoot && (
                <div className="parts-empty-hint">
                  Select a project to view installed parts
                </div>
              )}
              {selectedProjectRoot && installedError && (
                <div className="parts-empty-hint">{installedError}</div>
              )}
              {selectedProjectRoot && !installedError && installedParts.length === 0 && (
                <div className="parts-empty-hint">No parts installed</div>
              )}
              {selectedProjectRoot && installedParts.length > 0 && (
                <div className="parts-results-table parts-installed-table">
                  <div className="parts-results-header">
                    <span>PN</span>
                    <span>Description</span>
                    <span>Mfr</span>
                    <span>Stock</span>
                    <span>Price</span>
                  </div>
                  {installedParts.map((part) => (
                    <div
                      key={part.identifier}
                      className="parts-results-row installed"
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
                        <CheckCircle size={12} className="parts-installed-badge" />
                      </span>
                      <span className="parts-cell parts-cell-description">
                        {part.description || '-'}
                      </span>
                      <span className="parts-cell">{part.manufacturer || '-'}</span>
                      <span className="parts-cell">{formatStock(part.stock)}</span>
                      <span className="parts-cell">{formatCurrency(part.unit_cost)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        <div className="parts-section">
          {hasSearchQuery && (
            <div className="parts-section-header static">
              <span className="section-title">RESULTS</span>
              <span className="section-count">{searchResults.length}</span>
            </div>
          )}

          <div className="parts-section-content">
            {searchLoading && (
              <div className="parts-empty-state">
                <PackageSearch size={24} />
                <span>Searching...</span>
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
                <div className="parts-results-header">
                  <span>PN</span>
                  <span>Description</span>
                  <span>Mfr</span>
                  <span>Stock</span>
                  <span>Price</span>
                </div>
                {searchResults.map((part) => {
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
                      <span className="parts-cell">{part.manufacturer}</span>
                      <span className="parts-cell">{formatStock(part.stock)}</span>
                      <span className="parts-cell">{formatCurrency(part.unit_cost)}</span>
                    </div>
                  )
                })}
              </div>
            )}
            {!hasSearchQuery && (
              <div className="parts-empty-hint">
                Search for a part to see results
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
