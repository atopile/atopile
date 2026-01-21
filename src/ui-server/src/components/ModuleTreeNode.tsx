/**
 * ModuleTreeNode - Shared tree node component for displaying module children.
 * Used by both BuildNode (lazy-loaded module structure) and StandardLibraryPanel.
 * Displays interfaces, parameters, modules with appropriate icons and colors.
 */

import { useState } from 'react'
import { ChevronDown, ChevronRight, Box, Zap, Cable, Hash, Cpu } from 'lucide-react'
import type { ModuleChild } from '../types/build'
import './ModuleTreeNode.css'

// Item types that can appear in the tree
type ItemType = 'interface' | 'module' | 'component' | 'trait' | 'parameter'

// Type configuration for icons and colors
const typeConfig: Record<ItemType, { icon: typeof Box; color: string; label: string }> = {
  interface: { icon: Cable, color: 'var(--ctp-blue)', label: 'Interface' },
  module: { icon: Box, color: 'var(--ctp-green)', label: 'Module' },
  component: { icon: Cpu, color: 'var(--ctp-mauve)', label: 'Component' },
  trait: { icon: Zap, color: 'var(--ctp-yellow)', label: 'Trait' },
  parameter: { icon: Hash, color: 'var(--ctp-peach)', label: 'Parameter' },
}

interface ModuleTreeNodeProps {
  child: ModuleChild
  depth: number
  expandedPaths: Set<string>
  onToggle: (path: string) => void
  basePath?: string
}

export function ModuleTreeNode({
  child,
  depth,
  expandedPaths,
  onToggle,
  basePath = ''
}: ModuleTreeNodeProps) {
  const path = basePath ? `${basePath}.${child.name}` : child.name
  const isExpanded = expandedPaths.has(path)
  const hasChildren = child.children && child.children.length > 0
  const itemType = child.itemType || 'interface'
  const config = typeConfig[itemType]
  const Icon = config.icon

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
        style={{ paddingLeft: `${depth * 12 + 4}px` }}
        onClick={handleClick}
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
        <span className="module-tree-name">{child.name}</span>
        <span className="module-tree-type" style={{ color: config.color }}>
          {child.typeName}
        </span>
      </div>

      {isExpanded && hasChildren && (
        <div className="module-tree-children">
          {child.children!.map((subChild, idx) => (
            <ModuleTreeNode
              key={`${path}-${subChild.name}-${idx}`}
              child={subChild}
              depth={depth + 1}
              expandedPaths={expandedPaths}
              onToggle={onToggle}
              basePath={path}
            />
          ))}
        </div>
      )}
    </div>
  )
}

// Root component for the entire module tree
interface ModuleTreeProps {
  children: ModuleChild[]
  rootName?: string
  rootType?: string
}

export function ModuleTree({ children, rootName, rootType }: ModuleTreeProps) {
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
    const rootItemType = rootType === 'component' ? 'component' : 'module'
    const config = typeConfig[rootItemType]
    const Icon = config.icon
    const isRootExpanded = expandedPaths.has('__root__')

    return (
      <div className="module-tree">
        <div
          className="module-tree-row expandable root"
          onClick={() => handleToggle('__root__')}
        >
          <button className="module-tree-expand-btn">
            {isRootExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
          </button>
          <span className="module-tree-icon" style={{ color: config.color }}>
            <Icon size={14} />
          </span>
          <span className="module-tree-name root-name">{rootName}</span>
          <span className="module-tree-count">{children.length}</span>
        </div>
        {isRootExpanded && (
          <div className="module-tree-children">
            {children.map((child, idx) => (
              <ModuleTreeNode
                key={`${child.name}-${idx}`}
                child={child}
                depth={1}
                expandedPaths={expandedPaths}
                onToggle={handleToggle}
              />
            ))}
          </div>
        )}
      </div>
    )
  }

  // No root name - show children directly
  return (
    <div className="module-tree">
      {children.map((child, idx) => (
        <ModuleTreeNode
          key={`${child.name}-${idx}`}
          child={child}
          depth={0}
          expandedPaths={expandedPaths}
          onToggle={handleToggle}
        />
      ))}
    </div>
  )
}
