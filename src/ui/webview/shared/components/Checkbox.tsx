import { useId } from 'react'
import { Check } from 'lucide-react'
import './Checkbox.css'

export interface CheckboxProps {
  /** Controlled checked state */
  checked?: boolean
  /** Change handler — receives the new checked value */
  onCheckedChange?: (checked: boolean) => void
  /** Accessible name when no visible label is associated */
  'aria-label'?: string
  /** HTML id (auto-generated if omitted) */
  id?: string
  /** HTML name */
  name?: string
  /** Disabled state */
  disabled?: boolean
  /** Additional class name on the root element */
  className?: string
}

export function Checkbox({
  checked = false,
  onCheckedChange,
  id: idProp,
  name,
  disabled = false,
  className = '',
  ...rest
}: CheckboxProps) {
  const autoId = useId()
  const id = idProp ?? autoId

  return (
    <label className={`checkbox ${className}`.trim()}>
      <input
        id={id}
        name={name}
        type="checkbox"
        className="checkbox-input"
        checked={checked}
        disabled={disabled}
        onChange={(e) => onCheckedChange?.(e.target.checked)}
        aria-label={rest['aria-label']}
      />
      <span className="checkbox-indicator">
        <Check size={12} className="checkbox-icon" />
      </span>
    </label>
  )
}
