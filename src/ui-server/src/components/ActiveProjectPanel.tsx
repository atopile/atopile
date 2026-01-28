import { useEffect, useMemo, useState, useRef, useCallback } from 'react'
import { FolderOpen, Play, Layers, Cuboid, Layout, Plus, ChevronDown, Check, X, Package, CheckCircle2, XCircle, AlertCircle, AlertTriangle, Target, ScrollText } from 'lucide-react'
import type { Project, BuildTarget } from '../types/build'
import type { QueuedBuild } from '../types/build'
import { useStore } from '../store'
import { sendAction } from '../api/websocket'
import './ActiveProjectPanel.css'

interface NewProjectData {
  name?: string
  license?: string
  description?: string
  parentDirectory?: string
}

interface ActiveProjectPanelProps {
  projects: Project[]
  selectedProjectRoot: string | null
  selectedTargetName: string | null
  projectModules?: ModuleDefinition[]
  onSelectProject: (projectRoot: string | null) => void
  onSelectTarget: (projectRoot: string, targetName: string) => void
  onBuildTarget: (projectRoot: string, targetName: string) => void
  onBuildAllTargets: (projectRoot: string, projectName: string) => void
  onOpenKiCad: (projectRoot: string, targetName: string) => void
  onOpen3D: (projectRoot: string, targetName: string) => void
  onOpenLayout: (projectRoot: string, targetName: string) => void
  onCreateProject?: (data?: NewProjectData) => Promise<void>
  onCreateTarget?: (projectRoot: string, data: NewTargetData) => Promise<void>
  onGenerateManufacturingData?: (projectRoot: string, targetName: string) => void
  queuedBuilds?: QueuedBuild[]
  onCancelBuild?: (buildId: string) => void
}

// Helper to format path for display - shows last 2 segments
function formatPath(path: string): string {
  if (!path) return ''
  const parts = path.split('/')
  // Show last 2 segments (e.g., "examples/equations")
  return parts.slice(-2).join('/')
}

function formatDuration(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return ''
  if (seconds < 1) {
    return `${seconds.toFixed(2)}s`
  }
  if (seconds < 10) {
    return `${seconds.toFixed(1)}s`
  }
  const total = Math.floor(seconds)
  if (total < 60) {
    return `${total}s`
  }
  const mins = Math.floor(total / 60)
  const secs = total % 60
  if (mins < 60) {
    return `${mins}m ${secs}s`
  }
  const hours = Math.floor(mins / 60)
  const remainMins = mins % 60
  return `${hours}h ${remainMins}m`
}

function formatRelativeSeconds(epochSeconds: number): string {
  if (!Number.isFinite(epochSeconds) || epochSeconds <= 0) return ''
  const diffMs = Date.now() - epochSeconds * 1000
  const diffSecs = Math.floor(diffMs / 1000)
  const diffMins = Math.floor(diffSecs / 60)
  const diffHours = Math.floor(diffMins / 60)
  const diffDays = Math.floor(diffHours / 24)

  if (diffSecs < 60) return 'just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays === 1) return 'yesterday'
  if (diffDays < 7) return `${diffDays}d ago`
  return new Date(epochSeconds * 1000).toLocaleDateString()
}

function getBuildCounter(buildId?: string): string | null {
  if (!buildId) return null
  const match = buildId.match(/^build-(\d+)-/)
  if (match) return `#${match[1]}`
  return `#${buildId}`
}

// Simple fuzzy match for project search
function fuzzyMatch(text: string, query: string): boolean {
  const lowerText = text.toLowerCase()
  const lowerQuery = query.toLowerCase()

  // Direct substring match
  if (lowerText.includes(lowerQuery)) return true

  // Fuzzy: check if all query chars appear in order
  let queryIdx = 0
  for (const char of lowerText) {
    if (char === lowerQuery[queryIdx]) {
      queryIdx++
      if (queryIdx === lowerQuery.length) return true
    }
  }
  return false
}

