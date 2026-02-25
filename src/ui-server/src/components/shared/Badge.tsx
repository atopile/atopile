import { forwardRef, type HTMLAttributes, type AnchorHTMLAttributes } from 'react'
import './Badge.css'

type BadgeVariant = 'default' | 'secondary' | 'destructive' | 'outline' | 'success' | 'warning' | 'info'

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant
}

export const Badge = forwardRef<HTMLSpanElement, BadgeProps>(
  ({ variant = 'default', className = '', children, ...props }, ref) => {
    const cls = `badge badge-${variant} ${className}`.trim()
    return (
      <span ref={ref} className={cls} {...props}>
        {children}
      </span>
    )
  }
)
Badge.displayName = 'Badge'

/* ---- BadgeAsLink ---- */

export interface BadgeAsLinkProps extends AnchorHTMLAttributes<HTMLAnchorElement> {
  variant?: BadgeVariant
}

export const BadgeAsLink = forwardRef<HTMLAnchorElement, BadgeAsLinkProps>(
  ({ variant = 'default', className = '', children, ...props }, ref) => {
    const cls = `badge badge-as-link badge-${variant} ${className}`.trim()
    return (
      <a ref={ref} className={cls} {...props}>
        {children}
      </a>
    )
  }
)
BadgeAsLink.displayName = 'BadgeAsLink'
