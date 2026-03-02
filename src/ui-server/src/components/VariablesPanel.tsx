import { useState, useEffect, useCallback, useMemo, memo, useRef } from 'react'
import {
  Box, Zap,
  Hash, Percent, CircuitBoard, RefreshCw,
  AlertTriangle, Loader2, Check
} from 'lucide-react'
import { smartTruncatePair } from './sidebar-modules/sidebarUtils'
import { PanelSearchBox } from './shared/PanelSearchBox'
import { EmptyState } from './shared/EmptyState'
import { TreeRowHeader } from './shared/TreeRowHeader'

// Variable types
type VariableType = 'voltage' | 'current' | 'resistance' | 'capacitance' | 'ratio' | 'frequency' | 'power' | 'percentage' | 'dimensionless'

interface Variable {
  name: string
  spec?: string              // Design spec (what the design requires - user input or calculated)
  specTolerance?: string     // Spec tolerance
  actual?: string            // Component actual rating (from datasheet)
  actualTolerance?: string   // Actual tolerance
  unit?: string
  type: VariableType
  meetsSpec?: boolean        // Does actual meet spec? (false = error)
  source?: string            // Where this value came from (e.g., "user", "derived", "picked", "datasheet")
}

interface VariableNode {
  name: string
  type: 'module' | 'interface' | 'component'
  path: string
  typeName?: string  // The type name (e.g., "I2C", "SPI", "Resistor")
  variables?: Variable[]
  children?: VariableNode[]
  expanded?: boolean
}

interface VariablesData {
  version: string
  build_id?: string
  nodes: VariableNode[]
}

// Get icon for variable type
function getVariableIcon(type: VariableType) {
  switch (type) {
    case 'voltage':
      return <Zap size={12} className="var-icon voltage" />
    case 'current':
      return <Zap size={12} className="var-icon current" />
    case 'resistance':
      return <Hash size={12} className="var-icon resistance" />
    case 'capacitance':
      return <Hash size={12} className="var-icon capacitance" />
    case 'ratio':
    case 'percentage':
      return <Percent size={12} className="var-icon ratio" />
    case 'frequency':
      return <RefreshCw size={12} className="var-icon frequency" />
    case 'power':
      return <Zap size={12} className="var-icon power" />
    default:
      return <Hash size={12} className="var-icon" />
  }
}

// Get node type icon
function getNodeIcon(type: 'module' | 'interface' | 'component') {
  switch (type) {
    case 'module':
      return <Box size={14} className="node-type-icon module" />
    case 'interface':
      return <Zap size={14} className="node-type-icon interface" />
    case 'component':
      return <CircuitBoard size={14} className="node-type-icon component" />
  }
}

// Variable row component - table style, memoized to prevent unnecessary re-renders
const VariableRow = memo(function VariableRow({ variable, onCopy }: { variable: Variable; onCopy: (value: string) => void }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    let fullValue = `${variable.name}: `
    if (variable.spec) fullValue += `${variable.spec}${variable.specTolerance || ''}`
    if (variable.actual) fullValue += ` → ${variable.actual}${variable.actualTolerance || ''}`
    if (variable.unit) fullValue += ` ${variable.unit}`
    onCopy(fullValue)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  const hasSpec = variable.spec !== undefined
  const hasActual = variable.actual !== undefined
  const hasError = variable.meetsSpec === false

  return (
    <div
      className={`variable-table-row ${hasError ? 'error' : ''}`}
      onClick={handleCopy}
      title="Click to copy"
    >
      {/* Name column */}
      <div className="var-col-name">
        {getVariableIcon(variable.type)}
        <span className="var-name-text">{variable.name}</span>
      </div>

      {/* Spec column */}
      <div className="var-col-spec">
        {hasSpec ? (
          <>
            <span className="var-spec-value">{variable.spec}</span>
            {variable.specTolerance && <span className="var-tolerance">{variable.specTolerance}</span>}
          </>
        ) : (
          <span className="var-empty">—</span>
        )}
      </div>

      {/* Actual column */}
      <div className={`var-col-actual ${hasError ? 'error' : hasActual ? 'ok' : ''}`}>
        {hasActual ? (
          <>
            <span className="var-actual-value">{variable.actual}</span>
            {variable.actualTolerance && <span className="var-tolerance">{variable.actualTolerance}</span>}
          </>
        ) : (
          <span className="var-empty">—</span>
        )}
      </div>

      {/* Status */}
      <div className="var-col-status">
        {hasError && <AlertTriangle size={12} className="status-error" />}
        {copied && <Check size={12} className="status-copied" />}
      </div>
    </div>
  )
})

// Helper function to check if a variable matches source filter
function matchesSourceFilter(source: string | undefined, sourceFilter: SourceFilter): boolean {
  if (sourceFilter === 'all') return true
  const s = source || 'derived'
  if (sourceFilter === 'user') return s === 'user'
  if (sourceFilter === 'computed') return s === 'derived'
  if (sourceFilter === 'picked') return s === 'picked' || s === 'datasheet'
  return true
}

