/**
 * ModuleTreeNode - Shared tree node component for displaying module children.
 * Used by both BuildNode (lazy-loaded module structure) and StandardLibraryPanel.
 * Displays interfaces, parameters, modules with appropriate icons and colors.
 * Supports grouping children by type (components, modules, interfaces, parameters).
 */

import { useState, useMemo } from 'react'
import { ChevronDown, ChevronRight, Box, Zap, Cable, Hash, Cpu } from 'lucide-react'
import type { ModuleChild } from '../types/build'
import { smartTruncatePair } from './sidebar-modules/sidebarUtils'
import './ModuleTreeNode.css'

// Max characters for name + type combined (fits typical sidebar width)
const MAX_TOTAL_CHARS = 40

// Item types that can appear in the tree
type ItemType = 'interface' | 'module' | 'component' | 'trait' | 'parameter'

// Type configuration for icons and colors (order determines display priority)
const typeConfig: Record<ItemType, { icon: typeof Box; color: string; label: string; pluralLabel: string; order: number }> = {
  component: { icon: Cpu, color: 'var(--ctp-mauve)', label: 'Component', pluralLabel: 'Components', order: 0 },
  module: { icon: Box, color: 'var(--ctp-green)', label: 'Module', pluralLabel: 'Modules', order: 1 },
  interface: { icon: Cable, color: 'var(--ctp-blue)', label: 'Interface', pluralLabel: 'Interfaces', order: 2 },
  parameter: { icon: Hash, color: 'var(--ctp-peach)', label: 'Parameter', pluralLabel: 'Parameters', order: 3 },
  trait: { icon: Zap, color: 'var(--ctp-yellow)', label: 'Trait', pluralLabel: 'Traits', order: 4 },
}

// Order for displaying type groups
const typeOrder: ItemType[] = ['component', 'module', 'interface', 'parameter', 'trait']

// Helper to group children by item type
function groupChildrenByType(children: ModuleChild[]): Record<ItemType, ModuleChild[]> {
  const groups: Record<ItemType, ModuleChild[]> = {
    component: [],
    module: [],
    interface: [],
    parameter: [],
    trait: [],
  }

  for (const child of children) {
    const itemType = (child.itemType || 'interface') as ItemType
    groups[itemType].push(child)
  }

  // Sort each group alphabetically by name
  for (const type of typeOrder) {
    groups[type].sort((a, b) => a.name.localeCompare(b.name))
  }

  return groups
}

// Get display value for a child (spec for parameters, typeName otherwise)
function getDisplayValue(child: ModuleChild): string {
  if (child.itemType === 'parameter') {
    return child.spec || '—'
  }
  return child.typeName
}

interface ModuleTreeNodeProps {
  child: ModuleChild
  depth: number
  expandedPaths: Set<string>
  onToggle: (path: string) => void
  basePath?: string
  grouped?: boolean
}