// ProjectSelector component - true combobox with inline search
function ProjectSelector({
  projects,
  activeProject,
  onSelectProject,
  onCreateProject,
}: {
  projects: Project[]
  activeProject: Project | null
  onSelectProject: (projectRoot: string | null) => void
  onCreateProject?: () => void
}) {
  const [isOpen, setIsOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [highlightedIndex, setHighlightedIndex] = useState(0)
  const comboboxRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Filter projects by search with fuzzy matching
  const filteredProjects = useMemo(() => {
    if (!searchQuery.trim()) return projects
    return projects.filter(
      (p) =>
        fuzzyMatch(p.name, searchQuery) ||
        fuzzyMatch(p.root, searchQuery)
    )
  }, [projects, searchQuery])

  // Reset highlight when filtered projects change
  useEffect(() => {
    setHighlightedIndex(0)
  }, [filteredProjects.length])

  // Close on outside click
  useEffect(() => {
    if (!isOpen) return
    const handleClickOutside = (e: MouseEvent) => {
      if (comboboxRef.current && !comboboxRef.current.contains(e.target as Node)) {
        setIsOpen(false)
        setSearchQuery('')
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [isOpen])

  // Keyboard navigation
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Escape') {
        setIsOpen(false)
        setSearchQuery('')
        inputRef.current?.blur()
      } else if (e.key === 'ArrowDown') {
        e.preventDefault()
        if (!isOpen) {
          setIsOpen(true)
        } else {
          setHighlightedIndex((prev) =>
            prev < filteredProjects.length - 1 ? prev + 1 : prev
          )
        }
      } else if (e.key === 'ArrowUp') {
        e.preventDefault()
        setHighlightedIndex((prev) => (prev > 0 ? prev - 1 : 0))
      } else if (e.key === 'Enter') {
        e.preventDefault()
        if (filteredProjects[highlightedIndex]) {
          onSelectProject(filteredProjects[highlightedIndex].root)
          setIsOpen(false)
          setSearchQuery('')
          inputRef.current?.blur()
        }
      }
    },
    [filteredProjects, highlightedIndex, isOpen, onSelectProject]
  )

  const handleInputFocus = () => {
    setIsOpen(true)
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.target.value)
    if (!isOpen) setIsOpen(true)
  }

  const selectProject = (project: Project) => {
    onSelectProject(project.root)
    setIsOpen(false)
    setSearchQuery('')
    inputRef.current?.blur()
  }

  // Display value: show search query when typing, otherwise show active project
  const displayValue = isOpen ? searchQuery : (activeProject?.name || '')

  return (
    <div className="project-combobox" ref={comboboxRef}>
      <div className={`combobox-input-wrapper ${isOpen ? 'open' : ''}`}>
        <FolderOpen size={14} className="combobox-icon" />
        <input
          ref={inputRef}
          type="text"
          className="combobox-input"
          placeholder={activeProject ? activeProject.name : 'Select project...'}
          value={displayValue}
          onChange={handleInputChange}
          onFocus={handleInputFocus}
          onKeyDown={handleKeyDown}
          aria-haspopup="listbox"
          aria-expanded={isOpen}
          aria-autocomplete="list"
        />
        <button
          type="button"
          className="combobox-toggle"
          onClick={() => {
            setIsOpen(!isOpen)
            if (!isOpen) inputRef.current?.focus()
          }}
          tabIndex={-1}
        >
          <ChevronDown size={14} className={`chevron ${isOpen ? 'open' : ''}`} />
        </button>
      </div>

      {isOpen && (
        <div className="combobox-dropdown">
          <div className="combobox-list" role="listbox">
            {filteredProjects.length === 0 ? (
              <div className="combobox-empty">No matching projects</div>
            ) : (
              filteredProjects.map((project, index) => {
                const isActive = project.root === activeProject?.root
                const isHighlighted = index === highlightedIndex
                return (
                  <button
                    key={project.root}
                    className={`combobox-option ${isActive ? 'active' : ''} ${isHighlighted ? 'highlighted' : ''}`}
                    onClick={() => selectProject(project)}
                    onMouseEnter={() => setHighlightedIndex(index)}
                    role="option"
                    aria-selected={isActive}
                  >
                    <FolderOpen size={12} className="option-icon" />
                    <span className="combobox-option-name">{project.name}</span>
                    <span className="combobox-option-path" title={project.root}>
                      {project.displayPath || formatPath(project.root)}
                    </span>
                    {isActive && <Check size={12} className="check-icon" />}
                  </button>
                )
              })
            )}
          </div>

          {onCreateProject && (
            <div className="combobox-footer">
              <button
                className="combobox-create-btn"
                onClick={() => {
                  onCreateProject()
                  setIsOpen(false)
                  setSearchQuery('')
                }}
              >
                <Plus size={12} />
                <span>New Project</span>
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// TargetSelector component - combobox for target selection
function TargetSelector({
  targets,
  activeTargetName,
  onSelectTarget,
  onCreateTarget,
  disabled,
}: {
  targets: BuildTarget[]
  activeTargetName: string | null
  onSelectTarget: (targetName: string) => void
  onCreateTarget?: () => void
  disabled?: boolean
}) {
  const [isOpen, setIsOpen] = useState(false)
  const [highlightedIndex, setHighlightedIndex] = useState(0)
  const comboboxRef = useRef<HTMLDivElement>(null)

  const activeTarget = targets.find(t => t.name === activeTargetName) || targets[0] || null

  // Close on outside click
  useEffect(() => {
    if (!isOpen) return
    const handleClickOutside = (e: MouseEvent) => {
      if (comboboxRef.current && !comboboxRef.current.contains(e.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [isOpen])

  // Keyboard navigation
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Escape') {
        setIsOpen(false)
      } else if (e.key === 'ArrowDown') {
        e.preventDefault()
        if (!isOpen) {
          setIsOpen(true)
        } else {
          setHighlightedIndex((prev) =>
            prev < targets.length - 1 ? prev + 1 : prev
          )
        }
      } else if (e.key === 'ArrowUp') {
        e.preventDefault()
        setHighlightedIndex((prev) => (prev > 0 ? prev - 1 : 0))
      } else if (e.key === 'Enter') {
        e.preventDefault()
        if (targets[highlightedIndex]) {
          onSelectTarget(targets[highlightedIndex].name)
          setIsOpen(false)
        }
      }
    },
    [targets, highlightedIndex, isOpen, onSelectTarget]
  )

  const selectTarget = (target: BuildTarget) => {
    onSelectTarget(target.name)
    setIsOpen(false)
  }

  if (targets.length === 0) {
    return (
      <div className="target-selector-empty">
        <span>No builds defined</span>
        {onCreateTarget && (
          <button
            className="create-target-btn"
            onClick={onCreateTarget}
            title="Create new build"
          >
            <Plus size={12} />
          </button>
        )}
      </div>
    )
  }

  return (
    <div className="target-selector-row">
      <div className="target-combobox" ref={comboboxRef}>
        <button
          type="button"
          className={`target-combobox-trigger ${isOpen ? 'open' : ''}`}
          onClick={() => !disabled && setIsOpen(!isOpen)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          aria-haspopup="listbox"
          aria-expanded={isOpen}
        >
          <Target size={12} className="target-icon" />
          <span className="target-trigger-name">{activeTarget?.name || 'Select build'}</span>
          {activeTarget?.entry && (
            <span className="target-trigger-entry">{activeTarget.entry.split(':').pop()}</span>
          )}
          <ChevronDown size={12} className={`chevron ${isOpen ? 'open' : ''}`} />
        </button>

        {isOpen && (
          <div className="target-combobox-dropdown">
            <div className="target-combobox-list" role="listbox">
              {targets.map((target, index) => {
                const isActive = target.name === activeTargetName
                const isHighlighted = index === highlightedIndex
                return (
                  <button
                    key={target.name}
                    className={`target-option ${isActive ? 'active' : ''} ${isHighlighted ? 'highlighted' : ''}`}
                    onClick={() => selectTarget(target)}
                    onMouseEnter={() => setHighlightedIndex(index)}
                    role="option"
                    aria-selected={isActive}
                  >
                    <Target size={12} className="option-icon" />
                    <span className="target-option-name">{target.name}</span>
                    {target.entry && (
                      <span className="target-option-entry">{target.entry.split(':').pop()}</span>
                    )}
                    {isActive && <Check size={12} className="check-icon" />}
                  </button>
                )
              })}
            </div>
          </div>
        )}
      </div>

      {onCreateTarget && (
        <button
          className="create-target-btn"
          onClick={onCreateTarget}
          title="Create new build"
          disabled={disabled}
        >
          <Plus size={12} />
        </button>
      )}
    </div>
  )
}

// Available license options
const LICENSE_OPTIONS = [
  { value: '', label: 'Select license (optional)' },
  { value: 'MIT', label: 'MIT License' },
  { value: 'Apache-2.0', label: 'Apache 2.0' },
  { value: 'GPL-3.0', label: 'GPL 3.0' },
  { value: 'BSD-3-Clause', label: 'BSD 3-Clause' },
  { value: 'Proprietary', label: 'Proprietary' },
]

interface NewTargetData {
  name: string
  entry: string
}

interface ModuleDefinition {
  name: string
  type: string
  file: string
  entry: string
  line?: number
  super_type?: string
}

interface EntryStatus {
  file_exists: boolean
  module_exists: boolean
}

// New Target Form component with autocomplete
function NewTargetForm({
  onSubmit,
  onCancel,
  isCreating,
  error,
  projectName,
  projectRoot,
  modules,
}: {
  onSubmit: (data: NewTargetData) => void
  onCancel: () => void
  isCreating?: boolean
  error?: string | null
  projectName?: string
  projectRoot?: string
  modules?: ModuleDefinition[]
}) {
  const [name, setName] = useState('')
  const [entry, setEntry] = useState('')
  const [entryStatus, setEntryStatus] = useState<EntryStatus | null>(null)
  const [isCheckingEntry, setIsCheckingEntry] = useState(false)
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [highlightedIndex, setHighlightedIndex] = useState(0)
  const nameRef = useRef<HTMLInputElement>(null)
  const entryRef = useRef<HTMLInputElement>(null)
  const suggestionsRef = useRef<HTMLDivElement>(null)

  // Focus name input on mount
  useEffect(() => {
    nameRef.current?.focus()
  }, [])

  // Check entry status when entry changes (debounced)
  useEffect(() => {
    if (!entry || !projectRoot) {
      setEntryStatus(null)
      return
    }

    // Check if entry matches an existing module
    const matchingModule = modules?.find(m => m.entry === entry)
    if (matchingModule) {
      setEntryStatus({ file_exists: true, module_exists: true })
      return
    }

    // Debounce the check
    const timer = setTimeout(async () => {
      setIsCheckingEntry(true)
      try {
        const { sendActionWithResponse } = await import('../api/websocket')
        const response = await sendActionWithResponse('checkEntry', {
          project_root: projectRoot,
          entry,
        })
        const result = response.result as { success?: boolean; file_exists?: boolean; module_exists?: boolean } | undefined
        if (result?.success) {
          setEntryStatus({
            file_exists: Boolean(result.file_exists),
            module_exists: Boolean(result.module_exists),
          })
        }
      } catch (err) {
        setEntryStatus({ file_exists: false, module_exists: false })
      } finally {
        setIsCheckingEntry(false)
      }
    }, 300)

    return () => clearTimeout(timer)
  }, [entry, projectRoot, modules])

  // Filter suggestions based on entry input
  const suggestions = useMemo(() => {
    if (!modules || !entry) return []
    const lowerEntry = entry.toLowerCase()
    return modules
      .filter(m =>
        m.entry.toLowerCase().includes(lowerEntry) ||
        m.name.toLowerCase().includes(lowerEntry)
      )
      .slice(0, 8) // Limit to 8 suggestions
  }, [modules, entry])

  // Reset highlight when suggestions change
  useEffect(() => {
    setHighlightedIndex(0)
  }, [suggestions.length])

  // Close suggestions on outside click
  useEffect(() => {
    if (!showSuggestions) return
    const handleClickOutside = (e: MouseEvent) => {
      if (suggestionsRef.current && !suggestionsRef.current.contains(e.target as Node) &&
          entryRef.current && !entryRef.current.contains(e.target as Node)) {
        setShowSuggestions(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [showSuggestions])

  const handleEntryKeyDown = (e: React.KeyboardEvent) => {
    if (!showSuggestions || suggestions.length === 0) {
      if (e.key === 'Escape') onCancel()
      return
    }

    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setHighlightedIndex(prev => Math.min(prev + 1, suggestions.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setHighlightedIndex(prev => Math.max(prev - 1, 0))
    } else if (e.key === 'Enter' && suggestions[highlightedIndex]) {
      e.preventDefault()
      setEntry(suggestions[highlightedIndex].entry)
      setShowSuggestions(false)
    } else if (e.key === 'Escape') {
      setShowSuggestions(false)
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim() || !entry.trim()) return
    onSubmit({
      name: name.trim(),
      entry: entry.trim(),
    })
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape' && !showSuggestions) {
      onCancel()
    }
  }

  // Entry status message
  const getEntryStatusMessage = () => {
    if (isCheckingEntry) return 'Checking...'
    if (!entryStatus) return 'Format: file.ato:ModuleName'
    if (entryStatus.module_exists) return '✓ Module exists'
    if (entryStatus.file_exists) return '⚠ Module not found in file'
    return '⚠ Entry does not exist'
  }

  const getEntryStatusClass = () => {
    if (!entryStatus || isCheckingEntry) return ''
    if (entryStatus.module_exists) return 'status-exists'
    return 'status-create'
  }

  return (
    <form className="new-target-form" onSubmit={handleSubmit} onKeyDown={handleKeyDown}>
      <div className="form-header">
        <span className="form-title">New Build{projectName ? ` in ${projectName}` : ''}</span>
        <button
          type="button"
          className="form-close-btn"
          onClick={onCancel}
          disabled={isCreating}
        >
          <X size={14} />
        </button>
      </div>

      {error && (
        <div className="form-error">
          <AlertCircle size={14} />
          <span>{error}</span>
        </div>
      )}

      <div className="form-field">
        <label htmlFor="target-name">Name</label>
        <input
          ref={nameRef}
          id="target-name"
          type="text"
          placeholder="e.g., sensor_board"
          value={name}
          onChange={(e) => setName(e.target.value)}
          disabled={isCreating}
          required
        />
      </div>

      <div className="form-field entry-field">
        <label htmlFor="target-entry">Entry Point</label>
        <div className="entry-input-wrapper">
        <input
          ref={entryRef}
          id="target-entry"
          type="text"
          placeholder="e.g., main.ato:SensorBoard"
          value={entry}
            onChange={(e) => {
              setEntry(e.target.value)
              setShowSuggestions(true)
            }}
            onFocus={() => setShowSuggestions(true)}
            onKeyDown={handleEntryKeyDown}
          disabled={isCreating}
          autoComplete="off"
          required
        />
          {showSuggestions && suggestions.length > 0 && (
            <div className="entry-suggestions" ref={suggestionsRef}>
              {suggestions.map((module, index) => (
                <button
                  key={module.entry}
                  type="button"
                  className={`entry-suggestion ${index === highlightedIndex ? 'highlighted' : ''}`}
                  onClick={() => {
                    setEntry(module.entry)
                    setShowSuggestions(false)
                  }}
                  onMouseEnter={() => setHighlightedIndex(index)}
                >
                  <span className="suggestion-name">{module.name}</span>
                  <span className="suggestion-file">{module.file}</span>
                </button>
              ))}
            </div>
          )}
        </div>
        <span className={`form-hint ${getEntryStatusClass()}`}>
          {getEntryStatusMessage()}
        </span>
      </div>

      <div className="form-actions">
        <button
          type="button"
          className="form-btn secondary"
          onClick={onCancel}
          disabled={isCreating}
        >
          Cancel
        </button>
        <button
          type="submit"
          className="form-btn primary"
          disabled={isCreating || !name.trim() || !entry.trim()}
        >
          {isCreating ? 'Creating...' : 'Create'}
        </button>
      </div>
    </form>
  )
}

// New Project Form component
function NewProjectForm({
  onSubmit,
  onCancel,
  isCreating,
  error,
}: {
  onSubmit: (data: NewProjectData) => void
  onCancel: () => void
  isCreating?: boolean
  error?: string | null
}) {
  const [name, setName] = useState('')
  const [license, setLicense] = useState('')
  const [description, setDescription] = useState('')
  const nameRef = useRef<HTMLInputElement>(null)

  // Focus name input on mount
  useEffect(() => {
    nameRef.current?.focus()
  }, [])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit({
      name: name.trim() || undefined,
      license: license || undefined,
      description: description.trim() || undefined,
    })
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      onCancel()
    }
  }

  return (
    <form className="new-project-form" onSubmit={handleSubmit} onKeyDown={handleKeyDown}>
      <div className="form-header">
        <span className="form-title">Create New Project</span>
        <button
          type="button"
          className="form-close-btn"
          onClick={onCancel}
          disabled={isCreating}
        >
          <X size={14} />
        </button>
      </div>

      {error && (
        <div className="form-error">
          <AlertCircle size={14} />
          <span>{error}</span>
        </div>
      )}

      <div className="form-field">
        <label htmlFor="project-name">Name</label>
        <input
          ref={nameRef}
          id="project-name"
          type="text"
          placeholder="my-project (optional)"
          value={name}
          onChange={(e) => setName(e.target.value)}
          disabled={isCreating}
        />
      </div>

      <div className="form-field">
        <label htmlFor="project-license">License</label>
        <select
          id="project-license"
          value={license}
          onChange={(e) => setLicense(e.target.value)}
          disabled={isCreating}
        >
          {LICENSE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      <div className="form-field">
        <label htmlFor="project-description">Description</label>
        <textarea
          id="project-description"
          placeholder="Project description (optional)"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          disabled={isCreating}
          rows={2}
        />
      </div>

      <div className="form-actions">
        <button
          type="button"
          className="form-btn secondary"
          onClick={onCancel}
          disabled={isCreating}
        >
          Cancel
        </button>
        <button
          type="submit"
          className="form-btn primary"
          disabled={isCreating}
        >
          {isCreating ? 'Creating...' : 'Create'}
        </button>
      </div>
    </form>
  )
}

// Build status icon component
function BuildStatusIcon({ status }: { status: QueuedBuild['status'] }) {
  switch (status) {
    case 'success':
      return <CheckCircle2 size={14} className="status-icon success" />
    case 'failed':
      return <XCircle size={14} className="status-icon failed" />
    case 'warning':
      return <AlertTriangle size={14} className="status-icon warning" />
    case 'cancelled':
      return <AlertCircle size={14} className="status-icon cancelled" />
    default:
      return null
  }
}

// Build Queue Item component
// Stage status icon component
function StageStatusIcon({ status }: { status: string }) {
  switch (status) {
    case 'success':
      return <CheckCircle2 size={10} className="stage-icon success" />
    case 'failed':
    case 'error':
      return <XCircle size={10} className="stage-icon failed" />
    case 'warning':
      return <AlertCircle size={10} className="stage-icon warning" />
    case 'running':
    case 'building':
      return <span className="stage-icon running">●</span>
    case 'skipped':
      return <span className="stage-icon skipped">○</span>
    default:
      return <span className="stage-icon pending">○</span>
  }
}

function getCurrentStage(build: QueuedBuild): { name: string } | null {
  if (!build.stages || build.stages.length === 0) return null

  const running = build.stages.find(
    (stage) => stage.status === 'running' || stage.status === 'building'
  )
  if (running) {
    return { name: running.displayName || running.name }
  }

  const completed = [...build.stages].reverse().find((stage) =>
    stage.status === 'success' ||
    stage.status === 'warning' ||
    stage.status === 'failed' ||
    stage.status === 'error'
  )

  if (completed) {
    return { name: completed.displayName || completed.name }
  }

  return null
}

function BuildQueueItem({
  build,
  onCancel,
}: {
  build: QueuedBuild
  onCancel?: (buildId: string) => void
}) {
  const [isExpanded, setIsExpanded] = useState(false)

  // Calculate progress from stages
  const progress = useMemo(() => {
    if (!build.stages || build.stages.length === 0) return 0
    const totalStages = 14 // Default expected stages
    const completedStages = build.stages.filter(
      (s) => s.status === 'success' || s.status === 'warning'
    ).length
    return Math.round((completedStages / totalStages) * 100)
  }, [build.stages])

  const targetName = build.target || build.entry || 'default'
  const isComplete = build.status === 'success' || build.status === 'failed' || build.status === 'cancelled' || build.status === 'warning'
  const hasStages = build.stages && build.stages.length > 0
  const canExpand = true
  const buildCounter = useMemo(() => getBuildCounter(build.buildId), [build.buildId])
  const currentStage = useMemo(() => getCurrentStage(build), [build])

  const elapsed = build.elapsedSeconds ?? 0

  const totalDuration = build.elapsedSeconds ?? null

  const runningStageElapsed = useMemo(() => {
    if (!build.stages || build.stages.length === 0) return null
    const running = build.stages.find((stage) => stage.status === 'running')
    return running?.elapsedSeconds ?? null
  }, [build.stages])

  const completedAt = useMemo(() => {
    if (!build.startedAt) return null
    if (build.elapsedSeconds && build.elapsedSeconds > 0) {
      return build.startedAt + build.elapsedSeconds
    }
    return null
  }, [build.startedAt, build.elapsedSeconds])

  const statusLabel = useMemo(() => {
    switch (build.status) {
      case 'queued':
        return 'Queued'
      case 'building':
        return ''
      case 'success':
      case 'failed':
      case 'warning':
      case 'cancelled':
        return completedAt ? formatRelativeSeconds(completedAt) : ''
      default:
        return build.status
    }
  }, [build.status, progress, completedAt])

  const elapsedLabel = useMemo(() => {
    if (build.status !== 'queued' && build.status !== 'building') return ''
    if (elapsed > 0) return formatDuration(elapsed)
    return '0s'
  }, [build.status, elapsed])

  return (
    <div className={`build-queue-item ${build.status} ${isExpanded ? 'expanded' : ''}`}>
      <div className="build-queue-header" onClick={() => canExpand && setIsExpanded(!isExpanded)}>
        {canExpand && (
          <ChevronDown
            size={10}
            className={`build-expand-icon ${isExpanded ? 'open' : ''}`}
          />
        )}
        {isComplete && <BuildStatusIcon status={build.status} />}
        <div className="build-queue-info">
          <span className="build-queue-target">{targetName}</span>
          {build.status === 'building' && currentStage && (
            <span className="build-queue-stage" title={currentStage.name}>
              {currentStage.name}
            </span>
          )}
        </div>
        {statusLabel && (
          <div className="build-queue-meta">
            <span className="build-queue-status">{statusLabel}</span>
            {elapsedLabel && (
              <span className="build-queue-time">{elapsedLabel}</span>
            )}
          </div>
        )}
        {build.status === 'building' && (
          <div className="build-queue-progress">
            <div
              className="build-queue-progress-bar"
              style={{ width: `${progress}%` }}
            />
          </div>
        )}
        {(build.status === 'queued' || build.status === 'building') && onCancel && build.buildId && (
          <button
            className="build-queue-cancel"
            onClick={(e) => {
              e.stopPropagation()
              onCancel(build.buildId)
            }}
            title="Cancel build"
          >
            <X size={10} />
          </button>
        )}
      </div>

      {/* Expanded stages view */}
      {isExpanded && (
        <div className="build-stages">
          <div className="build-stages-header">
            <span className="build-stages-title">Steps ({build.stages?.length ?? 0})</span>
            <div className="build-stages-meta">
              {buildCounter && <span className="build-queue-counter">{buildCounter}</span>}
              {totalDuration && <span className="build-stages-total">Total {formatDuration(totalDuration)}</span>}
            </div>
          </div>
          {hasStages ? (
            build.stages!.map((stage, index) => (
              <div
                key={index}
                className={`build-stage ${stage.status} build-stage-clickable`}
                onClick={(e) => {
                  e.stopPropagation()
                  if (build.buildId) {
                    useStore.getState().setLogViewerBuildId(build.buildId)
                    sendAction('setLogViewCurrentId', { buildId: build.buildId, stage: stage.stageId || stage.name })
                  }
                }}
                title={`View logs for ${stage.displayName || stage.name}`}
              >
                <StageStatusIcon status={stage.status} />
                <span className="stage-name">{stage.displayName || stage.name}</span>
                {(() => {
                  const stageElapsed = stage.status === 'running'
                    ? runningStageElapsed ?? stage.elapsedSeconds
                    : stage.elapsedSeconds
                  if (stageElapsed === undefined || stageElapsed === null) return null
                  if (stage.status === 'pending') return null
                  return (
                    <span className="stage-time">{formatDuration(stageElapsed)}</span>
                  )
                })()}
              </div>
            ))
          ) : (
            <div className="build-stages-empty">No steps recorded</div>
          )}
        </div>
      )}
    </div>
  )
}

export function ActiveProjectPanel({
  projects,
  selectedProjectRoot,
  selectedTargetName,
  projectModules,
  onSelectProject,
  onSelectTarget,
  onBuildTarget,
  onBuildAllTargets,
  onOpenKiCad,
  onOpen3D,
  onOpenLayout,
  onCreateProject,
  onCreateTarget,
  onGenerateManufacturingData,
  queuedBuilds = [],
  onCancelBuild,
}: ActiveProjectPanelProps) {
  const [showBuildQueue, setShowBuildQueue] = useState(false)
  const [showNewProjectForm, setShowNewProjectForm] = useState(false)
  const [showNewTargetForm, setShowNewTargetForm] = useState(false)
  const [isCreatingProject, setIsCreatingProject] = useState(false)
  const [isCreatingTarget, setIsCreatingTarget] = useState(false)
  const [createProjectError, setCreateProjectError] = useState<string | null>(null)
  const [createTargetError, setCreateTargetError] = useState<string | null>(null)

  const handleCreateProject = useCallback(async (data?: NewProjectData) => {
    if (!onCreateProject) return
    setIsCreatingProject(true)
    setCreateProjectError(null)

    try {
      await onCreateProject(data)
      // Success - close form
      setShowNewProjectForm(false)
    } catch (error) {
      // Display error to user
      setCreateProjectError(error instanceof Error ? error.message : 'Failed to create project')
    } finally {
      setIsCreatingProject(false)
    }
  }, [onCreateProject])

  // Reset errors when forms are opened
  useEffect(() => {
    if (showNewProjectForm) {
      setCreateProjectError(null)
    }
  }, [showNewProjectForm])

  useEffect(() => {
    if (showNewTargetForm) {
      setCreateTargetError(null)
    }
  }, [showNewTargetForm])

  const activeProject = useMemo(() => {
    if (!projects || projects.length === 0) return null
    const match = selectedProjectRoot
      ? projects.find((p) => p.root === selectedProjectRoot)
      : null
    return match || projects[0] || null
  }, [projects, selectedProjectRoot])

  const activeTargetName = useMemo(() => {
    if (!activeProject) return null
    if (selectedTargetName) return selectedTargetName
    return activeProject.targets?.[0]?.name ?? null
  }, [activeProject, selectedTargetName])

  const handleCreateTarget = useCallback(async (data: NewTargetData) => {
    if (!onCreateTarget || !activeProject) return
    setIsCreatingTarget(true)
    setCreateTargetError(null)

    try {
      await onCreateTarget(activeProject.root, data)
      // Success - close form
      setShowNewTargetForm(false)
    } catch (error) {
      // Display error to user
      setCreateTargetError(error instanceof Error ? error.message : 'Failed to create build')
    } finally {
      setIsCreatingTarget(false)
    }
  }, [onCreateTarget, activeProject])

  // Filter builds for active project
  const projectBuilds = useMemo(() => {
    if (!activeProject) return []
    return queuedBuilds.filter((b) => b.projectRoot === activeProject.root)
  }, [queuedBuilds, activeProject])

  // Auto-expand build queue when builds are active
  useEffect(() => {
    if (projectBuilds.length > 0 && !showBuildQueue) {
      setShowBuildQueue(true)
    }
  }, [projectBuilds.length])

  useEffect(() => {
    if (!activeProject) return
    if (!selectedProjectRoot) {
      onSelectProject(activeProject.root)
      return
    }
    if (!selectedTargetName && activeTargetName) {
      onSelectTarget(activeProject.root, activeTargetName)
    }
  }, [activeProject, selectedProjectRoot, selectedTargetName, activeTargetName, onSelectProject, onSelectTarget])

  // Tooltip text based on state
  const getOutputTooltip = (action: string) => {
    if (!activeProject) return 'Select a project first'
    if (!activeTargetName) return 'Select a build first'
    return `Open ${action} for ${activeTargetName}`
  }

  return (
    <div className="projects-panel-v2">
      {/* New Project Form (shown as overlay when active) */}
      {showNewProjectForm && (
        <NewProjectForm
          onSubmit={handleCreateProject}
          onCancel={() => setShowNewProjectForm(false)}
          isCreating={isCreatingProject}
          error={createProjectError}
        />
      )}

      {/* New Target Form (shown as overlay when active) */}
      {showNewTargetForm && (
        <NewTargetForm
          onSubmit={handleCreateTarget}
          onCancel={() => setShowNewTargetForm(false)}
          isCreating={isCreatingTarget}
          error={createTargetError}
          projectName={activeProject?.name}
          projectRoot={activeProject?.root}
          modules={projectModules}
        />
      )}

      {/* Project Selector Row */}
      <div className="project-selector-row">
        <ProjectSelector
          projects={projects}
          activeProject={activeProject}
          onSelectProject={onSelectProject}
          onCreateProject={onCreateProject ? () => setShowNewProjectForm(true) : undefined}
        />
        {onCreateProject && (
          <button
            className="new-project-btn"
            onClick={() => setShowNewProjectForm(true)}
            title="Create new project"
          >
            <Plus size={14} />
          </button>
        )}
      </div>

      <div className="builds-section">
        <div className="builds-header">
          <span className="section-label">Builds</span>
        </div>

        <div className="build-targets">
          <TargetSelector
            targets={activeProject?.targets || []}
            activeTargetName={activeTargetName}
            onSelectTarget={(targetName) => {
              if (activeProject) {
                onSelectTarget(activeProject.root, targetName)
              }
            }}
            onCreateTarget={onCreateTarget && activeProject ? () => setShowNewTargetForm(true) : undefined}
            disabled={!activeProject}
          />
        </div>

        <div className="build-controls">
          <button
            className="control-btn primary"
            onClick={() => {
              if (!activeProject || !activeTargetName) return
              onBuildTarget(activeProject.root, activeTargetName)
            }}
            disabled={!activeProject || !activeTargetName}
            title={activeTargetName ? `Build ${activeTargetName}` : 'Select a build first'}
          >
            <Play size={12} />
            <span>Build</span>
          </button>
          <button
            className="control-btn"
            onClick={() => {
              if (!activeProject) return
              onBuildAllTargets(activeProject.root, activeProject.name)
            }}
            disabled={!activeProject}
            title={activeProject ? `Build all in ${activeProject.name}` : 'Select a project first'}
          >
            <Layers size={12} />
            <span>Build All</span>
          </button>
          {onGenerateManufacturingData && (
            <button
              className="control-btn"
              onClick={() => {
                if (!activeProject || !activeTargetName) return
                onGenerateManufacturingData(activeProject.root, activeTargetName)
              }}
              disabled={!activeProject || !activeTargetName}
              title={
                activeProject && activeTargetName
                  ? `Generate manufacturing files for ${activeTargetName}`
                  : 'Run a build first to generate manufacturing data'
              }
            >
              <Package size={12} />
              <span>MFG Data</span>
            </button>
          )}
        </div>

        <div className="build-outputs">
          <button
            className="control-btn output-btn"
            onClick={() => {
              if (!activeProject || !activeTargetName) return
              onOpenKiCad(activeProject.root, activeTargetName)
            }}
            disabled={!activeProject || !activeTargetName}
            title={getOutputTooltip('KiCad schematic editor')}
          >
            <Layers size={12} />
            <span>KiCad</span>
          </button>
          <button
            className="control-btn output-btn"
            onClick={() => {
              if (!activeProject || !activeTargetName) return
              onOpen3D(activeProject.root, activeTargetName)
            }}
            disabled={!activeProject || !activeTargetName}
            title={getOutputTooltip('3D board viewer')}
          >
            <Cuboid size={12} />
            <span>3D</span>
          </button>
          <button
            className="control-btn output-btn"
            onClick={() => {
              if (!activeProject || !activeTargetName) return
              onOpenLayout(activeProject.root, activeTargetName)
            }}
            disabled={!activeProject || !activeTargetName}
            title={getOutputTooltip('PCB layout editor')}
          >
            <Layout size={12} />
            <span>Layout</span>
          </button>
          <button
            className="control-btn output-btn"
            onClick={() => {
              const targetBuilds = projectBuilds.filter(b => b.target === activeTargetName)
              const latestBuild = targetBuilds.length > 0 ? targetBuilds[0] : projectBuilds[0]
              if (latestBuild?.buildId) {
                useStore.getState().setLogViewerBuildId(latestBuild.buildId)
                sendAction('setLogViewCurrentId', { buildId: latestBuild.buildId, stage: null })
              }
            }}
            disabled={!activeProject || projectBuilds.length === 0}
            title={projectBuilds.length > 0 ? 'View build logs' : 'No builds available'}
          >
            <ScrollText size={12} />
            <span>Logs</span>
          </button>
        </div>

        {/* Build Queue - always visible, collapsed when empty */}
        <div className="build-queue-section">
          <button
            className="build-queue-toggle"
            onClick={() => setShowBuildQueue(!showBuildQueue)}
          >
            <ChevronDown
              size={12}
              className={`toggle-chevron ${showBuildQueue ? 'open' : ''}`}
            />
            <span>Build Queue</span>
          </button>
          {showBuildQueue && (
            <div className="build-queue-list">
              {projectBuilds.length === 0 ? (
                <div className="build-queue-empty">No recent builds</div>
              ) : (
                projectBuilds.map((build) => (
                  <BuildQueueItem
                    key={build.buildId}
                    build={build}
                    onCancel={onCancelBuild}
                  />
                ))
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
