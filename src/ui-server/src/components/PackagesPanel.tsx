/**
 * PackagesPanel - Tab-based package browser
 *
 * Layout:
 * - Tabs: "Browse" (marketplace) | "Project" (installed)
 * - Browse tab: Search bar + marketplace results
 * - Project tab: Packages installed in current project
 */

import { useEffect, useMemo, useRef, useState } from 'react'
import { CheckCircle, Package, PackageSearch, Search } from 'lucide-react'
import type { PackageInfo, ProjectDependency } from '../types/build'
import { isInstalledInProject } from '../utils/packageUtils'
import type { SelectedPackage } from './sidebar-modules'
import './PackagesPanel.css'

interface PackagesPanelProps {
  packages: PackageInfo[]
  installedDependencies: ProjectDependency[]
  selectedProjectRoot: string | null
  selectedProjectName?: string | null
  installingPackageIds?: string[]
  updatingDependencyIds?: string[]
  installError?: string | null
  onInstallPackage?: (packageId: string, projectRoot: string, version?: string) => void
  onOpenPackageDetail: (pkg: SelectedPackage) => void
  onDependencyVersionChange?: (projectRoot: string, identifier: string, newVersion: string) => void
  onRemoveDependency?: (projectRoot: string, identifier: string) => void
}

type TabId = 'browse' | 'project'

// Installed package row
function InstalledPackageRow({
  dependency,
  onClick,
}: {
  dependency: ProjectDependency
  onClick: () => void
}) {
  return (
    <div className="packages-row" onClick={onClick}>
      <Package size={14} className="packages-row-icon" />
      <div className="packages-row-info">
        <div className="packages-row-header">
          <span className="packages-row-name">{dependency.name}</span>
        </div>
        {dependency.summary && (
          <div className="packages-row-summary">{dependency.summary}</div>
        )}
      </div>
      <div className="packages-row-meta">
        <span className="packages-row-publisher">{dependency.publisher}</span>
        <span className="packages-row-version">{dependency.version}</span>
      </div>
    </div>
  )
}

// Marketplace package row
function MarketplacePackageRow({
  pkg,
  installed,
  onClick,
}: {
  pkg: PackageInfo
  installed: boolean
  onClick: () => void
}) {
  return (
    <div className={`packages-row ${installed ? 'installed' : ''}`} onClick={onClick}>
      <Package size={14} className="packages-row-icon" />
      <div className="packages-row-info">
        <div className="packages-row-header">
          <span className="packages-row-name">{pkg.name}</span>
          {installed && <CheckCircle size={12} className="packages-installed-badge" />}
        </div>
        {pkg.summary && (
          <div className="packages-row-summary">{pkg.summary}</div>
        )}
      </div>
      <div className="packages-row-meta">
        <span className="packages-row-publisher">{pkg.publisher}</span>
      </div>
    </div>
  )
}