export function ModuleTreeNode({
  child,
  depth,
  expandedPaths,
  onToggle,
  basePath = '',
  grouped = true
}: ModuleTreeNodeProps) {
  const path = basePath ? `${basePath}.${child.name}` : child.name
  const isExpanded = expandedPaths.has(path)
  const hasChildren = child.children && child.children.length > 0
  const itemType = (child.itemType || 'interface') as ItemType
  const config = typeConfig[itemType]
  const Icon = config.icon
  const displayValue = getDisplayValue(child)

  // Smart truncation to fit both name and type in available space
  // Reduce available chars based on depth (deeper = less space due to indentation)
  const availableChars = Math.max(25, MAX_TOTAL_CHARS - depth * 2)
  const [displayName, displayType] = smartTruncatePair(
    child.name,
    displayValue,
    availableChars
  )

  // Check if truncation occurred (for showing tooltip)
  const nameTruncated = displayName !== child.name
  const typeTruncated = displayType !== displayValue

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (hasChildren) {
      onToggle(path)
    }
  }

  return (
    <div className="module-tree-node">
      <div
        className={`module-tree-row ${hasChildren ? 'expandable' : ''}`}
        style={{ paddingLeft: `${depth * 6 + 4}px` }}
        onClick={handleClick}
        title={nameTruncated || typeTruncated ? `${child.name}: ${displayValue}` : undefined}
      >
        {hasChildren ? (
          <button className="module-tree-expand-btn" onClick={handleClick}>
            {isExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
          </button>
        ) : (
          <span className="module-tree-expand-spacer" />
        )}
        <span className="module-tree-icon" style={{ color: config.color }}>
          <Icon size={12} />
        </span>
        <span
          className={`module-tree-name ${nameTruncated ? 'truncated' : ''}`}
          title={nameTruncated ? child.name : undefined}
        >
          {displayName}
        </span>
        <span
          className={`module-tree-type ${itemType === 'parameter' && !child.spec ? 'unconstrained' : ''} ${typeTruncated ? 'truncated' : ''}`}
          style={{ color: itemType === 'parameter' ? 'var(--ctp-subtext0)' : config.color }}
          title={typeTruncated ? displayValue : undefined}
        >
          {displayType}
        </span>
      </div>

      {isExpanded && hasChildren && (
        <div className="module-tree-children">
          {grouped ? (
            <GroupedChildren
              children={child.children!}
              depth={depth + 1}
              expandedPaths={expandedPaths}
              onToggle={onToggle}
              basePath={path}
            />
          ) : (
            child.children!.map((subChild, idx) => (
              <ModuleTreeNode
                key={`${path}-${subChild.name}-${idx}`}
                child={subChild}
                depth={depth + 1}
                expandedPaths={expandedPaths}
                onToggle={onToggle}
                basePath={path}
                grouped={grouped}
              />
            ))
          )}
        </div>
      )}
    </div>
  )
}

// Type group header component
interface TypeGroupHeaderProps {
  type: ItemType
  count: number
  isExpanded: boolean
  onToggle: () => void
  depth: number
}

