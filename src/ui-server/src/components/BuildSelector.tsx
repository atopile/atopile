import React, { useState, useRef, useEffect } from 'react'
import { 
  ChevronDown, ChevronRight, Search, Layers, Package,
  Box, Zap, Check, X, AlertTriangle, AlertCircle
} from 'lucide-react'

// Selection type - exported for use across components
export type Selection = {
  type: 'none' | 'project' | 'build' | 'symbol'
  projectId?: string
  buildId?: string
  symbolPath?: string
  label?: string
}

// Symbol in a build
export type BuildSymbol = {
  name: string
  type: 'module' | 'interface' | 'component' | 'parameter'
  path: string
  children?: BuildSymbol[]
  hasErrors?: boolean
  hasWarnings?: boolean
}

// Build target
export type BuildTarget = {
  id: string
  name: string
  entry: string
  status: 'idle' | 'building' | 'success' | 'error' | 'warning'
  errors?: number
  warnings?: number
  duration?: number
  symbols?: BuildSymbol[]
}

// Project
export type Project = {
  id: string
  name: string
  type: 'project' | 'package'
  path: string
  version?: string
  latestVersion?: string
  installed?: boolean
  builds: BuildTarget[]
  description?: string
  summary?: string
}

interface BuildSelectorProps {
  selection: Selection
  onSelectionChange: (selection: Selection) => void
  projects: Project[]
  placeholder?: string
  showSymbols?: boolean  // Whether to allow selecting symbols (deep nesting)
  compact?: boolean      // Compact mode for smaller spaces
}

// Get icon for symbol type
function getSymbolIcon(type: string, size: number = 12) {
  switch (type) {
    case 'module':
      return <Box size={size} className="symbol-icon module" />
    case 'interface':
      return <Zap size={size} className="symbol-icon interface" />
    case 'component':
      return <Package size={size} className="symbol-icon component" />
    default:
      return <Box size={size} className="symbol-icon" />
  }
}

// Get status indicator
function getStatusIcon(status: string, size: number = 10) {
  switch (status) {
    case 'error':
      return <AlertCircle size={size} className="status-icon error" />
    case 'warning':
      return <AlertTriangle size={size} className="status-icon warning" />
    case 'success':
      return <Check size={size} className="status-icon success" />
    default:
      return null
  }
}

// Format selection label
function getSelectionLabel(selection: Selection, projects: Project[]): string {
  if (selection.type === 'none') {
    return 'All'
  }
  
  const project = projects.find(p => p.id === selection.projectId)
  if (!project) return selection.label || 'Unknown'
  
  if (selection.type === 'project') {
    return project.name
  }
  
  const build = project.builds.find(b => b.id === selection.buildId)
  if (!build) return project.name
  
  if (selection.type === 'build') {
    return `${project.name} › ${build.name}`
  }
  
  // Symbol level
  if (selection.symbolPath) {
    const symbolName = selection.symbolPath.split('.').pop() || selection.symbolPath
    return `${project.name} › ${build.name} › ${symbolName}`
  }
  
  return selection.label || 'Unknown'
}

