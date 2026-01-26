import { useEffect, useMemo, useRef, useState, useCallback } from 'react'
import { FileCode, Loader2, AlertTriangle, Search, X } from 'lucide-react'
import type { ModuleChild, ModuleDefinition, Project } from '../types/build'
import { sendActionWithResponse } from '../api/websocket'
import { ModuleTree } from './ModuleTreeNode'
import './StructurePanel.css'

interface StructurePanelProps {
  activeFilePath: string | null
  lastAtoFile: string | null
  projects: Project[]
  projectModules: Record<string, ModuleDefinition[]>
  onFetchModules: (projectRoot: string) => void
}

type ExplorerState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; modules: StructureModule[] }

interface StructureModule {
  name: string
  entry: string | null
  children: ModuleChild[]
}

function findProjectRoot(filePath: string, projects: Project[]): Project | null {
  if (!filePath || projects.length === 0) return null
  const normalized = filePath.replace(/\\/g, '/')
  const candidates = projects.filter((p) => normalized.startsWith(p.root.replace(/\\/g, '/') + '/'))
  if (candidates.length === 0) return null
  return candidates.sort((a, b) => b.root.length - a.root.length)[0]
}

/**
 * Recursively filter children based on search term.
 * A node matches if its name or typeName contains the search term (case-insensitive).
 * Parent nodes are included if any of their descendants match.
 */
function filterChildren(children: ModuleChild[], searchTerm: string): ModuleChild[] {
  if (!searchTerm) return children

  const lowerSearch = searchTerm.toLowerCase()

  function nodeMatches(node: ModuleChild): boolean {
    return (
      node.name.toLowerCase().includes(lowerSearch) ||
      node.typeName.toLowerCase().includes(lowerSearch) ||
      (node.spec?.toLowerCase().includes(lowerSearch) ?? false)
    )
  }

  function filterNode(node: ModuleChild): ModuleChild | null {
    const directMatch = nodeMatches(node)
    const filteredChildren = node.children
      ? node.children.map(filterNode).filter((c): c is ModuleChild => c !== null)
      : []

    // Include node if it matches directly or has matching descendants
    if (directMatch || filteredChildren.length > 0) {
      return {
        ...node,
        children: filteredChildren,
      }
    }

    return null
  }

  return children.map(filterNode).filter((c): c is ModuleChild => c !== null)
}