// Helper function to check if a variable matches search query (pre-lowercased)
function matchesSearch(v: Variable, searchLower: string): boolean {
  if (!searchLower) return true
  return (
    v.name.toLowerCase().includes(searchLower) ||
    (v.spec?.toLowerCase().includes(searchLower) ?? false) ||
    (v.actual?.toLowerCase().includes(searchLower) ?? false)
  )
}

// Recursive function to check if any descendant matches filters
// Memoized at component level to avoid recalculating on every render
function nodeOrDescendantsMatch(
  node: VariableNode,
  searchLower: string,
  sourceFilter: SourceFilter
): boolean {
  // Check if node name matches
  if (searchLower && node.name.toLowerCase().includes(searchLower)) return true

  // Check if any variables match
  const hasMatchingVar = node.variables?.some(v =>
    matchesSourceFilter(v.source, sourceFilter) && matchesSearch(v, searchLower)
  )
  if (hasMatchingVar) return true

  // Check children recursively
  if (node.children?.some(child => nodeOrDescendantsMatch(child, searchLower, sourceFilter))) {
    return true
  }

  return false
}

// Collect paths that should be expanded to reveal search matches
function collectExpandedPathsForSearch(
  nodes: VariableNode[],
  searchLower: string,
  sourceFilter: SourceFilter
): Set<string> {
  const expanded = new Set<string>()

  const nodeMatches = (node: VariableNode): boolean => {
    if (searchLower && node.name.toLowerCase().includes(searchLower)) return true
    const hasMatchingVar = node.variables?.some(v =>
      matchesSourceFilter(v.source, sourceFilter) && matchesSearch(v, searchLower)
    )
    return !!hasMatchingVar
  }

  const walk = (node: VariableNode): boolean => {
    let childMatch = false
    if (node.children && node.children.length > 0) {
      for (const child of node.children) {
        if (walk(child)) childMatch = true
      }
    }

    const directMatch = nodeMatches(node)
    const shouldExpand = (directMatch || childMatch) && (node.children?.length || 0) > 0
    if (shouldExpand) expanded.add(node.path)
    return directMatch || childMatch
  }

  for (const node of nodes) {
    walk(node)
  }

  return expanded
}

// Tree node component - memoized to prevent unnecessary re-renders
const VariableNodeComponent = memo(function VariableNodeComponent({
  node,
  depth,
  searchQuery,
  sourceFilter,
  expandedNodes,
  onToggleExpand,
  onCopyValue
}: {
  node: VariableNode
  depth: number
  searchQuery: string
  sourceFilter: SourceFilter
  expandedNodes: Set<string>
  onToggleExpand: (path: string) => void
  onCopyValue: (value: string) => void
}) {
  const isExpanded = expandedNodes.has(node.path)
  const hasChildren = (node.children && node.children.length > 0) || (node.variables && node.variables.length > 0)
  const searchLower = searchQuery.toLowerCase()

  // Memoize filtered variables - filter operation that runs on every node
  const filteredVariables = useMemo(() => {
    if (!node.variables) return []
    return node.variables.filter(v =>
      matchesSourceFilter(v.source, sourceFilter) && matchesSearch(v, searchLower)
    )
  }, [node.variables, sourceFilter, searchLower])

  // Memoize the filter match check - recursive check
  const matchesFilters = useMemo(() => {
    // No filtering needed if no search and showing all sources
    if (!searchQuery && sourceFilter === 'all') return true

    // Check this node and its descendants
    return nodeOrDescendantsMatch(node, searchLower, sourceFilter)
  }, [node, searchQuery, sourceFilter, searchLower])

  if (!matchesFilters) return null

  // Smart truncation for name and type to prevent overflow
  // Max 35 total characters for name + type combined (fits sidebar width)
  const [displayName, displayTypeName] = node.typeName
    ? smartTruncatePair(node.name, node.typeName, 35)
    : [node.name.length > 35 ? node.name.slice(0, 32) + '…' : node.name, ''];

  return (
    <div className={`variable-tree-node depth-${Math.min(depth, 4)}`}>
      <TreeRowHeader
        className="variable-node-header"
        isExpandable={hasChildren}
        isExpanded={isExpanded}
        onClick={() => onToggleExpand(node.path)}
        icon={getNodeIcon(node.type)}
        label={displayName}
        secondaryLabel={displayTypeName || undefined}
        count={node.variables?.length}
        title={node.name}
      />

      {isExpanded && (
        <div className="variable-node-content">
          {/* Variables table */}
          {filteredVariables.length > 0 && (
            <div className="variables-table">
              <div className="variables-table-header">
                <div className="var-col-name">Parameter</div>
                <div className="var-col-spec">Spec</div>
                <div className="var-col-actual">Actual</div>
                <div className="var-col-status"></div>
              </div>
              {filteredVariables.map((variable, idx) => (
                <VariableRow
                  key={`${node.path}-${variable.name}-${idx}`}
                  variable={variable}
                  onCopy={onCopyValue}
                />
              ))}
            </div>
          )}

          {/* Children */}
          {node.children?.map((child, idx) => (
            <VariableNodeComponent
              key={`${child.path}-${idx}`}
              node={child}
              depth={depth + 1}
              searchQuery={searchQuery}
              sourceFilter={sourceFilter}
              expandedNodes={expandedNodes}
              onToggleExpand={onToggleExpand}
              onCopyValue={onCopyValue}
            />
          ))}
        </div>
      )}
    </div>
  )
})

