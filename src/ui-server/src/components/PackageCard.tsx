/**
 * PackageCard component - displays a package (installed or available) in the sidebar.
 * Includes version selection, install/update functionality, and build targets.
 */
import { useState, useRef, useEffect, memo } from 'react'
import {
  ChevronDown, ChevronRight, Package, Download, Check,
  Search, ArrowUpCircle, Layers, Loader2, ExternalLink
} from 'lucide-react'
import { BuildsCard } from './BuildsCard'
import { DependencyCard, type ProjectDependency } from './DependencyCard'
import { FileExplorer, type FileTreeNode } from './FileExplorer'
import { sendActionWithResponse } from '../api/websocket'
import type {
  Selection,
  Project,
  AvailableProject,
  SelectedPackage
} from './projectsTypes'
import type { PackageDetails } from '../types/build'
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
function isInstalledInProject(
  pkg: Project,
  targetProjectPath: string
): { installed: boolean; version?: string; needsUpdate?: boolean; latestVersion?: string } {
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

// Version selector dropdown (custom, not native select)
function VersionSelector({
  versions,
  selectedVersion,
  onVersionChange,
  latestVersion
}: {
  versions: string[]
  selectedVersion: string
  onVersionChange: (version: string) => void
  latestVersion?: string
}) {
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Filter out invalid versions
  const validVersions = versions.filter(v => v && v !== 'unknown')
  if (validVersions.length === 0) return null

  // Use selectedVersion only if it's valid, otherwise use first valid version
  const validSelectedVersion = selectedVersion && selectedVersion !== 'unknown' ? selectedVersion : null
  const displayVersion = validSelectedVersion || validVersions[0] || ''

  return (
    <div className="version-selector" ref={dropdownRef}>
      <button
        className="version-selector-btn"
        onClick={(e) => {
          e.stopPropagation()
          setIsOpen(!isOpen)
        }}
        title="Select version"
      >
        <span className="version-selector-value">{displayVersion}</span>
        <ChevronDown size={10} />
      </button>
      {isOpen && (
        <div className="version-selector-menu">
          {validVersions.map((v) => (
            <button
              key={v}
              className={`version-option ${v === selectedVersion ? 'selected' : ''}`}
              onClick={(e) => {
                e.stopPropagation()
                onVersionChange(v)
                setIsOpen(false)
              }}
            >
              <span>{v}</span>
              {v === latestVersion && <span className="latest-tag">latest</span>}
              {v === selectedVersion && <Check size={12} className="selected-check" />}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

// Project selector dropdown for install target
function ProjectSelector({
  availableProjects,
  selectedProjectId,
  onSelect
}: {
  availableProjects: AvailableProject[]
  selectedProjectId: string
  onSelect: (projectId: string) => void
}) {
  const [isOpen, setIsOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const dropdownRef = useRef<HTMLDivElement>(null)
  const searchInputRef = useRef<HTMLInputElement>(null)

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

  useEffect(() => {
    if (isOpen && availableProjects.length > 5 && searchInputRef.current) {
      searchInputRef.current.focus()
    }
  }, [isOpen, availableProjects.length])

  const selectedProject = availableProjects.find(p => p.id === selectedProjectId)
  const displayName = selectedProject?.name || 'project'

  return (
    <div className="project-selector" ref={dropdownRef}>
      <button
        className="project-selector-btn"
        onClick={(e) => {
          e.stopPropagation()
          setIsOpen(!isOpen)
        }}
        title={`Install to: ${selectedProject?.name}`}
      >
        <span className="project-selector-name">{displayName}</span>
        <ChevronDown size={10} />
      </button>
      {isOpen && (
        <div className="project-selector-menu">
          <div className="dropdown-header">Install to:</div>
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
              .map(p => (
                <button
                  key={p.id}
                  className={`dropdown-item ${p.id === selectedProjectId ? 'selected' : ''}`}
                  onClick={(e) => {
                    e.stopPropagation()
                    onSelect(p.id)
                    setIsOpen(false)
                  }}
                >
                  <Layers size={12} />
                  <span>{p.name}</span>
                  {p.id === selectedProjectId && <Check size={12} className="selected-check" />}
                </button>
              ))}
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
  onInstall: (projectId: string, targetProject: string, version?: string) => void
  onOpenSource?: (projectId: string, entry: string) => void
  onOpenKiCad?: (projectId: string, buildId: string) => void
  onOpenLayout?: (projectId: string, buildId: string) => void
  onOpen3D?: (projectId: string, buildId: string) => void
  availableProjects: AvailableProject[]
  isInstalling?: boolean
}

// Package card component
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
  availableProjects,
  isInstalling = false
}: PackageCardProps) {
  const [expanded, setExpanded] = useState(false)
  const [descExpanded, setDescExpanded] = useState(false)
  const [selectedVersion, setSelectedVersion] = useState(() => {
    const version = project.version && project.version !== 'unknown' ? project.version : null
    const latestVersion = project.latestVersion && project.latestVersion !== 'unknown' ? project.latestVersion : null
    return version || latestVersion || ''
  })
  const [selectedProjectId, setSelectedProjectId] = useState(() => {
    return availableProjects.find(p => p.isActive)?.id || availableProjects[0]?.id || ''
  })

  // Package details state (fetched on expand)
  const [packageDetails, setPackageDetails] = useState<PackageDetails | null>(null)
  const [detailsLoading, setDetailsLoading] = useState(false)
  const [detailsError, setDetailsError] = useState<string | null>(null)

  const isSelected = selection.type === 'project' && selection.projectId === project.id

  const selectedTarget = availableProjects.find(p => p.id === selectedProjectId)
  const installStatus = isInstalledInProject(project, selectedTarget?.path || selectedProjectId)

  // Fetch package details when expanded
  useEffect(() => {
    if (expanded && !packageDetails && !detailsLoading) {
      setDetailsLoading(true)
      setDetailsError(null)

      sendActionWithResponse('getPackageDetails', { packageId: project.id })
        .then(response => {
          const result = response.result ?? {}
          const details = (result as { details?: PackageDetails }).details
          if (details) {
            setPackageDetails(details)
            if (details.versions?.length > 0 && !selectedVersion) {
              setSelectedVersion(details.versions[0].version)
            }
          } else {
            setDetailsError('Failed to load package details')
          }
        })
        .catch(err => {
          setDetailsError(err.message || 'Failed to load package details')
        })
        .finally(() => {
          setDetailsLoading(false)
        })
    }
  }, [expanded, packageDetails, detailsLoading, project.id, selectedVersion])

  const handleInstall = (e: React.MouseEvent) => {
    e.stopPropagation()
    onInstall(project.id, selectedProjectId, selectedVersion || undefined)
  }

  // Build available versions list (filter out 'unknown')
  const rawVersions = packageDetails?.versions?.map((v: { version: string }) => v.version) ||
    (project.latestVersion && project.version && project.latestVersion !== project.version
      ? [project.latestVersion, project.version]
      : project.version ? [project.version] : project.latestVersion ? [project.latestVersion] : [])
  const versions = rawVersions.filter(v => v && v !== 'unknown')

  // Convert dependencies to DependencyCard format
  const dependencies: ProjectDependency[] = (packageDetails?.dependencies || []).map(dep => {
    const parts = dep.identifier.split('/')
    const publisher = parts.length === 2 ? parts[0] : 'unknown'
    const name = parts.length === 2 ? parts[1] : dep.identifier
    return {
      identifier: dep.identifier,
      version: dep.version || 'latest',
      name,
      publisher,
    }
  })

  // Convert to file tree format
  const fileTree: FileTreeNode[] = [] // TODO: Add when backend provides files list

  return (
    <div
      className={`package-card ${isSelected ? 'selected' : ''} ${expanded ? 'expanded' : ''}`}
      onClick={() => {
        if (isSelected) {
          // If already selected, deselect and collapse
          setExpanded(false)
          setDescExpanded(false)
          onSelect({ type: 'none' })
        } else {
          // If not selected, select and expand
          setExpanded(true)
          onSelect({
            type: 'project',
            projectId: project.id,
            label: project.name
          })
        }
      }}
    >
      {/* Row 1: Package name + publisher */}
      <div className="package-card-header">
        <span className="tree-expand">
          {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </span>
        <Package size={16} className="package-icon" />
        <span className="package-name">{project.name}</span>
        {project.publisher && (
          <span className={`package-publisher-tag ${project.publisher === 'atopile' ? 'official' : ''}`}>
            {project.publisher.toLowerCase()}
          </span>
        )}
        {project.homepage && (
          <a
            href={project.homepage}
            className="package-external-link"
            target="_blank"
            rel="noopener noreferrer"
            title="Open homepage"
            onClick={(e) => e.stopPropagation()}
          >
            <ExternalLink size={12} />
          </a>
        )}
      </div>

      {/* Row 2: Description + metadata */}
      {(project.summary || project.description) && (
        <div
          className={`package-card-description ${!expanded ? 'clamped' : ''} ${expanded && !descExpanded ? 'clamped' : ''}`}
          onClick={(e) => {
            if (expanded) {
              e.stopPropagation()
              setDescExpanded(!descExpanded)
            }
          }}
        >
          {expanded ? (project.description || project.summary) : project.summary}
        </div>
      )}

      {/* Row 3: Install bar (project -> version -> install button) */}
      <div className="package-install-bar" onClick={(e) => e.stopPropagation()}>
        {/* Project selector */}
        <ProjectSelector
          availableProjects={availableProjects}
          selectedProjectId={selectedProjectId}
          onSelect={setSelectedProjectId}
        />

        {/* Version selector */}
        {versions.length > 0 && (
          <VersionSelector
            versions={versions}
            selectedVersion={selectedVersion}
            onVersionChange={setSelectedVersion}
            latestVersion={project.latestVersion}
          />
        )}

        {/* Install button */}
        <button
          className={`install-btn ${isInstalling ? 'installing' : ''} ${installStatus.installed ? (installStatus.needsUpdate ? 'update-available' : 'installed') : ''}`}
          onClick={handleInstall}
          disabled={isInstalling}
          title={isInstalling
            ? 'Installing...'
            : installStatus.needsUpdate
              ? `Update to ${selectedVersion} in ${selectedTarget?.name}`
              : installStatus.installed
                ? `Installed in ${selectedTarget?.name}`
                : `Install ${selectedVersion} to ${selectedTarget?.name}`}
        >
          {isInstalling ? (
            <>
              <Loader2 size={14} className="spin" />
              <span>Installing...</span>
            </>
          ) : installStatus.installed ? (
            installStatus.needsUpdate ? (
              <>
                <ArrowUpCircle size={14} />
                <span>Update</span>
              </>
            ) : (
              <>
                <Check size={14} />
                <span>Installed</span>
              </>
            )
          ) : (
            <>
              <Download size={14} />
              <span>Install</span>
            </>
          )}
        </button>
      </div>

      {/* Expanded content */}
      {expanded && (
        <div className="package-expanded-content">
          {/* Build targets using shared BuildsCard */}
          {project.builds.length > 0 && (
            <BuildsCard
              builds={project.builds}
              projectId={project.id}
              projectRoot={project.root || ''}
              selection={selection}
              onSelect={onSelect}
              onBuild={onBuild}
              onCancelBuild={onCancelBuild}
              onStageFilter={onStageFilter}
              onOpenSource={onOpenSource}
              onOpenKiCad={onOpenKiCad}
              onOpenLayout={onOpenLayout}
              onOpen3D={onOpen3D}
              readOnly={true}
            />
          )}

          {/* Loading state for details */}
          {detailsLoading && (
            <div className="package-loading">
              <Loader2 size={16} className="spin" />
              <span>Loading package details...</span>
            </div>
          )}

          {/* Error state */}
          {detailsError && (
            <div className="package-error">
              <span>Failed to load details: {detailsError}</span>
            </div>
          )}

          {/* Package metadata bar */}
          {packageDetails && !detailsLoading && (
            <div className="package-meta-bar">
              {packageDetails.downloads !== undefined && packageDetails.downloads > 0 && (
                <span className="meta-item">
                  <Download size={11} />
                  {formatDownloads(packageDetails.downloads)}
                </span>
              )}
              {packageDetails.versionCount > 0 && (
                <span className="meta-item">{packageDetails.versionCount} versions</span>
              )}
              {packageDetails.license && (
                <span className="meta-item">{packageDetails.license}</span>
              )}
            </div>
          )}

          {/* Dependencies (once loaded) */}
          {packageDetails && dependencies.length > 0 && (
            <DependencyCard
              dependencies={dependencies}
              projectId={project.id}
              readOnly={true}
            />
          )}

          {/* File explorer (once loaded) */}
          {packageDetails && fileTree.length > 0 && (
            <FileExplorer
              files={fileTree}
              onFileClick={(path: string) => onOpenSource?.(project.id, path)}
            />
          )}
        </div>
      )}
    </div>
  )
})