export function StructurePanel({
  activeFilePath,
  lastAtoFile,
  projects,
  projectModules,
  onFetchModules,
}: StructurePanelProps) {
  const [state, setState] = useState<ExplorerState>({ status: 'idle' })
  const [searchTerm, setSearchTerm] = useState('')
  const [expandedPathsByModule, setExpandedPathsByModule] = useState<Map<string, Set<string>>>(
    new Map()
  )
  const requestIdRef = useRef(0)
  const lastRequestKeyRef = useRef<string | null>(null)
  const searchInputRef = useRef<HTMLInputElement>(null)

  // Store expanded paths per file so they persist when switching files
  const expandedPathsPerFile = useRef<Map<string, Map<string, Set<string>>>>(new Map())

  // Dev mode: default file path relative to project root
  const DEV_DEFAULT_RELATIVE_PATH = 'examples/equations/equations.ato'

  // Determine the effective file to display:
  // - If active file is .ato, use it
  // - Otherwise, fall back to lastAtoFile
  // - In dev mode with projects but no file, try default
  const effectiveAtoFile = useMemo(() => {
    if (activeFilePath?.toLowerCase().endsWith('.ato')) {
      return activeFilePath
    }
    if (lastAtoFile) {
      return lastAtoFile
    }
    // Dev mode fallback: use default file from first project with matching path
    if (import.meta.env.DEV && projects.length > 0) {
      for (const project of projects) {
        const candidate = `${project.root.replace(/\\/g, '/')}/${DEV_DEFAULT_RELATIVE_PATH}`
        // We can't check file existence in frontend, so just use first project
        return candidate
      }
    }
    return null
  }, [activeFilePath, lastAtoFile, projects])

  const activeProject = useMemo(() => {
    if (!effectiveAtoFile) return null
    return findProjectRoot(effectiveAtoFile, projects)
  }, [effectiveAtoFile, projects])

  const displayPath = useMemo(() => {
    if (!effectiveAtoFile) return 'No .ato file selected'
    if (!activeProject) return effectiveAtoFile
    const prefix = activeProject.root.replace(/\\/g, '/') + '/'
    const normalized = effectiveAtoFile.replace(/\\/g, '/')
    return normalized.startsWith(prefix) ? normalized.slice(prefix.length) : effectiveAtoFile
  }, [effectiveAtoFile, activeProject])

  const activeProjectModules = activeProject
    ? projectModules[activeProject.root]
    : undefined

  // Filter children based on search term
  const filteredModules = useMemo(() => {
    if (state.status !== 'ready') return []
    if (!searchTerm) return state.modules

    const lowerSearch = searchTerm.toLowerCase()

    return state.modules
      .map((module) => {
        if (module.name.toLowerCase().includes(lowerSearch)) {
          return module
        }
        const filteredChildren = filterChildren(module.children, searchTerm)
        return {
          ...module,
          children: filteredChildren,
        }
      })
      .filter((module) => module.children.length > 0 || module.name.toLowerCase().includes(lowerSearch))
  }, [state, searchTerm])

  // Handle expansion state changes - persist per file
  const handleExpandedPathsChange = useCallback((moduleKey: string, newPaths: Set<string>) => {
    setExpandedPathsByModule(prev => {
      const next = new Map(prev)
      next.set(moduleKey, newPaths)
      if (effectiveAtoFile) {
        expandedPathsPerFile.current.set(effectiveAtoFile, next)
      }
      return next
    })
  }, [effectiveAtoFile])

  const handleClearSearch = useCallback(() => {
    setSearchTerm('')
    searchInputRef.current?.focus()
  }, [])

  // Restore expansion state when switching files
  useEffect(() => {
    if (effectiveAtoFile) {
      const savedPaths = expandedPathsPerFile.current.get(effectiveAtoFile)
      if (savedPaths) {
        setExpandedPathsByModule(savedPaths)
      } else {
        setExpandedPathsByModule(new Map())
      }
    } else {
      setExpandedPathsByModule(new Map())
    }
  }, [effectiveAtoFile])

  useEffect(() => {
    if (!effectiveAtoFile) {
      setState({ status: 'idle' })
      return
    }
    // Wait for projects to load before showing "outside workspace" error
    if (projects.length === 0) {
      setState({ status: 'loading' })
      return
    }
    if (!activeProject) {
      setState({ status: 'error', message: 'File is outside the current workspace' })
      return
    }

    if (!activeProjectModules || activeProjectModules.length === 0) {
      onFetchModules(activeProject.root)
    }

    const requestKey = `${activeProject.root}:${effectiveAtoFile}`
    if (lastRequestKeyRef.current === requestKey && state.status === 'ready') {
      return
    }

    const requestId = ++requestIdRef.current
    lastRequestKeyRef.current = requestKey
    setState({ status: 'loading' })
    sendActionWithResponse('getModuleChildrenForFile', {
      projectRoot: activeProject.root,
      filePath: effectiveAtoFile,
      maxDepth: 5,
    })
      .then((response) => {
        if (requestId !== requestIdRef.current) return
        const result = response.result ?? {}
        const modules = Array.isArray((result as { modules?: unknown }).modules)
          ? (result as { modules: StructureModule[] }).modules
          : null
        if (modules) {
          setState({ status: 'ready', modules })
          return
        }
        const children = Array.isArray((result as { children?: unknown }).children)
          ? (result as { children: ModuleChild[] }).children
          : []
        const moduleName = (result as { moduleName?: string | null }).moduleName ?? null
        const entry = (result as { entry?: string | null }).entry ?? null
        setState({
          status: 'ready',
          modules: [
            {
              name: moduleName || 'Module',
              entry,
              children,
            },
          ],
        })
      })
      .catch((error) => {
        if (requestId !== requestIdRef.current) return
        setState({ status: 'error', message: error.message || 'Failed to load structure' })
      })
  }, [effectiveAtoFile, activeProject, activeProjectModules, onFetchModules, projects.length])

  useEffect(() => {
    if (!effectiveAtoFile || state.status !== 'ready') return
    setExpandedPathsByModule(prev => {
      const next = new Map(prev)
      let changed = false
      for (const module of state.modules) {
        const key = module.entry || module.name
        if (!next.has(key)) {
          next.set(key, new Set(['__root__']))
          changed = true
        }
      }
      if (changed) {
        expandedPathsPerFile.current.set(effectiveAtoFile, next)
        return next
      }
      return prev
    })
  }, [effectiveAtoFile, state])

  return (
    <div className="structure-panel">
      <div className="structure-header">
        <FileCode size={14} />
        <div className="structure-meta">
          <span className="structure-title">Active ATO</span>
          <span className="structure-path" title={displayPath}>{displayPath}</span>
        </div>
      </div>

      {/* Search bar - only show when we have content */}
      {state.status === 'ready' && state.modules.some((m) => m.children.length > 0) && (
        <div className="structure-search">
          <Search size={14} className="structure-search-icon" />
          <input
            ref={searchInputRef}
            type="text"
            className="structure-search-input"
            placeholder="Filter structure..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
          {searchTerm && (
            <button
              className="structure-search-clear"
              onClick={handleClearSearch}
              title="Clear search"
            >
              <X size={14} />
            </button>
          )}
        </div>
      )}

      <div className="structure-body">
        {state.status === 'idle' && (
          <div className="structure-empty">
            <span>Open an .ato file to view the structure</span>
          </div>
        )}
        {state.status === 'loading' && (
          <div className="structure-loading">
            <Loader2 size={16} className="spin" />
            <span>Loading structure...</span>
          </div>
        )}
        {state.status === 'error' && (
          <div className="structure-error">
            <AlertTriangle size={14} />
            <span>{state.message}</span>
          </div>
        )}
        {state.status === 'ready' && (
          filteredModules.length > 0 ? (
            <div className="structure-modules">
              {filteredModules.map((module) => {
                const key = module.entry || module.name
                const expandedPaths = expandedPathsByModule.get(key) ?? new Set(['__root__'])
                return (
                  <div key={key} className="structure-module">
                    <ModuleTree
                      children={module.children}
                      rootName={module.name}
                      expandedPaths={expandedPaths}
                      onExpandedPathsChange={(paths) => handleExpandedPathsChange(key, paths)}
                    />
                    {module.children.length === 0 && !searchTerm && (
                      <div className="structure-empty">
                        <span>No structure found</span>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          ) : searchTerm ? (
            <div className="structure-empty">
              <span>No matches for "{searchTerm}"</span>
            </div>
          ) : (
            <div className="structure-empty">
              <span>No structure found</span>
            </div>
          )
        )}
      </div>
    </div>
  )
}
