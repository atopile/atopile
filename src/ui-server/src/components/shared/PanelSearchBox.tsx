import { useRef, useEffect, useMemo } from 'react'
import { Search, X, Regex } from 'lucide-react'
import { isValidRegex } from '../../utils/searchUtils'
import './PanelSearchBox.css'

interface PanelSearchBoxProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  autoFocus?: boolean
  /** Enable regex mode support - shows toggle button */
  enableRegex?: boolean
  /** Current regex mode state */
  isRegex?: boolean
  /** Callback when regex mode is toggled */
  onRegexToggle?: (isRegex: boolean) => void
}

export function PanelSearchBox({
  value,
  onChange,
  placeholder = 'Search...',
  autoFocus = false,
  enableRegex = false,
  isRegex = false,
  onRegexToggle,
}: PanelSearchBoxProps) {
  const inputRef = useRef<HTMLInputElement>(null)

  // Validate regex pattern when in regex mode
  const regexValidation = useMemo(() => {
    if (!enableRegex || !isRegex || !value) {
      return { valid: true }
    }
    return isValidRegex(value)
  }, [enableRegex, isRegex, value])

  // Auto-focus when autoFocus prop becomes true
  useEffect(() => {
    if (autoFocus && inputRef.current) {
      // Small delay to ensure the panel is fully rendered
      const timer = setTimeout(() => {
        inputRef.current?.focus()
      }, 50)
      return () => clearTimeout(timer)
    }
  }, [autoFocus])

  const handleRegexToggle = () => {
    if (onRegexToggle) {
      onRegexToggle(!isRegex)
    }
  }

  const showRegexError = enableRegex && isRegex && !regexValidation.valid

  return (
    <div className={`panel-search-box ${showRegexError ? 'has-error' : ''}`}>
      <Search size={14} className="panel-search-icon" />
      <input
        ref={inputRef}
        type="text"
        placeholder={isRegex ? 'Regex pattern...' : placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        aria-invalid={showRegexError}
      />
      {enableRegex && (
        <button
          className={`panel-search-regex ${isRegex ? 'active' : ''}`}
          onClick={handleRegexToggle}
          aria-label={isRegex ? 'Disable regex mode' : 'Enable regex mode'}
          title={isRegex ? 'Regex mode (click to disable)' : 'Enable regex mode'}
        >
          <Regex size={12} />
        </button>
      )}
      {value && (
        <button
          className="panel-search-clear"
          onClick={() => onChange('')}
          aria-label="Clear search"
        >
          <X size={12} />
        </button>
      )}
      {showRegexError && (
        <span className="panel-search-error" title={regexValidation.error}>
          Invalid regex
        </span>
      )}
    </div>
  )
}
