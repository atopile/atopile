import { Loader2 } from 'lucide-react'
import './Spinner.css'

export interface SpinnerProps extends React.SVGAttributes<SVGSVGElement> {
  /** Icon size in px (default 14) */
  size?: number
  /** Additional class name */
  className?: string
}

export function Spinner({ size = 14, className = '', ...rest }: SpinnerProps) {
  return (
    <Loader2
      size={size}
      role="status"
      aria-label="Loading"
      className={`spinner ${className}`.trim()}
      {...rest}
    />
  )
}
