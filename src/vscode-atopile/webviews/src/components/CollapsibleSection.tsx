import { ChevronDown, ChevronRight, GripHorizontal, AlertCircle, AlertTriangle, X, Filter } from 'lucide-react'

interface CollapsibleSectionProps {
  id: string
  title: string
  badge?: number | string
  badgeType?: 'count' | 'filter'
  errorCount?: number
  warningCount?: number
  collapsed: boolean
  onToggle: () => void
  onClearFilter?: () => void
  height?: number
  onResizeStart?: (e: React.MouseEvent) => void
  children: React.ReactNode
  flexGrow?: boolean
}

export function CollapsibleSection({
  id,
  title,
  badge,
  badgeType = 'count',
  errorCount,
  warningCount,
  collapsed,
  onToggle,
  onClearFilter,
  height,
  onResizeStart,
  children,
  flexGrow
}: CollapsibleSectionProps) {
  // Has a manually set height?
  const hasManualHeight = !collapsed && height && !flexGrow

  return (
    <div
      className={`collapsible-section ${collapsed ? 'collapsed' : ''} ${flexGrow ? 'flex-grow' : ''} ${hasManualHeight ? 'has-height' : ''}`}
      style={hasManualHeight ? { height, flex: '0 0 auto' } : undefined}
      data-section-id={id}
    >
      <div className="section-title-bar" onClick={onToggle}>
        <button className="section-chevron">
          {collapsed ? <ChevronRight size={12} /> : <ChevronDown size={12} />}
        </button>
        <span className="section-title">{title}</span>
        
        {/* Error/Warning counts */}
        {errorCount !== undefined && errorCount > 0 && (
          <span className="section-error-count">
            <AlertCircle size={10} />
            {errorCount}
          </span>
        )}
        {warningCount !== undefined && warningCount > 0 && (
          <span className="section-warning-count">
            <AlertTriangle size={10} />
            {warningCount}
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
