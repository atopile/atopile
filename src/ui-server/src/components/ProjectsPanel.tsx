import { useState } from 'react'
import { Search, Plus } from 'lucide-react'
import { type ProjectDependency } from './DependencyCard'
import { type FileTreeNode } from './FileExplorer'
import { ProjectCard } from './ProjectCard'
import type {
  Selection,
  BuildTarget,
  Project,
  ModuleDefinition,
  AvailableProject,
  SelectedPackage
} from './projectsTypes'

// Types are now imported from ./projectsTypes

// Types AvailableProject, SelectedPackage imported from ./projectsTypes
// Helper functions getTypeIcon, getStatusIcon imported from components

interface ProjectsPanelProps {
  selection: Selection
  onSelect: (selection: Selection) => void
  onBuild: (level: 'project' | 'build' | 'symbol', id: string, label: string) => void
  onCancelBuild?: (buildId: string) => void  // Cancel a running build
  onStageFilter?: (stageName: string, buildId?: string, projectId?: string) => void
  onOpenPackageDetail?: (pkg: SelectedPackage) => void
  onPackageInstall?: (packageId: string, targetProjectRoot: string, version?: string) => void
  onCreateProject?: (parentDirectory?: string, name?: string) => void  // Creates a new project
  onProjectExpand?: (projectRoot: string) => void  // Called when a project is expanded (for module fetching)
  onOpenSource?: (projectId: string, entry: string) => void  // Open source file (ato button)
  onOpenKiCad?: (projectId: string, buildId: string) => void  // Open in KiCad
  onOpenLayout?: (projectId: string, buildId: string) => void  // Open layout preview
  onOpen3D?: (projectId: string, buildId: string) => void  // Open 3D viewer
  onFileClick?: (projectId: string, filePath: string) => void  // Open a file in the editor
  onDependencyVersionChange?: (projectId: string, identifier: string, newVersion: string) => void  // Change dependency version
  onRemoveDependency?: (projectId: string, identifier: string) => void  // Remove a dependency
  onAddBuild?: (projectId: string) => void  // Add a new build target
  onUpdateBuild?: (projectId: string, buildId: string, updates: Partial<BuildTarget>) => void  // Update build target (rename/entry)
  onDeleteBuild?: (projectId: string, buildId: string) => void  // Delete a build target
  filterType?: 'all' | 'projects' | 'packages'
  projects?: Project[]  // Optional - defaults to empty list
  projectModules?: Record<string, ModuleDefinition[]>  // Modules for each project root
  projectFiles?: Record<string, FileTreeNode[]>  // File tree for each project root
  projectDependencies?: Record<string, ProjectDependency[]>  // Dependencies for each project root
  installingPackageIds?: string[]  // IDs of packages currently being installed
  updatingDependencyIds?: string[]  // IDs of dependencies currently being updated (format: projectRoot:dependencyId)
}

