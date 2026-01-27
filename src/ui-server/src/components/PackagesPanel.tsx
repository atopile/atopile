/**
 * PackagesPanel - VS Code-style package browser
 *
 * Layout:
 * - Search at top (filters both installed and marketplace)
 * - Collapsible INSTALLED section with count
 * - Marketplace results below
 */

import { useMemo, useState } from 'react'
import { ChevronDown, ChevronRight, Package, PackageSearch, Search, CheckCircle } from 'lucide-react'
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

// Installed package row - matches marketplace layout with version
function InstalledPackageRow({
  dependency,
  onClick,
}: {
  dependency: ProjectDependency
  onClick: () => void
}) {
  return (
    <div className="marketplace-package-row installed" onClick={onClick}>
      <Package size={14} className="marketplace-package-icon" />
      <div className="marketplace-package-info">
        <div className="marketplace-package-header">
          <span className="marketplace-package-name">{dependency.name}</span>
          <CheckCircle size={12} className="marketplace-installed-badge" />
        </div>
        {dependency.summary && (
          <div className="marketplace-package-summary">{dependency.summary}</div>
        )}
      </div>
      <div className="marketplace-package-meta">
        <span className="marketplace-package-publisher">{dependency.publisher}</span>
        <span className="marketplace-package-version">{dependency.version}</span>
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
    <div className={`marketplace-package-row ${installed ? 'installed' : ''}`} onClick={onClick}>
      <Package size={14} className="marketplace-package-icon" />
      <div className="marketplace-package-info">
        <div className="marketplace-package-header">
          <span className="marketplace-package-name">{pkg.name}</span>
          {installed && <CheckCircle size={12} className="marketplace-installed-badge" />}
        </div>
        {pkg.summary && (
          <div className="marketplace-package-summary">{pkg.summary}</div>
        )}
      </div>
      <div className="marketplace-package-meta">
        <span className="marketplace-package-publisher">{pkg.publisher}</span>
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
  const [searchQuery, setSearchQuery] = useState('')
  const [installedOpen, setInstalledOpen] = useState(true)

  // Filter installed packages by search query
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
  const showInstalledSection = !hasSearchQuery || filteredInstalled.length > 0
  const showMarketplaceSection = hasSearchQuery || filteredMarketplace.length > 0

  return (
    <div className="packages-panel">
      {/* Search - always at top */}
      <div className="packages-search-bar">
        <Search size={14} />
        <input
          type="text"
          placeholder="Search packages..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
      </div>

      {installError && (
        <div className="packages-error">{installError}</div>
      )}

      <div className="packages-sections">
        {/* Installed section */}
        {showInstalledSection && (
          <div className="packages-section">
            <button
              className="packages-section-header"
              onClick={() => setInstalledOpen((prev) => !prev)}
            >
              <span className="section-toggle">
                {installedOpen ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
              </span>
              <span className="section-title">INSTALLED</span>
              <span className="section-count">{filteredInstalled.length}</span>
            </button>

            {installedOpen && (
              <div className="packages-section-content">
                {selectedProjectRoot ? (
                  filteredInstalled.length > 0 ? (
                    filteredInstalled.map((dep) => (
                      <InstalledPackageRow
                        key={dep.identifier}
                        dependency={dep}
                        onClick={() => handleOpenInstalledPackage(dep)}
                      />
                    ))
                  ) : (
                    <div className="packages-empty-hint">
                      {hasSearchQuery ? 'No matching installed packages' : 'No packages installed'}
                    </div>
                  )
                ) : (
                  <div className="packages-empty-hint">
                    Select a project to view installed packages
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Marketplace / Search Results */}
        {showMarketplaceSection && (
          <div className="packages-section">
            {hasSearchQuery && (
              <div className="packages-section-header static">
                <span className="section-title">MARKETPLACE</span>
                <span className="section-count">{filteredMarketplace.length}</span>
              </div>
            )}

            <div className="packages-section-content">
              {filteredMarketplace.length > 0 ? (
                filteredMarketplace.map((pkg) => {
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
                })
              ) : (
                <div className="packages-empty-state">
                  <PackageSearch size={24} />
                  <span>No packages found</span>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