export function PackagesPanel({
  packages,
  installedDependencies,
  selectedProjectRoot,
  installError,
  onOpenPackageDetail,
}: PackagesPanelProps) {
  const [activeTab, setActiveTab] = useState<TabId>('browse')
  const [searchQuery, setSearchQuery] = useState('')
  const searchInputRef = useRef<HTMLInputElement>(null)

  // Focus search input when switching to browse tab
  useEffect(() => {
    if (activeTab === 'browse' && searchInputRef.current) {
      searchInputRef.current.focus()
    }
  }, [activeTab])

  // Filter installed packages by search query (for project tab)
  const filteredInstalled = useMemo(() => {
    if (!searchQuery.trim()) return installedDependencies
    const query = searchQuery.toLowerCase()
    return installedDependencies.filter((dep) =>
      dep.name.toLowerCase().includes(query) ||
      dep.identifier.toLowerCase().includes(query) ||
      (dep.summary || '').toLowerCase().includes(query)
    )
  }, [installedDependencies, searchQuery])

  // Filter marketplace packages by search query
  const filteredMarketplace = useMemo(() => {
    if (!searchQuery.trim()) return packages
    const query = searchQuery.toLowerCase()
    return packages.filter((pkg) =>
      pkg.name.toLowerCase().includes(query) ||
      pkg.identifier.toLowerCase().includes(query) ||
      (pkg.description || '').toLowerCase().includes(query) ||
      (pkg.summary || '').toLowerCase().includes(query)
    )
  }, [packages, searchQuery])

  const handleOpenInstalledPackage = (dep: ProjectDependency) => {
    onOpenPackageDetail({
      name: dep.name,
      fullName: dep.identifier,
      version: dep.version,
      description: dep.summary,
      installed: true,
      homepage: dep.homepage,
      repository: dep.repository,
    })
  }

  const handleOpenMarketplacePackage = (pkg: PackageInfo) => {
    const installed = selectedProjectRoot
      ? isInstalledInProject(pkg.installedIn || [], selectedProjectRoot)
      : false
    onOpenPackageDetail({
      name: pkg.name,
      fullName: pkg.identifier,
      version: pkg.version,
      description: pkg.description || pkg.summary,
      installed,
      homepage: pkg.homepage,
      repository: pkg.repository,
    })
  }

  const hasSearchQuery = searchQuery.trim().length > 0

  return (
    <div className="packages-panel">
      <div className="packages-tabs">
        <button
          className={`packages-tab ${activeTab === 'browse' ? 'active' : ''}`}
          onClick={() => setActiveTab('browse')}
        >
          <Search size={14} />
          Browse
        </button>
        <button
          className={`packages-tab ${activeTab === 'project' ? 'active' : ''}`}
          onClick={() => setActiveTab('project')}
        >
          <Package size={14} />
          Project
          {installedDependencies.length > 0 && (
            <span className="packages-tab-count">{installedDependencies.length}</span>
          )}
        </button>
      </div>

      {activeTab === 'browse' && (
        <div className="packages-tab-content">
          <div className="packages-search-bar">
            <Search size={14} />
            <input
              ref={searchInputRef}
              type="text"
              placeholder="Search packages..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          {installError && (
            <div className="packages-error">{installError}</div>
          )}

          <div className="packages-results-container">
            {!hasSearchQuery && packages.length === 0 && (
              <div className="packages-empty-state">
                <PackageSearch size={32} />
                <span>Search for packages to install</span>
              </div>
            )}
            {hasSearchQuery && filteredMarketplace.length === 0 && (
              <div className="packages-empty-state">
                <PackageSearch size={24} />
                <span>No packages found</span>
              </div>
            )}
            {filteredMarketplace.length > 0 && (
              <div className="packages-list">
                {filteredMarketplace.map((pkg) => {
                  const installed = selectedProjectRoot
                    ? isInstalledInProject(pkg.installedIn || [], selectedProjectRoot)
                    : false
                  return (
                    <MarketplacePackageRow
                      key={pkg.identifier}
                      pkg={pkg}
                      installed={installed}
                      onClick={() => handleOpenMarketplacePackage(pkg)}
                    />
                  )
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'project' && (
        <div className="packages-tab-content">
          <div className="packages-results-container">
            {!selectedProjectRoot && (
              <div className="packages-empty-state">
                <Package size={32} />
                <span>Select a project to view installed packages</span>
              </div>
            )}
            {selectedProjectRoot && installedDependencies.length === 0 && (
              <div className="packages-empty-state">
                <Package size={32} />
                <span>No packages installed in this project</span>
                <button
                  className="packages-empty-action"
                  onClick={() => setActiveTab('browse')}
                >
                  Browse packages
                </button>
              </div>
            )}
            {selectedProjectRoot && installedDependencies.length > 0 && (
              <div className="packages-list">
                {filteredInstalled.map((dep) => (
                  <InstalledPackageRow
                    key={dep.identifier}
                    dependency={dep}
                    onClick={() => handleOpenInstalledPackage(dep)}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
