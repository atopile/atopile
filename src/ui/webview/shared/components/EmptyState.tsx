import type { ReactNode } from 'react'

interface EmptyStateProps {
  title: string
  description?: string
  icon?: ReactNode
  children?: ReactNode
  className?: string
}

/**
 * Unified empty state component for consistent styling across all panels.
 * Uses the panel-empty-state class from _utilities.css.
 */
export function EmptyState({
  title,
  description,
  icon,
  children,
  className = '',
}: EmptyStateProps) {
  return (
    <div className={`panel-empty-state ${className}`.trim()}>
      {icon && <div className="empty-icon">{icon}</div>}
      <span className="empty-title">{title}</span>
      {description && (
        <span className="empty-description">{description}</span>
      )}
      {children}
    </div>
  )
}