export function BuildSelector({
  selection,
  onSelectionChange,
  projects,
  placeholder: _placeholder = 'Select build...',
  showSymbols = true,
  compact = false
}: BuildSelectorProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [expandedProjects, setExpandedProjects] = useState<Set<string>>(new Set())
  const [expandedBuilds, setExpandedBuilds] = useState<Set<string>>(new Set())
  const dropdownRef = useRef<HTMLDivElement>(null)
  
  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])
  
  const toggleProject = (projectId: string, e: React.MouseEvent) => {
    e.stopPropagation()
    setExpandedProjects(prev => {
      const next = new Set(prev)
      if (next.has(projectId)) next.delete(projectId)
      else next.add(projectId)
      return next
    })
  }
  
  const toggleBuild = (buildKey: string, e: React.MouseEvent) => {
    e.stopPropagation()
    setExpandedBuilds(prev => {
      const next = new Set(prev)
      if (next.has(buildKey)) next.delete(buildKey)
      else next.add(buildKey)
      return next
    })
  }
  
  const selectAll = () => {
    onSelectionChange({ type: 'none' })
    setIsOpen(false)
  }
  
  const selectProject = (project: Project) => {
    onSelectionChange({
      type: 'project',
      projectId: project.id,
      label: project.name
    })
    setIsOpen(false)
  }
  
  const selectBuild = (project: Project, build: BuildTarget) => {
    onSelectionChange({
      type: 'build',
      projectId: project.id,
      buildId: build.id,
      label: `${project.name} › ${build.name}`
    })
    setIsOpen(false)
  }
  
  const selectSymbol = (project: Project, build: BuildTarget, symbol: BuildSymbol) => {
    onSelectionChange({
      type: 'symbol',
      projectId: project.id,
      buildId: build.id,
      symbolPath: symbol.path,
      label: `${project.name} › ${build.name} › ${symbol.name}`
    })
    setIsOpen(false)
  }
  
  // Filter projects/builds based on search
  const filteredProjects = projects.filter(project => {
    if (!searchQuery) return true
    const query = searchQuery.toLowerCase()
    
    // Match project name
    if (project.name.toLowerCase().includes(query)) return true
    
    // Match build names
    if (project.builds.some(b => b.name.toLowerCase().includes(query))) return true
    
    // Match symbol names if enabled
    if (showSymbols) {
      for (const build of project.builds) {
        if (build.symbols?.some(s => s.name.toLowerCase().includes(query))) {
          return true
        }
      }
    }
    
    return false
  })
  
  // Only show user projects (not packages) for filtering - packages are dependencies
  const userProjects = filteredProjects.filter(p => p.type === 'project')
  
  const label = getSelectionLabel(selection, projects)
  
  // Render symbol tree recursively
  const renderSymbol = (
    project: Project, 
    build: BuildTarget, 
    symbol: BuildSymbol, 
    depth: number = 0
  ): React.ReactElement => {
    const hasChildren = symbol.children && symbol.children.length > 0
    const symbolKey = `${project.id}-${build.id}-${symbol.path}`
    const isExpanded = expandedBuilds.has(symbolKey)
    
    return (
      <div key={symbol.path} className="selector-symbol">
        <div 
          className={`selector-symbol-row ${selection.symbolPath === symbol.path ? 'selected' : ''}`}
          style={{ paddingLeft: `${16 + depth * 12}px` }}
          onClick={() => selectSymbol(project, build, symbol)}
        >
          {hasChildren ? (
            <button 
              className="selector-expand"
              onClick={(e) => toggleBuild(symbolKey, e)}
            >
              {isExpanded ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
            </button>
          ) : (
            <span className="selector-expand-placeholder" />
          )}
          {getSymbolIcon(symbol.type)}
          <span className="selector-symbol-name">{symbol.name}</span>
          {symbol.hasErrors && <AlertCircle size={10} className="status-icon error" />}
          {symbol.hasWarnings && !symbol.hasErrors && <AlertTriangle size={10} className="status-icon warning" />}
        </div>
        {hasChildren && isExpanded && (
          <div className="selector-symbol-children">
            {symbol.children!.map(child => renderSymbol(project, build, child, depth + 1))}
          </div>
        )}
      </div>
    )
  }
  
  return (
    <div className={`build-selector ${compact ? 'compact' : ''}`} ref={dropdownRef}>
      <button 
        className={`selector-trigger ${isOpen ? 'open' : ''} ${selection.type !== 'none' ? 'has-selection' : ''}`}
        onClick={() => setIsOpen(!isOpen)}
      >
        <span className="selector-label">{label}</span>
        <ChevronDown size={12} className={`selector-chevron ${isOpen ? 'rotated' : ''}`} />
      </button>
      
      {isOpen && (
        <div className="selector-dropdown">
          <div className="selector-search">
            <Search size={12} />
            <input
              type="text"
              placeholder="Search..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              autoFocus
            />
            {searchQuery && (
              <button className="selector-clear" onClick={() => setSearchQuery('')}>
                <X size={10} />
              </button>
            )}
          </div>
          
          <div className="selector-list">
            {/* All option */}
            <div 
              className={`selector-item all ${selection.type === 'none' ? 'selected' : ''}`}
              onClick={selectAll}
            >
              <span className="selector-item-label">All Projects</span>
              {selection.type === 'none' && <Check size={12} className="selector-check" />}
            </div>
            
            <div className="selector-divider" />
            
            {/* Projects */}
            {userProjects.map(project => {
              const isProjectExpanded = expandedProjects.has(project.id)
              const isProjectSelected = selection.projectId === project.id && selection.type === 'project'
              const projectErrors = project.builds.reduce((sum, b) => sum + (b.errors || 0), 0)
              const projectWarnings = project.builds.reduce((sum, b) => sum + (b.warnings || 0), 0)
              
              return (
                <div key={project.id} className="selector-project">
                  <div 
                    className={`selector-project-row ${isProjectSelected ? 'selected' : ''}`}
                    onClick={() => selectProject(project)}
                  >
                    <button 
                      className="selector-expand"
                      onClick={(e) => toggleProject(project.id, e)}
                    >
                      {isProjectExpanded ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
                    </button>
                    <Layers size={12} className="selector-project-icon" />
                    <span className="selector-project-name">{project.name}</span>
                    {projectErrors > 0 && (
                      <span className="selector-count error">{projectErrors}</span>
                    )}
                    {projectWarnings > 0 && (
                      <span className="selector-count warning">{projectWarnings}</span>
                    )}
                    {isProjectSelected && <Check size={12} className="selector-check" />}
                  </div>
                  
                  {isProjectExpanded && (
                    <div className="selector-builds">
                      {project.builds.map(build => {
                        const buildKey = `${project.id}-${build.id}`
                        const isBuildExpanded = expandedBuilds.has(buildKey) && showSymbols
                        const isBuildSelected = selection.projectId === project.id && 
                                               selection.buildId === build.id && 
                                               selection.type === 'build'
                        
                        return (
                          <div key={build.id} className="selector-build">
                            <div 
                              className={`selector-build-row ${isBuildSelected ? 'selected' : ''}`}
                              onClick={() => selectBuild(project, build)}
                            >
                              {showSymbols && build.symbols && build.symbols.length > 0 ? (
                                <button 
                                  className="selector-expand"
                                  onClick={(e) => toggleBuild(buildKey, e)}
                                >
                                  {isBuildExpanded ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
                                </button>
                              ) : (
                                <span className="selector-expand-placeholder" />
                              )}
                              {getStatusIcon(build.status)}
                              <span className="selector-build-name">{build.name}</span>
                              <span className="selector-build-entry">{build.entry.split(':')[1]}</span>
                              {build.errors && build.errors > 0 && (
                                <span className="selector-count error">{build.errors}</span>
                              )}
                              {build.warnings && build.warnings > 0 && (
                                <span className="selector-count warning">{build.warnings}</span>
                              )}
                              {isBuildSelected && <Check size={12} className="selector-check" />}
                            </div>
                            
                            {/* Symbols */}
                            {showSymbols && isBuildExpanded && build.symbols && (
                              <div className="selector-symbols">
                                {build.symbols.map(symbol => renderSymbol(project, build, symbol))}
                              </div>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  )}
                </div>
              )
            })}
            
            {userProjects.length === 0 && (
              <div className="selector-empty">No projects found</div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