// Source filter options
type SourceFilter = 'all' | 'user' | 'computed' | 'picked'

interface VariablesPanelProps {
  // Variables data from state - frontend just displays this
  variablesData?: VariablesData | null
  isLoading?: boolean
  error?: string | null
  // Active context for empty state messages
  selectedTargetName?: string | null
  hasActiveProject?: boolean
  isExpanded?: boolean
}

export function VariablesPanel({
  variablesData,
  isLoading = false,
  error = null,
  selectedTargetName = null,
  hasActiveProject = false,
  isExpanded = false,
}: VariablesPanelProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set())
  // Always show all sources (filter removed per user request)
  const sourceFilter: SourceFilter = 'all'
  const [lastDataVersion, setLastDataVersion] = useState<string | null>(null)
  const lastSearchRef = useRef('')
  const expandedBeforeSearchRef = useRef<Set<string> | null>(null)

  // Extract variables from data
  const variables = variablesData?.nodes || []

  // Collapse all nodes when new data arrives
  useEffect(() => {
    const version = variablesData?.version
    if (version && version !== lastDataVersion) {
      setExpandedNodes(new Set())
      setLastDataVersion(version)
    }
  }, [variablesData?.version, lastDataVersion])

  const searchLower = searchQuery.trim().toLowerCase()

  const searchExpandedPaths = useMemo(() => {
    if (!searchLower) return null
    return collectExpandedPathsForSearch(variables, searchLower, sourceFilter)
  }, [variables, searchLower, sourceFilter])

  useEffect(() => {
    const prevSearch = lastSearchRef.current
    if (!prevSearch && searchLower) {
      expandedBeforeSearchRef.current = expandedNodes
      setExpandedNodes(searchExpandedPaths || new Set())
    } else if (searchLower) {
      setExpandedNodes(searchExpandedPaths || new Set())
    } else if (prevSearch && !searchLower && expandedBeforeSearchRef.current) {
      setExpandedNodes(expandedBeforeSearchRef.current)
      expandedBeforeSearchRef.current = null
    }
    lastSearchRef.current = searchLower
  }, [searchLower, searchExpandedPaths, expandedNodes])

  // Memoized callbacks to prevent child re-renders
  const handleToggleExpand = useCallback((path: string) => {
    setExpandedNodes(prev => {
      const next = new Set(prev)
      if (next.has(path)) {
        next.delete(path)
      } else {
        next.add(path)
      }
      return next
    })
  }, [])

  const handleCopyValue = useCallback((value: string) => {
    navigator.clipboard.writeText(value)
  }, [])

  // Helper for empty state description
  const getEmptyDescription = () => {
    if (selectedTargetName) {
      return `Run a build for "${selectedTargetName}" to generate variable data`
    }
    if (hasActiveProject) {
      return 'Select a build and run it to generate variable data'
    }
    return 'Select a project and build, then run it'
  }

  const toolbar = (
    <PanelSearchBox
      value={searchQuery}
      onChange={setSearchQuery}
      placeholder="Search variables..."
      autoFocus={isExpanded}
    />
  )

  // Loading state
  if (isLoading) {
    return (
      <div className="variables-panel">
        {toolbar}
        <div className="variables-loading">
          <Loader2 size={24} className="spinner" />
          <span>Loading variables...</span>
        </div>
      </div>
    )
  }

  // Error state - treat "not found" as empty state
  if (error) {
    const isNotFound = error.includes('404') || error.includes('not found') || error.includes('not_found') || error.toLowerCase().includes('run build')
    return (
      <div className="variables-panel">
        {toolbar}
        {isNotFound ? (
          <EmptyState
            title="No variables found"
            description={getEmptyDescription()}
          />
        ) : (
          <EmptyState
            title="Error loading variables"
            description={error}
          />
        )}
      </div>
    )
  }

  // Empty state - no variables
  if (variables.length === 0) {
    return (
      <div className="variables-panel">
        {toolbar}
        <EmptyState
          title="No variables found"
          description={getEmptyDescription()}
        />
      </div>
    )
  }

  // Normal state - has variables
  return (
    <div className="variables-panel">
      {toolbar}

      {/* Variable tree */}
      <div className="variables-tree">
        {variables.map((node, idx) => (
          <VariableNodeComponent
            key={`${node.path}-${idx}`}
            node={node}
            depth={0}
            searchQuery={searchQuery}
            sourceFilter={sourceFilter}
            expandedNodes={expandedNodes}
            onToggleExpand={handleToggleExpand}
            onCopyValue={handleCopyValue}
          />
        ))}
      </div>
    </div>
  )
}
