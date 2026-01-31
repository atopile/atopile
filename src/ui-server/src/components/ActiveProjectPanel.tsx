import { useEffect, useMemo, useState, useRef, useCallback } from 'react'
import { FolderOpen, Play, Layers, Cuboid, Layout, Plus, ChevronDown, Check, X, Factory, AlertCircle, Target } from 'lucide-react'
import type { Project, BuildTarget } from '../types/build'
import { postMessage } from '../api/vscodeApi'
import './ActiveProjectPanel.css'

// Re-export BuildQueueItem for use in standalone BuildQueue panel
export { BuildQueueItem } from './BuildQueueItem'

interface NewProjectData {
  name: string
  license?: string
  description?: string
  parentDirectory?: string
}

// Get workspace root from window object (set by VS Code extension)
const getWorkspaceRoot = (): string => {
  if (typeof window !== 'undefined') {
    return (window as Window & { __ATOPILE_WORKSPACE_ROOT__?: string }).__ATOPILE_WORKSPACE_ROOT__ || ''
  }
  return ''
}

interface ActiveProjectPanelProps {
  projects: Project[]
  selectedProjectRoot: string | null
  selectedTargetName: string | null
  projectModules?: ModuleDefinition[]
  onSelectProject: (projectRoot: string | null) => void
  onSelectTarget: (projectRoot: string, targetName: string) => void
  onBuildTarget: (projectRoot: string, targetName: string) => void
  onOpenKiCad: (projectRoot: string, targetName: string) => void
  onOpen3D: (projectRoot: string, targetName: string) => void
  onOpenLayout: (projectRoot: string, targetName: string) => void
  onCreateProject?: (data?: NewProjectData) => Promise<void>
  onCreateTarget?: (projectRoot: string, data: NewTargetData) => Promise<void>
  onGenerateManufacturingData?: (projectRoot: string, targetName: string) => void
}

