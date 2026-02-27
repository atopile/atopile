import { Spinner, type SpinnerProps } from './Spinner'
import './CenteredSpinner.css'

/**
 * Full-height centered spinner for panel loading states.
 */
export function CenteredSpinner({ size = 14, ...rest }: SpinnerProps) {
  return (
    <div className="centered-spinner">
      <Spinner size={size} {...rest} />
    </div>
  )
}
