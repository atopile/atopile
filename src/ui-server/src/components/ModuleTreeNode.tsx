/**
 * ModuleTreeNode - Shared tree node component for displaying module children.
 * Used by StructurePanel for displaying module structure.
 *
 * Uses the shared TreeRowHeader component for consistent rendering with
 * StandardLibraryPanel and VariablesPanel.
 */

import { useState, useMemo, KeyboardEvent } from 'react'
import { Box, Zap, Cable, Hash, Cpu } from 'lucide-react'
import type { ModuleChild } from '../types/build'
import { smartTruncatePair } from './sidebar-modules/sidebarUtils'
import { TreeRowHeader } from './shared'
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

  const handleClick = () => {
    if (hasChildren) {
      onToggle(path)
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      if (hasChildren) {
        onToggle(path)
      }
    } else if (e.key === 'ArrowRight' && hasChildren && !isExpanded) {
      e.preventDefault()
      onToggle(path)
    } else if (e.key === 'ArrowLeft' && hasChildren && isExpanded) {
      e.preventDefault()
      onToggle(path)
    }
  }

  // Determine if right value should show unconstrained styling
  const isUnconstrained = itemType === 'parameter' && !child.spec

  return (
    <div className="tree-row-node">
      <TreeRowHeader
        isExpandable={hasChildren}
        isExpanded={isExpanded}
        onClick={handleClick}
        onKeyDown={handleKeyDown}
        icon={<Icon size={12} style={{ color: config.color }} />}
        label={displayName}
        rightValue={displayType}
        depth={depth}
        title={nameTruncated || typeTruncated ? `${child.name}: ${displayValue}` : undefined}
        tabIndex={0}
        role="treeitem"
        ariaExpanded={hasChildren ? isExpanded : undefined}
        labelTruncated={nameTruncated}
        rightValueTruncated={typeTruncated}
        className={isUnconstrained ? 'unconstrained-param' : ''}
      />

      {isExpanded && hasChildren && (
        <div className="tree-row-children">
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

  const handleKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      onToggle()
    } else if (e.key === 'ArrowRight' && !isExpanded) {
      e.preventDefault()
      onToggle()
    } else if (e.key === 'ArrowLeft' && isExpanded) {
      e.preventDefault()
      onToggle()
    }
  }

  return (
    <TreeRowHeader
      isExpandable={true}
      isExpanded={isExpanded}
      onClick={onToggle}
      onKeyDown={handleKeyDown}
      icon={<Icon size={12} style={{ color: config.color }} />}
      label={label}
      count={count}
      depth={depth}
      isGroupHeader={true}
      tabIndex={0}
      role="treeitem"
      ariaExpanded={isExpanded}
    />
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
          <div key={type} className="tree-row-type-group">
            <TypeGroupHeader
              type={type}
              count={items.length}
              isExpanded={isGroupExpanded}
              onToggle={() => onToggle(groupPath)}
              depth={depth}
            />
            {isGroupExpanded && (
              <div className="tree-row-group-items">
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
  // Optional controlled expansion state (for preserving across file changes)
  expandedPaths?: Set<string>
  onExpandedPathsChange?: (paths: Set<string>) => void
}

export function ModuleTree({
  children,
  rootName,
  rootType,
  grouped = true,
  expandedPaths: controlledExpandedPaths,
  onExpandedPathsChange,
}: ModuleTreeProps) {
  const [internalExpandedPaths, setInternalExpandedPaths] = useState<Set<string>>(new Set())

  // Use controlled or uncontrolled expansion state
  const expandedPaths = controlledExpandedPaths ?? internalExpandedPaths
  const setExpandedPaths = onExpandedPathsChange ?? setInternalExpandedPaths

  const handleToggle = (path: string) => {
    const newSet = new Set(expandedPaths)
    if (newSet.has(path)) {
      newSet.delete(path)
    } else {
      newSet.add(path)
    }
    setExpandedPaths(newSet)
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

    const handleRootKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault()
        handleToggle('__root__')
      } else if (e.key === 'ArrowRight' && !isRootExpanded) {
        e.preventDefault()
        handleToggle('__root__')
      } else if (e.key === 'ArrowLeft' && isRootExpanded) {
        e.preventDefault()
        handleToggle('__root__')
      }
    }

    return (
      <div className="module-tree" role="tree">
        <TreeRowHeader
          className="root-row"
          isExpandable={true}
          isExpanded={isRootExpanded}
          onClick={() => handleToggle('__root__')}
          onKeyDown={handleRootKeyDown}
          icon={<Icon size={14} style={{ color: config.color }} />}
          label={displayRootName}
          count={children.length}
          depth={0}
          title={rootNameTruncated ? rootName : undefined}
          tabIndex={0}
          role="treeitem"
          ariaExpanded={isRootExpanded}
          labelTruncated={rootNameTruncated}
        />
        {isRootExpanded && (
          <div className="tree-row-children">
            {children.length === 0 ? (
              <div className="module-tree-empty">No structure found</div>
            ) : grouped ? (
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
      <div className="module-tree" role="tree">
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
    <div className="module-tree" role="tree">
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
