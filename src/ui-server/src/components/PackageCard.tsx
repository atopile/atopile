/**
 * PackageCard component - displays a package (installed or available) in the sidebar.
 * Includes version selection, install/update functionality, and build targets.
 */
import { useState, useRef, useEffect, memo } from 'react'
import {
  ChevronDown, ChevronRight, Package, Download, Check,
  Search, ArrowUpCircle, History, Scale, Github, Globe, Layers
} from 'lucide-react'
import { BuildNode } from './BuildNode'
import type {
  Selection,
  Project,
  AvailableProject,
  SelectedPackage
} from './projectsTypes'
import './PackageCard.css'

// Check if a package has an update available
export function hasUpdate(project: Project): boolean {
  if (!project.installed || !project.version || !project.latestVersion) return false
  return project.version !== project.latestVersion
}

// Format download count for display (e.g., 12847 -> "12.8k")
export function formatDownloads(count: number | null | undefined): string {
  if (count == null) return '0'
  if (count >= 1000000) {
    return (count / 1000000).toFixed(1).replace(/\.0$/, '') + 'M'
  }
  if (count >= 1000) {
    return (count / 1000).toFixed(1).replace(/\.0$/, '') + 'k'
  }
  return count.toString()
}

// Check if package is installed in a specific project
// Uses the package's installed_in array which contains project roots/paths
function isInstalledInProject(
  pkg: Project,
  targetProjectPath: string,
  _allProjects: Project[]
): { installed: boolean; version?: string; needsUpdate?: boolean; latestVersion?: string } {
  // The package has an 'installed_in' property with project paths where it's installed
  // We need to check if targetProjectPath matches any of them
  // Note: installed_in may be undefined for packages from mock data

  // For packages from real data, check installed_in array
  const installedIn = (pkg as any).installedIn || []
  const isInstalled = installedIn.some((path: string) =>
    path === targetProjectPath || path.endsWith(`/${targetProjectPath}`) || targetProjectPath.endsWith(path)
  )

  if (!isInstalled) return { installed: false }

  const needsUpdate = pkg.latestVersion && pkg.version && pkg.version !== pkg.latestVersion

  return {
    installed: true,
    version: pkg.version,
    needsUpdate: !!needsUpdate,
    latestVersion: pkg.latestVersion
  }
}

