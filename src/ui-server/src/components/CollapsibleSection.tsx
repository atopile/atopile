import { ChevronDown, ChevronRight, GripHorizontal, AlertCircle, AlertTriangle, X, Filter, Loader2 } from 'lucide-react'

interface CollapsibleSectionProps {
  id: string
  title: string
  badge?: number | string
  badgeType?: 'count' | 'filter'
  errorCount?: number
  warningCount?: number
  warningMessage?: string | null
  loading?: boolean
  collapsed: boolean
  onToggle: () => void
  onClearFilter?: () => void
  height?: number  // Calculated height from usePanelSizing (includes title bar)
  onResizeStart?: (e: React.MouseEvent) => void
  children: React.ReactNode
}

export function CollapsibleSection({
  id,
  title,
  badge,
  badgeType = 'count',
  errorCount,
  warningCount,
  warningMessage,
  loading,
  collapsed,
  onToggle,
  onClearFilter,
  height,
  onResizeStart,
  children,
}: CollapsibleSectionProps) {
  // Build style: use calculated height if provided, otherwise let CSS handle it
  const sectionStyle: React.CSSProperties | undefined = collapsed
    ? undefined  // Collapsed: CSS handles it (flex: 0 0 auto)
    : height
      ? { height, flex: '0 0 auto' }  // Explicit height from calculation
      : { flex: '1 1 0', minHeight: 0 }  // Fallback: share space equally

  return (
    <div
      className={`collapsible-section ${collapsed ? 'collapsed' : ''} ${height ? 'has-height' : ''}`}
      style={sectionStyle}
      data-section-id={id}
    >
      <div className="section-title-bar" onClick={onToggle}>
        <button className="section-chevron">
          {collapsed ? <ChevronRight size={12} /> : <ChevronDown size={12} />}
        </button>
        <span className="section-title">{title}</span>

        {/* Loading spinner */}
        {loading && (
          <span className="section-loading">
            <Loader2 size={12} className="animate-spin" />
          </span>
        )}

        {/* Error/Warning counts */}
        {errorCount !== undefined && errorCount > 0 && (
          <span className="section-error-count">
            <AlertCircle size={10} />
            {errorCount}
          </span>
        )}
        {warningCount !== undefined && warningCount > 0 && (
          <span className="section-warning-count" title={warningMessage || undefined}>
            <AlertTriangle size={10} />
            {warningCount}
          </span>
        )}
        {/* Show warning icon for message-only warnings (no count) */}
        {warningMessage && (warningCount === undefined || warningCount === 0) && (
          <span className="section-warning-message" title={warningMessage}>
            <AlertTriangle size={10} />
          </span>
        )}

        {/* Badge (count or filter) */}
        {badge !== undefined && (
          <span className={`section-badge ${badgeType === 'filter' ? 'filter-badge' : ''}`}>
            {badgeType === 'filter' && <Filter size={8} />}
            {badge}
            {badgeType === 'filter' && onClearFilter && (
              <button
                className="clear-filter-btn"
                onClick={(e) => {
                  e.stopPropagation()
                  onClearFilter()
                }}
                title="Clear filter"
              >
                <X size={8} />
              </button>
            )}
          </span>
        )}
      </div>

      {!collapsed && (
        <>
          <div className="section-body">
            {children}
          </div>
          {onResizeStart && (
            <div
              className="section-resize-handle"
              onMouseDown={onResizeStart}
            >
              <GripHorizontal size={10} />
            </div>
          )}
        </>
      )}
    </div>
  )
}
