/**
 * ProjectNode component - displays a local project in the sidebar.
 * Includes editable name/description, build targets, files, and dependencies.
 */
import { useState, useEffect, memo } from 'react'
import {
  ChevronDown, ChevronRight, Play, Layers,
  AlertCircle, AlertTriangle, Square
} from 'lucide-react'
import { getLastBuildStatusIcon, formatRelativeTime } from './BuildNode'
import { BuildsCard } from './BuildsCard'
import { FileExplorer, type FileTreeNode } from './FileExplorer'
import { DependencyCard, type ProjectDependency } from './DependencyCard'
import type {
  Selection,
  BuildTarget,
  Project,
  ModuleDefinition,
  SelectedPackage
} from './projectsTypes'
import './ProjectNode.css'

// ProjectNode Props
interface ProjectNodeProps {
  project: Project
  selection: Selection
  onSelect: (selection: Selection) => void
  onBuild: (level: 'project' | 'build' | 'symbol', id: string, label: string) => void
  onCancelBuild?: (buildId: string) => void
  onStageFilter?: (stageName: string, buildId?: string, projectId?: string) => void
  onOpenPackageDetail?: (pkg: SelectedPackage) => void
  isExpanded: boolean
  onExpandChange: (projectId: string, expanded: boolean) => void
  onUpdateProject?: (projectId: string, updates: Partial<Project>) => void
  onAddBuild?: (projectId: string) => void
  onUpdateBuild?: (projectId: string, buildId: string, updates: Partial<BuildTarget>) => void
  onDeleteBuild?: (projectId: string, buildId: string) => void
  onProjectExpand?: (projectRoot: string) => void
  onOpenSource?: (projectId: string, entry: string) => void
  onOpenKiCad?: (projectId: string, buildId: string) => void
  onOpenLayout?: (projectId: string, buildId: string) => void
  onOpen3D?: (projectId: string, buildId: string) => void
  onFileClick?: (projectId: string, filePath: string) => void
  onDependencyVersionChange?: (projectId: string, identifier: string, newVersion: string) => void
  onRemoveDependency?: (projectId: string, identifier: string) => void
  availableModules?: ModuleDefinition[]
  projectFiles?: FileTreeNode[]
  projectDependencies?: ProjectDependency[]
}