// Install dropdown component
function InstallDropdown({
  project,
  onInstall,
  availableProjects
}: {
  project: Project
  onInstall: (projectId: string, targetProject: string) => void
  availableProjects: AvailableProject[]
}) {
  const [isOpen, setIsOpen] = useState(false)
  const [selectedTargetId, setSelectedTargetId] = useState<string>(() => {
    // Default to active project
    return availableProjects.find(p => p.isActive)?.id || availableProjects[0]?.id || ''
  })
  const [searchQuery, setSearchQuery] = useState('')
  const dropdownRef = useRef<HTMLDivElement>(null)
  const searchInputRef = useRef<HTMLInputElement>(null)

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
        setSearchQuery('')
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Focus search input when dropdown opens (if many projects)
  useEffect(() => {
    if (isOpen && availableProjects.length > 5 && searchInputRef.current) {
      searchInputRef.current.focus()
    }
  }, [isOpen])

  const selectedTarget = availableProjects.find(p => p.id === selectedTargetId)
  const installStatus = isInstalledInProject(project, selectedTarget?.path || selectedTargetId, [])

  const handleInstall = (e: React.MouseEvent) => {
    e.stopPropagation()
    onInstall(project.id, selectedTargetId)
  }

  const handleSelectTarget = (targetId: string) => {
    setSelectedTargetId(targetId)
    setIsOpen(false)
  }

  // Determine button state based on selected target
  const isInstalled = installStatus.installed
  const needsUpdate = installStatus.needsUpdate

  // Truncate project name if too long
  const targetName = selectedTarget?.name || 'project'
  const displayName = targetName.length > 15 ? targetName.slice(0, 12) + '...' : targetName

  return (
    <div className="install-dropdown" ref={dropdownRef}>
      <button
        className={`install-btn install-btn-wide ${isInstalled ? (needsUpdate ? 'update-available' : 'installed') : ''}`}
        onClick={handleInstall}
        title={needsUpdate ? `Update to v${installStatus.latestVersion} in ${selectedTarget?.name}` : `Install to ${selectedTarget?.name}`}
      >
        {isInstalled ? (
          needsUpdate ? (
            <>
              <ArrowUpCircle size={12} />
              <span>Update in {displayName}</span>
            </>
          ) : (
            <>
              <Check size={12} />
              <span>Installed in {displayName}</span>
            </>
          )
        ) : (
          <>
            <Download size={12} />
            <span>Install to {displayName}</span>
          </>
        )}
      </button>
      <button
        className="install-dropdown-toggle"
        onClick={(e) => {
          e.stopPropagation()
          setIsOpen(!isOpen)
        }}
        title={`Change target project (${selectedTarget?.name})`}
      >
        <ChevronDown size={12} />
      </button>
      {isOpen && (
        <div className={`install-dropdown-menu ${availableProjects.length > 5 ? 'scrollable' : ''}`}>
          <div className="dropdown-header">Install to project:</div>
          {availableProjects.length > 5 && (
            <div className="dropdown-search">
              <Search size={10} />
              <input
                ref={searchInputRef}
                type="text"
                placeholder="Filter projects..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onClick={(e) => e.stopPropagation()}
              />
            </div>
          )}
          <div className="dropdown-items">
            {availableProjects
              .filter(p => p.name.toLowerCase().includes(searchQuery.toLowerCase()))
              .map(p => {
                const status = isInstalledInProject(project, p.path, [])
                return (
                  <button
                    key={p.id}
                    className={`dropdown-item ${p.id === selectedTargetId ? 'selected' : ''}`}
                    onClick={(e) => {
                      e.stopPropagation()
                      handleSelectTarget(p.id)
                    }}
                  >
                    <Layers size={12} />
                    <span>{p.name}</span>
                    {status.installed && (
                      <span className={`status-badge ${status.needsUpdate ? 'outdated' : 'installed'}`}>
                        {status.needsUpdate ? `v${status.version}→${status.latestVersion}` : `v${status.version}`}
                      </span>
                    )}
                    {p.id === selectedTargetId && <Check size={12} className="selected-check" />}
                  </button>
                )
              })}
            {availableProjects.filter(p => p.name.toLowerCase().includes(searchQuery.toLowerCase())).length === 0 && (
              <div className="dropdown-empty">No projects match "{searchQuery}"</div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// PackageCard Props
interface PackageCardProps {
  project: Project
  selection: Selection
  onSelect: (selection: Selection) => void
  onBuild: (level: 'project' | 'build' | 'symbol', id: string, label: string) => void
  onCancelBuild?: (buildId: string) => void
  onStageFilter?: (stageName: string, buildId?: string, projectId?: string) => void
  onOpenPackageDetail?: (pkg: SelectedPackage) => void
  onInstall: (projectId: string, targetProject: string) => void
  onOpenSource?: (projectId: string, entry: string) => void
  onOpenKiCad?: (projectId: string, buildId: string) => void
  onOpenLayout?: (projectId: string, buildId: string) => void
  onOpen3D?: (projectId: string, buildId: string) => void
  availableProjects: AvailableProject[]
}

// Package card component (larger, with summary)
// Memoized to prevent unnecessary re-renders in lists
export const PackageCard = memo(function PackageCard({
  project,
  selection,
  onSelect,
  onBuild,
  onCancelBuild,
  onStageFilter,
  onOpenPackageDetail: _onOpenPackageDetail,
  onInstall,
  onOpenSource,
  onOpenKiCad,
  onOpenLayout,
  onOpen3D,
  availableProjects
}: PackageCardProps) {
  const [expanded, setExpanded] = useState(false)
  const [descExpanded, setDescExpanded] = useState(false)
  const [selectedVersion, setSelectedVersion] = useState(project.version || '')
  const isSelected = selection.type === 'project' && selection.projectId === project.id

  const totalWarnings = project.builds.reduce((sum, b) => sum + (b.warnings || 0), 0)

  // Mock available versions - in real implementation this would come from the package data
  const availableVersions = project.latestVersion && project.version && project.latestVersion !== project.version
    ? [project.latestVersion, project.version]
    : project.version ? [project.version] : []

  return (
    <div
      className={`package-card ${isSelected ? 'selected' : ''} ${expanded ? 'expanded' : ''}`}
      onClick={() => {
        setExpanded(!expanded)
        if (expanded) setDescExpanded(false) // Reset desc when collapsing
        onSelect({
          type: 'project',
          projectId: project.id,
          label: project.name
        })
      }}
    >
      {/* Row 1: Package name */}
      <div className="package-card-name-row">
        <span className="tree-expand">
          {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </span>
        <Package size={18} className="package-icon" />
        <span className="package-name">{project.name}</span>
        {totalWarnings > 0 && <span className="warn-badge">{totalWarnings}</span>}
      </div>

      {/* Row 2: Description (summary when collapsed, full when expanded) */}
      {(project.summary || project.description) && (
        <div
          className={`package-card-description ${expanded && !descExpanded ? 'clamped' : ''}`}
          onClick={(e) => {
            if (expanded) {
              e.stopPropagation()
              setDescExpanded(!descExpanded)
            }
          }}
          title={expanded && !descExpanded ? 'Click to expand description' : ''}
        >
          {expanded ? (project.description || project.summary) : project.summary}
        </div>
      )}

      {/* Row 3: Compact actions bar - version, publisher, downloads, github, install */}
      <div className="package-actions-bar">
        {/* Version dropdown */}
        <select
          className="package-version-select"
          value={selectedVersion}
          onChange={(e) => {
            e.stopPropagation()
            setSelectedVersion(e.target.value)
          }}
          onClick={(e) => e.stopPropagation()}
        >
          {availableVersions.map((v, idx) => (
            <option key={v} value={v}>
              {v}{idx === 0 && hasUpdate(project) ? ' (latest)' : ''}
            </option>
          ))}
        </select>

        {/* Publisher badge */}
        {project.publisher && (
          <span
            className={`package-publisher-badge ${project.publisher === 'atopile' ? 'official' : 'community'}`}
            title={`Published by ${project.publisher}`}
          >
            {project.publisher.toLowerCase()}
          </span>
        )}

        {/* Downloads count */}
        {project.downloads !== undefined && project.downloads > 0 && (
          <span className="package-downloads" title={`${project.downloads.toLocaleString()} downloads`}>
            <Download size={10} />
            {formatDownloads(project.downloads)}
          </span>
        )}

        {/* GitHub button */}
        {project.repository && (
          <a
            href={project.repository}
            className="package-link-btn"
            onClick={(e) => e.stopPropagation()}
            target="_blank"
            rel="noopener noreferrer"
            title="View on GitHub"
          >
            <Github size={12} />
          </a>
        )}

        {/* Install dropdown (pushed to right) */}
        <div className="package-install-wrapper" onClick={(e) => e.stopPropagation()}>
          <InstallDropdown project={project} onInstall={onInstall} availableProjects={availableProjects} />
        </div>
      </div>

      {/* Expanded content */}
      {expanded && (
        <>
          {/* Package Stats Bar with Links */}
          <div className="package-stats-bar">
            {project.publisher && (
              <div className={`package-stat publisher ${project.publisher === 'atopile' ? 'official' : 'community'}`}>
                <span>{project.publisher.toLowerCase()}</span>
              </div>
            )}
            {project.downloads !== undefined && project.downloads > 0 && (
              <div className="package-stat">
                <Download size={11} />
                <span>{formatDownloads(project.downloads)}</span>
              </div>
            )}
            {project.versionCount !== undefined && project.versionCount > 0 && (
              <div className="package-stat">
                <History size={11} />
                <span>{project.versionCount} releases</span>
              </div>
            )}
            {project.license && (
              <div className="package-stat license">
                <Scale size={11} />
                <span>{project.license}</span>
              </div>
            )}

            {/* Links on right side */}
            <div className="package-stat-links">
              {project.homepage && (
                <a
                  href={project.homepage}
                  className="package-stat-link"
                  onClick={(e) => e.stopPropagation()}
                  target="_blank"
                  rel="noopener noreferrer"
                  title="Homepage"
                >
                  <Globe size={12} />
                </a>
              )}
              {project.repository && (
                <a
                  href={project.repository}
                  className="package-stat-link"
                  onClick={(e) => e.stopPropagation()}
                  target="_blank"
                  rel="noopener noreferrer"
                  title="GitHub Repository"
                >
                  <Github size={12} />
                </a>
              )}
            </div>
          </div>

          {/* Build targets */}
          <div className="package-card-builds">
            {project.builds.map((build, idx) => (
              <BuildNode
                key={`${build.id}-${idx}`}
                build={build}
                projectId={project.id}
                selection={selection}
                onSelect={onSelect}
                onBuild={onBuild}
                onCancelBuild={onCancelBuild}
                onStageFilter={onStageFilter}
                onOpenSource={onOpenSource}
                onOpenKiCad={onOpenKiCad}
                onOpenLayout={onOpenLayout}
                onOpen3D={onOpen3D}
              />
            ))}
          </div>
        </>
      )}
    </div>
  )
})
