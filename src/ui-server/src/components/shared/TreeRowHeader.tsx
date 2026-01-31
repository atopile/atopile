import { ReactNode } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import './TreeRowHeader.css'

export interface TreeRowHeaderProps {
  /** Whether this row is expandable (has children) */
  isExpandable?: boolean
  /** Whether this row is currently expanded */
  isExpanded?: boolean
  /** Click handler for the row */
  onClick?: () => void
  /** Icon to display (rendered component) */
  icon?: ReactNode
  /** Primary label/name */
  label: string
  /** Secondary label (type name, shown after colon) */
  secondaryLabel?: string
  /** Count badge (number of children/items) */
  count?: number
  /** Additional class name */
  className?: string
  /** Title attribute for tooltip */
  title?: string
}

/**
 * Shared tree row header component used for collapsible tree structures.
 * Used by StandardLibraryPanel, VariablesPanel, and other tree views.
 *
 * Structure:
 * [Chevron] [Icon] [Label] [: SecondaryLabel] [Count badge]
 */
export function TreeRowHeader({
  isExpandable = false,
  isExpanded = false,
  onClick,
  icon,
  label,
  secondaryLabel,
  count,
  className = '',
  title,
}: TreeRowHeaderProps) {
  return (
    <div
      className={`tree-row-header ${isExpanded ? 'expanded' : ''} ${className}`}
      onClick={onClick}
      title={title}
    >
      {/* Chevron for expand/collapse */}
      {isExpandable ? (
        <span className="tree-row-chevron">
          {isExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        </span>
      ) : (
        <span className="tree-row-chevron-spacer" />
      )}

      {/* Type icon */}
      {icon && <span className="tree-row-icon">{icon}</span>}

      {/* Primary label */}
      <span className="tree-row-label">{label}</span>

      {/* Secondary label (type name) */}
      {secondaryLabel && (
        <span className="tree-row-secondary">{secondaryLabel}</span>
      )}

      {/* Count badge */}
      {count !== undefined && count > 0 && (
        <span className="tree-row-count">{count}</span>
      )}
    </div>
  )
}