// Project card (for local projects - styled like package cards)
// Memoized to prevent unnecessary re-renders in lists
export const ProjectNode = memo(function ProjectNode({
  project,
  selection,
  onSelect,
  onBuild,
  onCancelBuild,
  onStageFilter,
  onOpenPackageDetail: _onOpenPackageDetail,
  isExpanded,
  onExpandChange,
  onUpdateProject,
  onAddBuild,
  onUpdateBuild,
  onDeleteBuild,
  onProjectExpand,
  onOpenSource,
  onOpenKiCad,
  onOpenLayout,
  onOpen3D,
  onFileClick,
  onDependencyVersionChange,
  onRemoveDependency,
  availableModules = [],
  projectFiles = [],
  projectDependencies = []
}: ProjectNodeProps) {
  const expanded = isExpanded
  const [isEditingName, setIsEditingName] = useState(false)
  const [isEditingDesc, setIsEditingDesc] = useState(false)
  const [projectName, setProjectName] = useState(project.name)
  const [description, setDescription] = useState(project.summary || '')
  const isSelected = selection.type === 'project' && selection.projectId === project.id

  const totalErrors = project.builds.reduce((sum, b) => sum + (b.errors || 0), 0)
  const totalWarnings = project.builds.reduce((sum, b) => sum + (b.warnings || 0), 0)
  const isBuilding = project.builds.some(b => b.status === 'building')

  // Get the maximum elapsed time from all building builds
  const buildingBuilds = project.builds.filter(b => b.status === 'building')
  const maxElapsedFromBuilds = buildingBuilds.length > 0
    ? Math.max(...buildingBuilds.map(b => b.elapsedSeconds || 0))
    : 0

  // Live timer for building state
  const [displayElapsed, setDisplayElapsed] = useState(maxElapsedFromBuilds)

  useEffect(() => {
    if (!isBuilding) {
      setDisplayElapsed(0)
      return
    }

    // Initialize with current elapsed time from builds
    setDisplayElapsed(maxElapsedFromBuilds)

    // Update every second
    const interval = setInterval(() => {
      setDisplayElapsed(prev => prev + 1)
    }, 1000)

    return () => clearInterval(interval)
  }, [isBuilding, maxElapsedFromBuilds])

  // Format elapsed time as mm:ss or hh:mm:ss
  const formatBuildTime = (seconds: number): string => {
    const hrs = Math.floor(seconds / 3600)
    const mins = Math.floor((seconds % 3600) / 60)
    const secs = Math.floor(seconds % 60)
    if (hrs > 0) {
      return `${hrs}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
    }
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const defaultDescription = "A new atopile project!"
  const displayDescription = description || defaultDescription
  const isDefaultDesc = !description

  const handleNameSave = () => {
    setIsEditingName(false)
    if (onUpdateProject) {
      onUpdateProject(project.id, { name: projectName })
    }
    console.log('Saving name:', projectName)
  }

  const handleDescriptionSave = () => {
    setIsEditingDesc(false)
    if (onUpdateProject) {
      onUpdateProject(project.id, { summary: description })
    }
    console.log('Saving description:', description)
  }

  return (
    <div
      className={`project-card ${isSelected ? 'selected' : ''} ${expanded ? 'expanded' : 'collapsed'} ${isBuilding ? 'building' : ''}`}
      onClick={() => {
        const willExpand = !expanded
        onExpandChange(project.id, willExpand)
        onSelect({
          type: 'project',
          projectId: project.id,
          label: project.name
        })
        // Fetch modules when expanding (for entry point picker)
        if (willExpand && onProjectExpand) {
          onProjectExpand(project.root)
        }
      }}
    >
      {/* Row 1: Project name - always visible */}
      <div className="project-card-name-row">
        <span className="tree-expand">
          {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </span>
        <Layers size={18} className="project-icon" />

        {/* Editable project name - only editable when expanded */}
        {isEditingName && expanded ? (
          <input
            type="text"
            className="project-name-input"
            value={projectName}
            onChange={(e) => setProjectName(e.target.value)}
            onBlur={handleNameSave}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleNameSave()
              if (e.key === 'Escape') {
                setProjectName(project.name)
                setIsEditingName(false)
              }
            }}
            autoFocus
            onClick={(e) => e.stopPropagation()}
          />
        ) : (
          <span
            className={`project-card-name ${expanded ? 'editable' : ''}`}
            onClick={expanded ? (e) => {
              e.stopPropagation()
              setIsEditingName(true)
            } : undefined}
            title={expanded ? "Click to edit name" : undefined}
          >
            {projectName}
          </span>
        )}

        {/* Status indicators and build button - right aligned */}
        <div className="project-card-actions-row">
          {/* Indicators wrapper - slides left on hover to make room for play button */}
          <div className="project-indicators">
            {/* Show build time when building */}
            {isBuilding && (
              <span className="build-time-indicator" title="Build time">
                <span className="build-time">{formatBuildTime(displayElapsed)}</span>
              </span>
            )}
            {/* Show errors/warnings/last build when not building (stop button handles building state) */}
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
                    {project.lastBuildStatus && getLastBuildStatusIcon(project.lastBuildStatus, 10)}
                    <span className="last-build-time">{formatRelativeTime(project.lastBuildTimestamp)}</span>
                  </span>
                )}
              </>
            )}
          </div>

          {/* Play button or Stop button depending on build state */}
          {isBuilding ? (
            <button
              className="project-build-btn-icon stop"
              onClick={(e) => {
                e.stopPropagation()
                // Cancel all running builds in this project
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
              className="project-build-btn-icon"
              onClick={(e) => {
                e.stopPropagation()
                onBuild('project', project.id, project.name)
              }}
              title={`Build all targets in ${project.name}`}
            >
              <Play size={14} fill="currentColor" />
            </button>
          )}
        </div>
      </div>

      {/* Expanded content */}
      {expanded && (
        <>
          {/* Row 2: Editable description */}
          <div className="project-card-description">
            {isEditingDesc ? (
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
                onClick={(e) => {
                  e.stopPropagation()
                  setIsEditingDesc(true)
                }}
                title="Click to edit description"
              >
                {displayDescription}
              </span>
            )}
          </div>

          {/* Build targets */}
          <BuildsCard
            builds={project.builds}
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
          />

          {/* File Explorer */}
          <FileExplorer
            files={projectFiles}
            onFileClick={onFileClick ? (path) => onFileClick(project.id, path) : undefined}
          />

          {/* Dependencies */}
          <DependencyCard
            dependencies={projectDependencies}
            projectId={project.id}
            onVersionChange={onDependencyVersionChange}
            onRemove={onRemoveDependency}
          />
        </>
      )}
    </div>
  )
})