export function ProjectsPanel({ selection, onSelect, onBuild, onCancelBuild, onStageFilter, onOpenPackageDetail: _onOpenPackageDetail, onPackageInstall, onCreateProject, onProjectExpand, onOpenSource, onOpenKiCad, onOpenLayout, onOpen3D, onFileClick, onDependencyVersionChange, onRemoveDependency, onAddBuild, onUpdateBuild, onDeleteBuild, filterType = 'all', projects: externalProjects, projectModules = {}, projectFiles = {}, projectDependencies = {}, installingPackageIds = [], updatingDependencyIds = [] }: ProjectsPanelProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [expandedProjectId, setExpandedProjectId] = useState<string | null>(null)
  const projects = externalProjects && externalProjects.length > 0 ? externalProjects : []
  
  // Handler to add a new project
  const handleAddProject = () => {
    // If callback is provided, use it (real implementation)
    if (onCreateProject) {
      onCreateProject()
      return
    }

    console.warn('Create project handler not provided')
  }
  
  // Handler to update a project
  const handleUpdateProject = (projectId: string, updates: Partial<Project>) => {
    console.warn('Update project handler not provided', projectId, updates)
  }
  
  // Handler to add a new build to a project
  const handleAddBuild = (projectId: string) => {
    // If external callback is provided, use it
    if (onAddBuild) {
      onAddBuild(projectId)
      return
    }

    console.warn('Add build handler not provided', projectId)
  }

  // Handler to update a build
  const handleUpdateBuild = (projectId: string, buildId: string, updates: Partial<BuildTarget>) => {
    // If external callback is provided, use it
    if (onUpdateBuild) {
      onUpdateBuild(projectId, buildId, updates)
      return
    }

    console.warn('Update build handler not provided', projectId, buildId, updates)
  }

  // Handler to delete a build
  const handleDeleteBuild = (projectId: string, buildId: string) => {
    // If external callback is provided, use it
    if (onDeleteBuild) {
      onDeleteBuild(projectId, buildId)
      return
    }

    console.warn('Delete build handler not provided', projectId, buildId)

    // Clear selection if the deleted build was selected
    if (selection.type === 'build' && selection.buildId === `${projectId}:${buildId}`) {
      onSelect({ type: 'none' })
    }
  }
  
  // Create available projects list for install dropdown (only actual projects, not packages)
  const availableProjects: AvailableProject[] = projects
    .filter(p => p.type === 'project')
    .map((p, idx) => ({
      id: p.id,
      name: p.name,
      path: p.root,
      isActive: idx === 0  // First project is active by default
    }))
  
  // Handle install action
  const handleInstall = (packageId: string, targetProjectId: string, version?: string) => {
    console.log(`Installing ${packageId} to ${targetProjectId}${version ? ` @ ${version}` : ''}`)
    if (onPackageInstall) {
      // Find the project root for the target project
      const targetProject = projects.find(p => p.id === targetProjectId)
      const projectRoot = targetProject?.root || targetProjectId
      onPackageInstall(packageId, projectRoot, version)
    } else {
      // Fallback for development/testing
      alert(`Installing ${packageId} to ${targetProjectId}`)
    }
  }
  
  // Filter projects based on external filterType prop
  const filteredProjects = projects.filter(project => {
    // Filter by type
    if (filterType === 'projects' && project.type !== 'project') return false
    if (filterType === 'packages' && project.type !== 'package') return false
    
    
    // Filter by search - include name, description, summary, and keywords
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      const searchableText = [
        project.name,
        project.id,
        project.publisher || '',
        project.description || '',
        project.summary || '',
        ...(project.keywords || [])
      ].join(' ').toLowerCase()
      
      return searchableText.includes(query)
    }
    
    return true
  })

  const placeholder = filterType === 'packages' 
    ? 'Search packages (e.g. "regulator", "sensor")...' 
    : 'Search projects...'

  return (
    <div className="projects-panel">
      {/* Search */}
      <div className="projects-toolbar">
        <div className="search-box">
          <Search size={12} />
          <input
            type="text"
            placeholder={placeholder}
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value)
              // Clear selection and collapse expanded project when user starts typing
              if (e.target.value) {
                if (selection.type !== 'none') {
                  onSelect({ type: 'none' })
                }
                // Collapse any expanded project so search results show all matches
                if (expandedProjectId !== null) {
                  setExpandedProjectId(null)
                }
              }
            }}
          />
        </div>
        
        {/* Add new project button (only for projects) */}
        {filterType === 'projects' && (
          <button 
            className="add-project-btn"
            onClick={handleAddProject}
            title="Create new project"
          >
            <Plus size={14} />
          </button>
        )}
        
      </div>
      
      {/* Project/Package list */}
      <div className="projects-tree">
        {filteredProjects
          .filter(project => {
            // For projects panel: hide other projects when one is expanded
            if (filterType === 'projects' && expandedProjectId !== null) {
              return project.id === expandedProjectId
            }
            return true
          })
          .map(project => {
            const isPackage = project.type === 'package'
            return (
              <ProjectCard
                key={project.id}
                project={project}
                preset={isPackage ? 'packageExplorer' : 'localProject'}
                selection={selection}
                onSelect={onSelect}
                onBuild={onBuild}
                onCancelBuild={onCancelBuild}
                onStageFilter={onStageFilter}
                isExpanded={expandedProjectId === project.id}
                onExpandChange={(projectId, expanded) => {
                  setExpandedProjectId(expanded ? projectId : null)
                }}
                // Edit mode props (for local projects)
                onUpdateProject={handleUpdateProject}
                onAddBuild={handleAddBuild}
                onUpdateBuild={handleUpdateBuild}
                onDeleteBuild={handleDeleteBuild}
                onProjectExpand={onProjectExpand}
                onDependencyVersionChange={onDependencyVersionChange}
                onRemoveDependency={onRemoveDependency}
                // Common props
                onOpenSource={onOpenSource}
                onOpenKiCad={onOpenKiCad}
                onOpenLayout={onOpenLayout}
                onOpen3D={onOpen3D}
                onFileClick={onFileClick}
                // Data props
                availableModules={projectModules[project.root] || []}
                projectFiles={projectFiles[project.root] || []}
                projectFilesByRoot={projectFiles}
                projectDependencies={projectDependencies[project.root] || []}
                updatingDependencyIds={updatingDependencyIds}
                // Package mode props
                availableProjects={availableProjects}
                onInstall={handleInstall}
                isInstalling={installingPackageIds.includes(project.id)}
              />
            )
          })}
        
        {filteredProjects.length === 0 && (
          <div className="empty-state">
            <span>No {filterType === 'packages' ? 'packages' : 'projects'} found</span>
            {searchQuery && filterType === 'packages' && (
              <span className="empty-hint">Try searching for "sensor", "regulator", or "mcu"</span>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
