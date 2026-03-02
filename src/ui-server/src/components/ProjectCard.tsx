/**
 * ProjectCard - Unified component for displaying projects and packages.
 * A package is just a project with additional package metadata (version, publisher, install status).
 *
 * Modes:
 * - editable (local projects): Can edit name/description, has build controls
 * - readOnly (packages): No editing, has install bar and package metadata
 *
 * See COMPONENT_ARCHITECTURE.md for the full editability matrix.
 */
import { useState, useEffect, memo, useMemo, useRef } from 'react'
import {
  ChevronDown, ChevronRight, Play, Layers, Package,
  AlertCircle, AlertTriangle, Square, Download, Check,
  Search, ArrowUpCircle, Loader2, ExternalLink
} from 'lucide-react'
import { formatRelativeTime } from './BuildNode'
import { StatusIcon } from './StatusIcon'
import { BuildsCard } from './BuildsCard'
import { ProjectExplorerCard } from './ProjectExplorerCard'
import { FileExplorer, type FileTreeNode } from './FileExplorer'
import { DependencyCard, type ProjectDependency } from './DependencyCard'
import { NameValidationDropdown } from './NameValidationDropdown'
import { MetadataBar } from './shared/MetadataBar'
import { UsageCard } from './UsageCard'
import { validateName } from '../utils/nameValidation'
import { compareVersionsDesc, isInstalledInProject } from '../utils/packageUtils'
import { generateImportStatement, generateUsageExample } from '../utils/codeHighlight'
import { sendActionWithResponse } from '../api/websocket'
import { useStore } from '../store'
import type { BuildTarget as ProjectBuildTarget, PackageDetails } from '../types/build'
import type {
  Selection,
  BuildTarget as UiBuildTarget,
  Project,
  ModuleDefinition,
  AvailableProject
} from './projectsTypes'
import './ProjectCard.css'

// Version selector dropdown
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

  const validVersions = versions.filter(v => v && v !== 'unknown')
  if (validVersions.length === 0) return null

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

// Project selector dropdown
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

// Check if package is installed in a specific project (returns detailed status)
function getInstallStatus(
  pkg: Project,
  targetProjectPath: string
): { installed: boolean; version?: string; needsUpdate?: boolean; latestVersion?: string } {
  const installedIn = (pkg as any).installedIn || []
  const installed = isInstalledInProject(installedIn, targetProjectPath)

  if (!installed) return { installed: false }

  const needsUpdate = pkg.latestVersion && pkg.version && pkg.version !== pkg.latestVersion

  return {
    installed: true,
    version: pkg.version,
    needsUpdate: !!needsUpdate,
    latestVersion: pkg.latestVersion
  }
}

// ProjectCard Props
// Preset configurations for different view contexts
export type ProjectCardPreset = 'localProject' | 'packageExplorer' | 'dependencyExpanded';

interface PresetFlags {
  readOnly: boolean;
  showInstallBar: boolean;
  showBuildControls: boolean;
  showUsageExamples: boolean;
  showMetadata: boolean;
  showModuleExplorer: boolean;
  showFileExplorer: boolean;
}

const PRESET_FLAGS: Record<ProjectCardPreset, PresetFlags> = {
  localProject: {
    readOnly: false,
    showInstallBar: false,
    showBuildControls: true,
    showUsageExamples: false,
    showMetadata: false,
    showModuleExplorer: true,
    showFileExplorer: true,
  },
  packageExplorer: {
    readOnly: true,
    showInstallBar: true,
    showBuildControls: false,
    showUsageExamples: true,
    showMetadata: true,
    showModuleExplorer: false,  // Package may not be installed locally
    showFileExplorer: false,
  },
  dependencyExpanded: {
    readOnly: true,
    showInstallBar: false,  // Already installed as dependency
    showBuildControls: false,
    showUsageExamples: true,
    showMetadata: true,
    showModuleExplorer: true,
    showFileExplorer: true,
  },
};

