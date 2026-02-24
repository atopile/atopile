import { forwardRef, type HTMLAttributes, type ReactNode } from 'react'
import { Info, CheckCircle2, AlertTriangle, AlertCircle, CircleAlert } from 'lucide-react'
import './Alert.css'

type AlertVariant = 'default' | 'info' | 'success' | 'warning' | 'destructive'

const variantIcons: Record<AlertVariant, ReactNode> = {
  default: <CircleAlert size={16} />,
  info: <Info size={16} />,
  success: <CheckCircle2 size={16} />,
  warning: <AlertTriangle size={16} />,
  destructive: <AlertCircle size={16} />,
}

/* ---- Alert ---- */

export interface AlertProps extends HTMLAttributes<HTMLDivElement> {
  variant?: AlertVariant
  /** Override the default icon */
  icon?: ReactNode
}

export const Alert = forwardRef<HTMLDivElement, AlertProps>(
  ({ variant = 'default', icon, className = '', children, ...props }, ref) => (
    <div
      ref={ref}
      role="alert"
      className={`alert alert-${variant} ${className}`.trim()}
      {...props}
    >
      <span className="alert-icon">{icon ?? variantIcons[variant]}</span>
      <div className="alert-body">{children}</div>
    </div>
  )
)
Alert.displayName = 'Alert'

/* ---- AlertTitle ---- */

export const AlertTitle = forwardRef<HTMLHeadingElement, HTMLAttributes<HTMLHeadingElement>>(
  ({ className = '', ...props }, ref) => (
    <h5 ref={ref} className={`alert-title ${className}`.trim()} {...props} />
  )
)
AlertTitle.displayName = 'AlertTitle'

/* ---- AlertDescription ---- */

export const AlertDescription = forwardRef<HTMLParagraphElement, HTMLAttributes<HTMLParagraphElement>>(
  ({ className = '', ...props }, ref) => (
    <p ref={ref} className={`alert-description ${className}`.trim()} {...props} />
  )
)
AlertDescription.displayName = 'AlertDescription'