// Helper to format path for display - shows last 2 segments
function formatPath(path: string): string {
  if (!path) return ''
  const parts = path.split('/')
  // Show last 2 segments (e.g., "examples/equations")
  return parts.slice(-2).join('/')
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

// ProjectSelector component - combobox with inline search
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
        <FolderOpen
          size={12}
          className="combobox-icon"
          onClick={() => inputRef.current?.focus()}
          style={{ marginRight: '2px' }}
        />
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
          <Target size={14} className="target-icon" />
          <span className="target-trigger-name">{activeTarget?.name || 'Select build'}</span>
          {activeTarget?.entry && (
            <span className="target-trigger-entry">{activeTarget.entry.split(':').pop()}</span>
          )}
          <ChevronDown size={14} className={`chevron ${isOpen ? 'open' : ''}`} />
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
  target_exists: boolean
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

    // Check if entry matches an existing module (still need to check target_exists from API)
    const matchingModule = modules?.find(m => m.entry === entry)

    // Debounce the check
    const timer = setTimeout(async () => {
      setIsCheckingEntry(true)
      try {
        const { sendActionWithResponse } = await import('../api/websocket')
        const response = await sendActionWithResponse('checkEntry', {
          project_root: projectRoot,
          entry,
        })
        const result = response.result as { success?: boolean; file_exists?: boolean; module_exists?: boolean; target_exists?: boolean } | undefined
        if (result?.success) {
          setEntryStatus({
            file_exists: matchingModule ? true : Boolean(result.file_exists),
            module_exists: matchingModule ? true : Boolean(result.module_exists),
            target_exists: Boolean(result.target_exists),
          })
        }
      } catch (err) {
        setEntryStatus({ file_exists: false, module_exists: false, target_exists: false })
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

  // Validate entry format: should be file.ato:ModuleName
  const isValidEntryFormat = (value: string): boolean => {
    const trimmed = value.trim()
    if (!trimmed) return false
    // Must contain .ato: followed by at least one character
    const match = trimmed.match(/\.ato:(.+)$/)
    return match !== null && match[1].length > 0
  }

  const entryFormatError = entry.trim() && !isValidEntryFormat(entry)
    ? 'Entry must be in format: file.ato:ModuleName'
    : null

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim() || !entry.trim() || !isValidEntryFormat(entry) || entryStatus?.target_exists) return
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
    if (entryFormatError) return entryFormatError
    if (isCheckingEntry) return 'Checking...'
    if (!entryStatus) return 'Format: file.ato:ModuleName'
    if (entryStatus.target_exists) return '✗ Entry already used as build target'
    if (entryStatus.module_exists) return '✓ Module exists'
    if (entryStatus.file_exists) return '⚠ Module not found in file'
    return '⚠ Entry does not exist'
  }

  const getEntryStatusClass = () => {
    if (entryFormatError) return 'status-error'
    if (!entryStatus || isCheckingEntry) return ''
    if (entryStatus.target_exists) return 'status-error'
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
          disabled={isCreating || !name.trim() || !entry.trim() || !isValidEntryFormat(entry) || entryStatus?.target_exists}
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
  const [parentDirectory, setParentDirectory] = useState(getWorkspaceRoot())
  const [license, setLicense] = useState('')
  const [description, setDescription] = useState('')
  const nameRef = useRef<HTMLInputElement>(null)

  // Focus name input on mount
  useEffect(() => {
    nameRef.current?.focus()
  }, [])

  // Listen for browse result from VS Code
  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      const message = event.data
      if (message?.type === 'browseProjectPathResult' && message.path) {
        setParentDirectory(message.path)
      }
    }
    window.addEventListener('message', handleMessage)
    return () => window.removeEventListener('message', handleMessage)
  }, [])

  const handleBrowse = () => {
    postMessage({ type: 'browseProjectPath' })
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const trimmedName = name.trim()
    if (!trimmedName) return
    onSubmit({
      name: trimmedName,
      license: license || undefined,
      description: description.trim() || undefined,
      parentDirectory: parentDirectory || undefined,
    })
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      onCancel()
    }
  }

  const isValid = name.trim().length > 0

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
        <label htmlFor="project-name">Name <span className="required">*</span></label>
        <input
          ref={nameRef}
          id="project-name"
          type="text"
          placeholder="my-project"
          value={name}
          onChange={(e) => setName(e.target.value)}
          disabled={isCreating}
          required
        />
      </div>

      <div className="form-field">
        <label htmlFor="project-path">Location</label>
        <div className="form-path-input">
          <input
            id="project-path"
            type="text"
            placeholder="/path/to/projects"
            value={parentDirectory}
            onChange={(e) => setParentDirectory(e.target.value)}
            disabled={isCreating}
            title={parentDirectory}
          />
          <button
            type="button"
            className="form-browse-btn"
            onClick={handleBrowse}
            disabled={isCreating}
            title="Browse..."
          >
            <FolderOpen size={12} />
          </button>
        </div>
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
          disabled={isCreating || !isValid}
        >
          {isCreating ? 'Creating...' : 'Create'}
        </button>
      </div>
    </form>
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
  onOpenKiCad,
  onOpen3D,
  onOpenLayout,
  onCreateProject,
  onCreateTarget,
  onGenerateManufacturingData,
}: ActiveProjectPanelProps) {
  const [showNewProjectForm, setShowNewProjectForm] = useState(false)
  const [showNewTargetForm, setShowNewTargetForm] = useState(false)
  const [isCreatingProject, setIsCreatingProject] = useState(false)
  const [isCreatingTarget, setIsCreatingTarget] = useState(false)
  const [createProjectError, setCreateProjectError] = useState<string | null>(null)
  const [createTargetError, setCreateTargetError] = useState<string | null>(null)

  const handleCreateProject = useCallback(async (data: NewProjectData) => {
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

      {/* Project Section */}
      <div className="project-section">
        <div className="section-header">
          <span className="section-label">Project</span>
        </div>
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
      </div>

      {/* Build Section */}
      <div className="builds-section">
        <div className="section-header">
          <span className="section-label">Build</span>
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

        {/* Action buttons - single row: Build | KiCad | 3D | Layout | Manufacture */}
        <div className="build-actions-row">
          <button
            className="action-btn primary"
            onClick={() => {
              if (!activeProject || !activeTargetName) return
              onBuildTarget(activeProject.root, activeTargetName)
            }}
            disabled={!activeProject || !activeTargetName}
            title={activeTargetName ? `Build ${activeTargetName}` : 'Select a build first'}
          >
            <Play size={12} />
            <span className="action-label">Build</span>
          </button>

          <div className="action-divider" />

          <button
            className="action-btn"
            onClick={() => {
              if (!activeProject || !activeTargetName) return
              onOpenKiCad(activeProject.root, activeTargetName)
            }}
            disabled={!activeProject || !activeTargetName}
            title={getOutputTooltip('KiCad schematic editor')}
          >
            <Layers size={12} />
            <span className="action-label">KiCad</span>
          </button>

          <div className="action-divider" />

          <button
            className="action-btn"
            onClick={() => {
              if (!activeProject || !activeTargetName) return
              onOpen3D(activeProject.root, activeTargetName)
            }}
            disabled={!activeProject || !activeTargetName}
            title={getOutputTooltip('3D board viewer')}
          >
            <Cuboid size={12} />
            <span className="action-label">3D</span>
          </button>

          <div className="action-divider" />

          <button
            className="action-btn"
            onClick={() => {
              if (!activeProject || !activeTargetName) return
              onOpenLayout(activeProject.root, activeTargetName)
            }}
            disabled={!activeProject || !activeTargetName}
            title={getOutputTooltip('PCB layout editor')}
          >
            <Layout size={12} />
            <span className="action-label">Layout</span>
          </button>

          <div className="action-divider" />

          {onGenerateManufacturingData && (
            <button
              className="action-btn"
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
              <Factory size={12} />
              <span className="action-label">Manufacture</span>
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
