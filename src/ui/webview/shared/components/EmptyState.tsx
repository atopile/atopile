import type { CSSProperties, ReactNode } from 'react'

interface EmptyStateProps {
  title: string
  description?: string
  icon?: ReactNode
  children?: ReactNode
  style?: CSSProperties
}

const containerStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  height: '100%',
  gap: 'var(--spacing-sm)',
  color: 'var(--text-muted)',
}

const iconStyle: CSSProperties = {
  opacity: 0.5,
}

const titleStyle: CSSProperties = {
  fontSize: 'var(--font-size-sm)',
}

const descriptionStyle: CSSProperties = {
  fontSize: 'var(--font-size-xs)',
  opacity: 0.7,
}

export function EmptyState({
  title,
  description,
  icon,
  children,
  style,
}: EmptyStateProps) {
  return (
    <div style={{ ...containerStyle, ...style }}>
      {icon && <div style={iconStyle}>{icon}</div>}
      <span style={titleStyle}>{title}</span>
      {description && (
        <span style={descriptionStyle}>{description}</span>
      )}
      {children}
    </div>
  )
}