interface ProjectCardProps {
  project: Project
  selection: Selection
  onSelect: (selection: Selection) => void
  onBuild: (level: 'project' | 'build' | 'symbol', id: string, label: string) => void
  onCancelBuild?: (buildId: string) => void
  onStageFilter?: (stageName: string, buildId?: string, projectId?: string) => void
  isExpanded: boolean
  onExpandChange: (projectId: string, expanded: boolean) => void

  // Preset (recommended) - sets multiple flags at once
  preset?: ProjectCardPreset

  // Edit mode props (for local projects)
  onUpdateProject?: (projectId: string, updates: Partial<Project>) => void
  onAddBuild?: (projectId: string) => void
  onUpdateBuild?: (projectId: string, buildId: string, updates: Partial<UiBuildTarget>) => void
  onDeleteBuild?: (projectId: string, buildId: string) => void
  onProjectExpand?: (projectRoot: string) => void
  onDependencyVersionChange?: (projectId: string, identifier: string, newVersion: string) => void
  onRemoveDependency?: (projectId: string, identifier: string) => void

  // Common props
  onOpenSource?: (projectId: string, entry: string) => void
  onOpenKiCad?: (projectId: string, buildId: string) => void
  onOpenLayout?: (projectId: string, buildId: string) => void
  onOpen3D?: (projectId: string, buildId: string) => void
  onFileClick?: (projectId: string, filePath: string) => void

  // Data props
  availableModules?: ModuleDefinition[]
  projectFiles?: FileTreeNode[]
  projectDependencies?: ProjectDependency[]
  projectFilesByRoot?: Record<string, FileTreeNode[]>
  projectBuildsByRoot?: Record<string, ProjectBuildTarget[]>  // Builds for installed dependencies (from local ato.yaml)
  updatingDependencyIds?: string[]  // IDs of dependencies being updated (format: projectRoot:dependencyId)

  // Package mode props (can override preset or use directly)
  readOnly?: boolean  // If true, show as package (no editing)
  availableProjects?: AvailableProject[]  // For install target selection
  onInstall?: (projectId: string, targetProject: string, version?: string) => void
  isInstalling?: boolean
}

