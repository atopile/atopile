import { ChevronDown, ChevronRight, GripHorizontal, AlertCircle, AlertTriangle, X, Filter, Loader2 } from 'lucide-react'

interface CollapsibleSectionProps {
  id: string
  title: string
  badge?: number | string
  badgeType?: 'count' | 'filter'
  errorCount?: number
  warningCount?: number
  warningMessage?: string | null  // Tooltip message for warnings (e.g., "Registry unavailable")
  loading?: boolean  // Show loading spinner in title bar
  collapsed: boolean
  onToggle: () => void
  onClearFilter?: () => void
  height?: number
  maxHeight?: number  // Auto-size up to this max, then scroll
  onResizeStart?: (e: React.MouseEvent) => void
  children: React.ReactNode
  flexGrow?: boolean
  autoSize?: boolean
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
  maxHeight,
  onResizeStart,
  children,
  flexGrow,
  autoSize
}: CollapsibleSectionProps) {
  // Has a manually set height?
  const hasManualHeight = !collapsed && height && !flexGrow
  // Auto-size with max constraint?
  const hasMaxHeight = !collapsed && !height && maxHeight && !flexGrow
  const hasAutoSize = !collapsed && autoSize && !height && !maxHeight && !flexGrow

  // Build style object
  const sectionStyle: React.CSSProperties | undefined = hasManualHeight
    ? { height, flex: '0 1 auto', minHeight: 0 }
    : hasMaxHeight
    ? { maxHeight, flex: '0 1 auto', minHeight: 0 }
    : hasAutoSize
    ? { flex: '0 1 auto', minHeight: 0 }
    : undefined

  return (
    <div
      className={`collapsible-section ${collapsed ? 'collapsed' : ''} ${flexGrow ? 'flex-grow' : ''} ${hasManualHeight ? 'has-height' : ''} ${hasMaxHeight ? 'has-max-height' : ''}`}
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
          {onResizeStart && !flexGrow && (
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
