import type { LucideIcon } from 'lucide-react'

interface EmptyStateProps {
  icon?: LucideIcon
  title: string
  description?: string
  className?: string
}

/**
 * Unified empty state component for consistent styling across all panels.
 * Uses the panel-empty-state class from _utilities.css.
 */
export function EmptyState({
  icon: Icon,
  title,
  description,
  className = '',
}: EmptyStateProps) {
  return (
    <div className={`panel-empty-state ${className}`.trim()}>
      <span className="empty-title">{title}</span>
      {description && (
        <span className="empty-description">{description}</span>
      )}
    </div>
  )
}