export const ProjectCard = memo(function ProjectCard({
  project,
  selection,
  onSelect,
  onBuild,
  onCancelBuild,
  onStageFilter,
  isExpanded,
  onExpandChange,
  preset,
  onUpdateProject,
  onAddBuild,
  onUpdateBuild,
  onDeleteBuild,
  onProjectExpand,
  onDependencyVersionChange,
  onRemoveDependency,
  onOpenSource,
  onOpenKiCad,
  onOpenLayout,
  onOpen3D,
  onFileClick,
  availableModules = [],
  projectFiles = [],
  projectDependencies = [],
  projectFilesByRoot = {},
  projectBuildsByRoot = {},
  updatingDependencyIds = [],
  readOnly: readOnlyProp,
  availableProjects = [],
  onInstall,
  isInstalling = false
}: ProjectCardProps) {
  // Derive feature flags from preset or props
  const presetFlags = preset ? PRESET_FLAGS[preset] : null;
  const readOnly = readOnlyProp ?? presetFlags?.readOnly ?? false;
  const showInstallBar = presetFlags?.showInstallBar ?? (readOnly && availableProjects.length > 0);
  const showBuildControls = presetFlags?.showBuildControls ?? !readOnly;
  const showUsageExamples = presetFlags?.showUsageExamples ?? readOnly;
  const showMetadata = presetFlags?.showMetadata ?? readOnly;
  const showModuleExplorer = presetFlags?.showModuleExplorer ?? !readOnly;
  const showFileExplorer = presetFlags?.showFileExplorer ?? !readOnly;
  const expanded = isExpanded
  const [isEditingName, setIsEditingName] = useState(false)
  const [isEditingDesc, setIsEditingDesc] = useState(false)
  const [projectName, setProjectName] = useState(project.name)
  const [description, setDescription] = useState(project.summary || '')
  const [descExpanded, setDescExpanded] = useState(false)
  const isSelected = selection.type === 'project' && selection.projectId === project.id

  // Migration state from store
  const migratingProjectRoots = useStore((state) => state.migratingProjectRoots)
  const migrationErrors = useStore((state) => state.migrationErrors)
  const isMigrating = migratingProjectRoots.includes(project.root)
  const migrationError = migrationErrors[project.root]

  // Build status (for editable mode) - use project.builds here since builds variable isn't defined yet
  const totalErrors = project.builds.reduce((sum, b) => sum + (b.errors || 0), 0)
  const totalWarnings = project.builds.reduce((sum, b) => sum + (b.warnings || 0), 0)
  const isBuilding = project.builds.some(b => b.status === 'building')

  // Live timer for building state
  const buildingBuilds = project.builds.filter(b => b.status === 'building')
  const maxElapsedFromBuilds = buildingBuilds.length > 0
    ? Math.max(...buildingBuilds.map(b => b.elapsedSeconds ?? 0))
    : 0
  const displayElapsed = isBuilding ? maxElapsedFromBuilds : 0

  const formatBuildTime = (seconds: number): string => {
    const hrs = Math.floor(seconds / 3600)
    const mins = Math.floor((seconds % 3600) / 60)
    const secs = Math.floor(seconds % 60)
    if (hrs > 0) {
      return `${hrs}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
    }
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  // Package mode state
  // Always default to latest version - we'll update when details load
  // Track if user has manually changed the version to avoid overwriting their choice
  const userHasSelectedVersion = useRef(false)
  const [selectedVersion, setSelectedVersion] = useState(() => {
    // Prefer latestVersion, but mark that user hasn't explicitly chosen yet
    const latestVersion = project.latestVersion && project.latestVersion !== 'unknown' ? project.latestVersion : null
    return latestVersion || ''
  })
  const [selectedProjectId, setSelectedProjectId] = useState(() => {
    return availableProjects.find(p => p.isActive)?.id || availableProjects[0]?.id || ''
  })

  // Package details (fetched on expand for packages)
  const [packageDetails, setPackageDetails] = useState<PackageDetails | null>(null)
  const [detailsLoading, setDetailsLoading] = useState(false)
  const [detailsError, setDetailsError] = useState<string | null>(null)

  // Fetch package details when expanded (package mode only)
  // Skip for dependencyExpanded - all data is available locally
  useEffect(() => {
    // For dependencies, we have all data locally - no need to fetch from registry
    if (preset === 'dependencyExpanded') return
    if (!readOnly || !expanded || packageDetails || detailsLoading) return

    setDetailsLoading(true)
    setDetailsError(null)

    sendActionWithResponse('getPackageDetails', { packageId: project.id }, { timeoutMs: 15000 })
      .then(response => {
        const result = response.result ?? {}
        const details = (result as { details?: PackageDetails }).details
        if (details) {
          setPackageDetails(details)
          const sortedDetailVersions = (details.versions || [])
            .map((v) => v.version)
            .filter((v) => v && v !== 'unknown')
            .sort(compareVersionsDesc)
          // Always update to latest version unless user has explicitly selected a different version
          if (sortedDetailVersions.length > 0 && !userHasSelectedVersion.current) {
            setSelectedVersion(sortedDetailVersions[0])
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
  }, [readOnly, expanded, packageDetails, detailsLoading, project.id, selectedVersion, preset])

  const defaultDescription = "A new atopile project!"
  const displayDescription = description || project.description || defaultDescription
  const isDefaultDesc = !description && !project.description

  // Name validation
  const nameValidation = useMemo(() => validateName(projectName), [projectName])

  const handleNameSave = () => {
    if (!nameValidation.isValid) return
    setIsEditingName(false)
    onUpdateProject?.(project.id, { name: projectName })
  }

  const handleDescriptionSave = () => {
    setIsEditingDesc(false)
    onUpdateProject?.(project.id, { summary: description })
  }

  // Install handling (package mode)
  const selectedTarget = availableProjects.find(p => p.id === selectedProjectId)
  const installStatus = getInstallStatus(project, selectedTarget?.path || selectedProjectId)

  const handleInstall = (e: React.MouseEvent) => {
    e.stopPropagation()
    onInstall?.(project.id, selectedProjectId, selectedVersion || undefined)
  }

  // Build available versions list
  const rawVersions = packageDetails?.versions?.map((v: { version: string }) => v.version) ||
    (project.latestVersion && project.version && project.latestVersion !== project.version
      ? [project.latestVersion, project.version]
      : project.version ? [project.version] : project.latestVersion ? [project.latestVersion] : [])
  const versions = rawVersions
    .filter(v => v && v !== 'unknown')
    .sort(compareVersionsDesc)

  // Convert dependencies to DependencyCard format
  const dependencies: ProjectDependency[] = readOnly
    ? (packageDetails?.dependencies || []).map(dep => {
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
    : projectDependencies

  // For packages, compute the actual filesystem path if installed
  // Packages are installed at <project_root>/.ato/modules/<package_id>/
  const packagePath = readOnly && packageDetails?.installedIn?.[0]
    ? `${packageDetails.installedIn[0]}/.ato/modules/${project.id}`
    : project.root

  // For dependencies/packages, prefer local builds (from fetchBuilds) over remote packageDetails
  // This allows the Explorer to show immediately without waiting for remote fetch
  const localBuilds = projectBuildsByRoot[project.root]
  const builds: UiBuildTarget[] = readOnly
    ? (localBuilds && localBuilds.length > 0)
      // Use local builds (from ato.yaml via fetchBuilds)
      ? localBuilds.map((b, idx) => ({
          id: b.name || `build-${idx}`,
          name: b.name || 'default',
          entry: b.entry || '',
          root: packagePath,
          status: 'idle' as const,
        }))
      // Fall back to remote packageDetails if local not available yet
      : packageDetails?.builds
        ? packageDetails.builds.map((build, idx) => {
            const name = typeof build === 'string' ? build : build.name
            const entry = typeof build === 'string' ? '' : build.entry
            return {
              id: name || `build-${idx}`,
              name: name || 'default',
              entry: entry || '',
            root: packagePath,
            status: 'idle' as const,
          }
        })
        : []
    : project.builds

  const isPackage = readOnly || project.type === 'package'
  const Icon = isPackage ? Package : Layers

  return (
    <div
      className={`project-card ${isSelected ? 'selected' : ''} ${expanded ? 'expanded' : 'collapsed'} ${isBuilding ? 'building' : ''} ${isPackage ? 'package-mode' : ''}`}
      onClick={() => {
        const willExpand = !expanded
        onExpandChange(project.id, willExpand)
        onSelect({
          type: 'project',
          projectId: project.id,
          label: project.name
        })
        if (willExpand && onProjectExpand) {
          onProjectExpand(project.root)
        }
      }}
    >
      {/* Header row */}
      <div className="project-card-name-row">
        <span className="tree-expand">
          {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </span>
        <Icon size={18} className={`project-icon ${isPackage ? 'package' : ''}`} />

        {/* Name - editable only in edit mode when expanded */}
        {isEditingName && expanded && !readOnly ? (
          <div className="name-input-wrapper" onClick={(e) => e.stopPropagation()}>
            <input
              type="text"
              className={`project-name-input ${!nameValidation.isValid ? 'invalid' : ''}`}
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              onBlur={() => {
                if (nameValidation.isValid) handleNameSave()
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleNameSave()
                if (e.key === 'Escape') {
                  setProjectName(project.name)
                  setIsEditingName(false)
                }
              }}
              autoFocus
            />
            <NameValidationDropdown
              validation={nameValidation}
              onApplySuggestion={(s) => setProjectName(s)}
            />
          </div>
        ) : (
          <span
            className={`project-card-name ${expanded && !readOnly ? 'editable' : ''}`}
            onClick={expanded && !readOnly ? (e) => {
              e.stopPropagation()
              setIsEditingName(true)
            } : undefined}
            title={expanded && !readOnly ? "Click to edit name" : undefined}
          >
            {projectName}
          </span>
        )}

        {/* Publisher badge (package mode) */}
        {isPackage && project.publisher && (
          <span className={`package-publisher-tag ${project.publisher === 'atopile' ? 'official' : ''}`}>
            {project.publisher.toLowerCase()}
          </span>
        )}

        {/* External link (package mode) */}
        {isPackage && project.homepage && (
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

        {/* Status indicators and build button */}
        {showBuildControls && (
          <div className="project-card-actions-row">
            <div className="project-indicators">
              {isBuilding && (
                <span className="build-time-indicator" title="Build time">
                  <span className="build-time">{formatBuildTime(displayElapsed)}</span>
                </span>
              )}
              {!isBuilding && (
                <>
                  {totalErrors > 0 && (
                    <span className="error-indicator">
                      <AlertCircle size={12} />
                      <span>{totalErrors}</span>
                    </span>
                  )}
                  {totalWarnings > 0 && (
                    <span className="warning-indicator">
                      <AlertTriangle size={12} />
                      <span>{totalWarnings}</span>
                    </span>
                  )}
                  {project.lastBuildTimestamp && (
                    <span className="last-build-info" title={`Last build: ${project.lastBuildStatus || 'unknown'}`}>
                      {project.lastBuildStatus && <StatusIcon status={project.lastBuildStatus as any} size={10} dimmed />}
                      <span className="last-build-time">{formatRelativeTime(project.lastBuildTimestamp)}</span>
                    </span>
                  )}
                </>
              )}
            </div>

            {isBuilding ? (
              <button
                className="project-build-btn-icon stop"
                onClick={(e) => {
                  e.stopPropagation()
                  project.builds
                    .filter(b => b.status === 'building' && b.buildId)
                    .forEach(b => onCancelBuild?.(b.buildId!))
                }}
                title={`Stop all builds in ${project.name}`}
              >
                <Square size={12} fill="currentColor" />
              </button>
            ) : (
              <button
                className={`project-build-btn-icon${isMigrating ? ' migrating' : ''}${migrationError ? ' has-error' : ''}`}
                onClick={(e) => {
                  e.stopPropagation()
                  if (!project.needsMigration) {
                    onBuild('project', project.id, project.name)
                  }
                }}
                disabled={isMigrating || project.needsMigration}
                title={migrationError ? `Migration failed: ${migrationError}` : (isMigrating ? 'Migrating...' : (project.needsMigration ? 'Use the migrate flow before building your project!' : `Build all targets in ${project.name}`))}
              >
                {isMigrating ? <Loader2 size={14} className="spin" /> : <Play size={14} fill="currentColor" />}
              </button>
            )}
          </div>
        )}
      </div>

      {/* Description row - only show in collapsed view for packages, always show when expanded */}
      {((project.summary || project.description || !readOnly) && (readOnly || expanded)) && (
        <div
          className={`project-card-description ${!expanded ? 'clamped' : ''} ${expanded && !descExpanded ? 'clamped' : ''}`}
          onClick={expanded && readOnly ? (e) => {
            e.stopPropagation()
            setDescExpanded(!descExpanded)
          } : undefined}
        >
          {isEditingDesc && !readOnly ? (
            <input
              type="text"
              className="description-input"
              value={description}
              placeholder={defaultDescription}
              onChange={(e) => setDescription(e.target.value)}
              onBlur={handleDescriptionSave}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleDescriptionSave()
                if (e.key === 'Escape') {
                  setDescription(project.summary || '')
                  setIsEditingDesc(false)
                }
              }}
              autoFocus
              onClick={(e) => e.stopPropagation()}
            />
          ) : (
            <span
              className={`description-text ${isDefaultDesc ? 'placeholder' : ''}`}
              onClick={!readOnly ? (e) => {
                e.stopPropagation()
                setIsEditingDesc(true)
              } : undefined}
              title={!readOnly ? "Click to edit description" : undefined}
            >
              {expanded ? (project.description || displayDescription) : displayDescription}
            </span>
          )}
        </div>
      )}

      {/* Install bar (package mode only, not for dependencies) */}
      {showInstallBar && availableProjects.length > 0 && (
        <div className="package-install-bar" onClick={(e) => e.stopPropagation()}>
          <ProjectSelector
            availableProjects={availableProjects}
            selectedProjectId={selectedProjectId}
            onSelect={setSelectedProjectId}
          />
          {versions.length > 0 && (
            <VersionSelector
              versions={versions}
              selectedVersion={selectedVersion}
              onVersionChange={(v) => {
                userHasSelectedVersion.current = true
                setSelectedVersion(v)
              }}
              latestVersion={versions[0]}  // First version after sorting is always latest
            />
          )}
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
      )}

      {/* Expanded content */}
      {expanded && (
        <div className="project-card-content">
          {/* Package metadata - for dependencies use local data, for packages fetch from registry */}
          {showMetadata && (
            <MetadataBar
              // For dependencies (preset=dependencyExpanded), use local data from project
              // For packages (packageExplorer), use remote packageDetails
              downloads={preset === 'dependencyExpanded' ? undefined : packageDetails?.downloads}
              versionCount={preset === 'dependencyExpanded' ? undefined : packageDetails?.versionCount}
              license={preset === 'dependencyExpanded' ? project.license : packageDetails?.license}
              homepage={preset === 'dependencyExpanded' ? project.homepage : packageDetails?.homepage}
              isLoading={preset !== 'dependencyExpanded' && detailsLoading}
            />
          )}

          {/* Error state for metadata (non-blocking, just informational) */}
          {/* Skip for dependencies since we don't fetch remotely */}
          {readOnly && preset !== 'dependencyExpanded' && detailsError && !detailsLoading && (
            <div className="package-error">
              <span>Failed to load package details: {detailsError}</span>
            </div>
          )}

          {/* Import and Usage examples - available immediately using project data */}
          {/* If usageContent (from usage.ato) is available, show that instead of generated example */}
          {showUsageExamples && (
            <UsageCard
              importCode={generateImportStatement(project.id, project.name)}
              usageCode={project.usageContent || generateUsageExample(project.name)}
              onOpenUsage={() => onOpenSource?.(project.id, project.usageContent ? 'usage.ato' : `${project.name}.ato`)}
            />
          )}

          {/* Module Explorer - only show if we have a valid filesystem path */}
          {/* For local projects: always show. For packages/deps: show if path differs from identifier (was resolved) */}
          {showModuleExplorer && (!readOnly || project.root !== project.id) && (
            <ProjectExplorerCard
              builds={builds}
              projectRoot={packagePath}
              defaultExpanded={false}
              isLoading={readOnly && !localBuilds?.length && detailsLoading}
            />
          )}

          {/* Builds */}
          <BuildsCard
            builds={builds}
            projectId={project.id}
            selection={selection}
            onSelect={onSelect}
            onBuild={onBuild}
            onCancelBuild={onCancelBuild}
            onStageFilter={onStageFilter}
            onUpdateBuild={onUpdateBuild}
            onDeleteBuild={onDeleteBuild}
            onOpenSource={onOpenSource}
            onOpenKiCad={onOpenKiCad}
            onOpenLayout={onOpenLayout}
            onOpen3D={onOpen3D}
            onAddBuild={onAddBuild}
            availableModules={availableModules}
            readOnly={readOnly}
            defaultExpanded={false}
          />

          {/* File Explorer */}
          {showFileExplorer && (
            <FileExplorer
              files={projectFiles}
              onFileClick={onFileClick ? (path) => onFileClick(project.id, path) : undefined}
            />
          )}

          {/* Dependencies */}
          <DependencyCard
            dependencies={dependencies}
            projectId={project.id}
            onVersionChange={onDependencyVersionChange}
            onRemove={onRemoveDependency}
            readOnly={readOnly}
            onProjectExpand={onProjectExpand}
            projectFilesByRoot={projectFilesByRoot}
            projectBuildsByRoot={projectBuildsByRoot}
            updatingDependencyIds={updatingDependencyIds}
            onFileClick={onFileClick}
          />
        </div>
      )}
    </div>
  )
})
