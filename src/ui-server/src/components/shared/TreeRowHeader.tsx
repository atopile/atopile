import { ReactNode, KeyboardEvent } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import './TreeRowHeader.css'

export interface TreeRowHeaderProps {
  /** Whether this row is expandable (has children) */
  isExpandable?: boolean
  /** Whether this row is currently expanded */
  isExpanded?: boolean
  /** Click handler for the row */
  onClick?: () => void
  /** Keyboard event handler */
  onKeyDown?: (e: KeyboardEvent<HTMLDivElement>) => void
  /** Icon to display (rendered component) */
  icon?: ReactNode
  /** Primary label/name */
  label: string
  /** Secondary label (type name) - displayed after the primary label with ": " prefix */
  secondaryLabel?: string
  /** Right-aligned value (alternative to secondaryLabel - displayed at the end of the row) */
  rightValue?: string
  /** Count badge (number of children/items) */
  count?: number
  /** Additional class name */
  className?: string
  /** Title attribute for tooltip */
  title?: string
  /** Nesting depth for indentation (0 = root level) */
  depth?: number
  /** Whether this is a group header (affects count badge styling) */
  isGroupHeader?: boolean
  /** Tab index for keyboard navigation */
  tabIndex?: number
  /** ARIA role */
  role?: string
  /** ARIA expanded state */
  ariaExpanded?: boolean
  /** Whether the label was truncated (shows dotted underline on hover) */
  labelTruncated?: boolean
  /** Whether the right value was truncated */
  rightValueTruncated?: boolean
}

/**
 * Shared tree row header component used for collapsible tree structures.
 * Used by StandardLibraryPanel, VariablesPanel, StructurePanel (ModuleTreeNode), and other tree views.
 *
 * Structure:
 * [Chevron] [Icon] [Label] [: SecondaryLabel] ... [RightValue] [Count badge]
 *
 * - secondaryLabel: Inline after label with ": " prefix (e.g., "myModule: Module")
 * - rightValue: Right-aligned at end of row (e.g., type annotations in Structure panel)
 */
export function TreeRowHeader({
  isExpandable = false,
  isExpanded = false,
  onClick,
  onKeyDown,
  icon,
  label,
  secondaryLabel,
  rightValue,
  count,
  className = '',
  title,
  depth = 0,
  isGroupHeader = false,
  tabIndex,
  role,
  ariaExpanded,
  labelTruncated = false,
  rightValueTruncated = false,
}: TreeRowHeaderProps) {
  // Calculate padding based on depth (6px per level + 4px base padding from CSS)
  const depthPadding = depth > 0 ? { paddingLeft: `${depth * 6 + 8}px` } : undefined

  return (
    <div
      className={`tree-row-header ${isExpanded ? 'expanded' : ''} ${isGroupHeader ? 'tree-group-header' : ''} ${className}`}
      onClick={onClick}
      onKeyDown={onKeyDown}
      title={title}
      style={depthPadding}
      tabIndex={tabIndex}
      role={role}
      aria-expanded={ariaExpanded}
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
      <span className={`tree-row-label ${labelTruncated ? 'truncated' : ''}`}>{label}</span>

      {/* Secondary label (inline after primary, with colon prefix) */}
      {secondaryLabel && (
        <span className="tree-row-secondary">{secondaryLabel}</span>
      )}

      {/* Right-aligned value (for type annotations, specs, etc.) */}
      {rightValue && (
        <span className={`tree-row-right-value ${rightValueTruncated ? 'truncated' : ''}`}>
          {rightValue}
        </span>
      )}

      {/* Count badge */}
      {count !== undefined && count > 0 && (
        <span className="tree-row-count">{count}</span>
      )}
    </div>
  )
}