function TypeGroupHeader({ type, count, isExpanded, onToggle, depth }: TypeGroupHeaderProps) {
  const config = typeConfig[type]
  const Icon = config.icon
  const label = count === 1 ? config.label : config.pluralLabel

  return (
    <div
      className="module-tree-row module-tree-group-header expandable"
      style={{ paddingLeft: `${depth * 6 + 4}px` }}
      onClick={onToggle}
    >
      <button className="module-tree-expand-btn" onClick={(e) => { e.stopPropagation(); onToggle() }}>
        {isExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
      </button>
      <span className="module-tree-icon" style={{ color: config.color }}>
        <Icon size={12} />
      </span>
      <span className="module-tree-group-label" style={{ color: config.color }}>
        {label}
      </span>
      <span className="module-tree-group-count">({count})</span>
    </div>
  )
}

// Grouped tree node - renders children grouped by type
interface GroupedChildrenProps {
  children: ModuleChild[]
  depth: number
  expandedPaths: Set<string>
  onToggle: (path: string) => void
  basePath: string
}

function GroupedChildren({ children, depth, expandedPaths, onToggle, basePath }: GroupedChildrenProps) {
  const grouped = useMemo(() => groupChildrenByType(children), [children])

  // Count non-empty groups
  const nonEmptyGroups = typeOrder.filter(type => grouped[type].length > 0)

  // If only one group type has items, render without group headers
  if (nonEmptyGroups.length === 1) {
    const items = grouped[nonEmptyGroups[0]]
    return (
      <>
        {items.map((child, idx) => (
          <ModuleTreeNode
            key={`${basePath}-${child.name}-${idx}`}
            child={child}
            depth={depth}
            expandedPaths={expandedPaths}
            onToggle={onToggle}
            basePath={basePath}
            grouped={true}
          />
        ))}
      </>
    )
  }

  return (
    <>
      {typeOrder.map(type => {
        const items = grouped[type]
        if (items.length === 0) return null

        const groupPath = `${basePath}.__group_${type}`
        const isGroupExpanded = expandedPaths.has(groupPath)

        return (
          <div key={type} className="module-tree-type-group">
            <TypeGroupHeader
              type={type}
              count={items.length}
              isExpanded={isGroupExpanded}
              onToggle={() => onToggle(groupPath)}
              depth={depth}
            />
            {isGroupExpanded && (
              <div className="module-tree-group-items">
                {items.map((child, idx) => (
                  <ModuleTreeNode
                    key={`${basePath}-${child.name}-${idx}`}
                    child={child}
                    depth={depth + 1}
                    expandedPaths={expandedPaths}
                    onToggle={onToggle}
                    basePath={basePath}
                    grouped={true}
                  />
                ))}
              </div>
            )}
          </div>
        )
      })}
    </>
  )
}

// Root component for the entire module tree
interface ModuleTreeProps {
  children: ModuleChild[]
  rootName?: string
  rootType?: string
  grouped?: boolean  // Whether to group children by type (default: true)
}

export function ModuleTree({ children, rootName, rootType, grouped = true }: ModuleTreeProps) {
  const [expandedPaths, setExpandedPaths] = useState<Set<string>>(new Set())

  const handleToggle = (path: string) => {
    setExpandedPaths(prev => {
      const newSet = new Set(prev)
      if (newSet.has(path)) {
        newSet.delete(path)
      } else {
        newSet.add(path)
      }
      return newSet
    })
  }

  // If there's a root name, show it as the parent
  if (rootName) {
    const rootItemType = (rootType === 'component' ? 'component' : 'module') as ItemType
    const config = typeConfig[rootItemType]
    const Icon = config.icon
    const isRootExpanded = expandedPaths.has('__root__')

    // Truncate root name if too long (leave room for count badge)
    const maxRootLen = MAX_TOTAL_CHARS - 5
    const displayRootName = rootName.length > maxRootLen
      ? rootName.slice(0, maxRootLen - 1) + '…'
      : rootName
    const rootNameTruncated = displayRootName !== rootName

    return (
      <div className="module-tree">
        <div
          className="module-tree-row expandable root"
          onClick={() => handleToggle('__root__')}
          title={rootNameTruncated ? rootName : undefined}
        >
          <button className="module-tree-expand-btn">
            {isRootExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
          </button>
          <span className="module-tree-icon" style={{ color: config.color }}>
            <Icon size={14} />
          </span>
          <span className={`module-tree-name root-name ${rootNameTruncated ? 'truncated' : ''}`}>
            {displayRootName}
          </span>
          <span className="module-tree-count">{children.length}</span>
        </div>
        {isRootExpanded && (
          <div className="module-tree-children">
            {grouped ? (
              <GroupedChildren
                children={children}
                depth={1}
                expandedPaths={expandedPaths}
                onToggle={handleToggle}
                basePath=""
              />
            ) : (
              children.map((child, idx) => (
                <ModuleTreeNode
                  key={`${child.name}-${idx}`}
                  child={child}
                  depth={1}
                  expandedPaths={expandedPaths}
                  onToggle={handleToggle}
                  grouped={grouped}
                />
              ))
            )}
          </div>
        )}
      </div>
    )
  }

  // No root name - show children directly (grouped or flat)
  if (grouped) {
    return (
      <div className="module-tree">
        <GroupedChildren
          children={children}
          depth={0}
          expandedPaths={expandedPaths}
          onToggle={handleToggle}
          basePath=""
        />
      </div>
    )
  }

  return (
    <div className="module-tree">
      {children.map((child, idx) => (
        <ModuleTreeNode
          key={`${child.name}-${idx}`}
          child={child}
          depth={0}
          expandedPaths={expandedPaths}
          onToggle={handleToggle}
          grouped={grouped}
        />
      ))}
    </div>
  )
}
