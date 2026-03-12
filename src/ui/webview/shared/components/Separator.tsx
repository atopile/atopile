import { forwardRef, type HTMLAttributes } from 'react'
import './Separator.css'

export interface SeparatorProps extends HTMLAttributes<HTMLDivElement> {
  /** Orientation of the divider (default "horizontal") */
  orientation?: 'horizontal' | 'vertical'
}

export const Separator = forwardRef<HTMLDivElement, SeparatorProps>(
  ({ orientation = 'horizontal', className = '', ...props }, ref) => (
    <div
      ref={ref}
      role="separator"
      aria-orientation={orientation}
      className={`separator separator-${orientation} ${className}`.trim()}
      {...props}
    />
  )
)
Separator.displayName = 'Separator'
