import { forwardRef, useState, useCallback, type InputHTMLAttributes } from 'react'
import { Search, X, Regex, CaseSensitive } from 'lucide-react'
import { isValidRegex } from '../../utils/searchUtils'
import './SearchBar.css'

/* ---- SearchBar (basic) ---- */

export interface SearchBarProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'onChange' | 'value' | 'type'> {
  value: string
  onChange: (value: string) => void
}

export const SearchBar = forwardRef<HTMLInputElement, SearchBarProps>(
  ({ value, onChange, placeholder = 'Search...', className = '', ...props }, ref) => {
    return (
      <div className={`search-bar ${className}`.trim()}>
        <Search size={14} className="search-bar-icon" />
        <input
          ref={ref}
          type="text"
          className="search-bar-input"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          {...props}
        />
        {value && (
          <button
            type="button"
            className="search-bar-clear"
            onClick={() => onChange('')}
            aria-label="Clear search"
          >
            <X size={12} />
          </button>
        )}
      </div>
    )
  }
)
SearchBar.displayName = 'SearchBar'

/* ---- RegexSearchBar ---- */

export interface RegexSearchBarProps extends Omit<SearchBarProps, 'onChange'> {
  onChange: (value: string) => void
  isRegex: boolean
  onRegexChange: (isRegex: boolean) => void
  caseSensitive: boolean
  onCaseSensitiveChange: (caseSensitive: boolean) => void
}

export const RegexSearchBar = forwardRef<HTMLInputElement, RegexSearchBarProps>(
  ({ value, onChange, isRegex, onRegexChange, caseSensitive, onCaseSensitiveChange, placeholder = 'Search...', className = '', ...props }, ref) => {
    const [regexError, setRegexError] = useState<string | undefined>()

    const handleChange = useCallback(
      (val: string) => {
        onChange(val)
        if (isRegex && val) {
          const { valid, error } = isValidRegex(val)
          setRegexError(valid ? undefined : error)
        } else {
          setRegexError(undefined)
        }
      },
      [onChange, isRegex]
    )

    const handleToggleRegex = useCallback(() => {
      const next = !isRegex
      onRegexChange(next)
      if (next && value) {
        const { valid, error } = isValidRegex(value)
        setRegexError(valid ? undefined : error)
      } else {
        setRegexError(undefined)
      }
    }, [isRegex, onRegexChange, value])

    const hasError = isRegex && !!regexError

    return (
      <div className={`search-bar ${hasError ? 'search-bar-invalid' : ''} ${className}`.trim()}>
        <Search size={14} className="search-bar-icon" />
        <input
          ref={ref}
          type="text"
          className="search-bar-input"
          value={value}
          onChange={(e) => handleChange(e.target.value)}
          placeholder={isRegex ? 'Regex pattern...' : placeholder}
          aria-invalid={hasError || undefined}
          {...props}
        />
        {value && (
          <button
            type="button"
            className="search-bar-clear"
            onClick={() => handleChange('')}
            aria-label="Clear search"
          >
            <X size={12} />
          </button>
        )}
        <button
          type="button"
          className={`search-bar-toggle ${caseSensitive ? 'active' : ''}`}
          onClick={() => onCaseSensitiveChange(!caseSensitive)}
          aria-label="Toggle case sensitivity"
          aria-pressed={caseSensitive}
          title={caseSensitive ? 'Case sensitive' : 'Case insensitive'}
        >
          <CaseSensitive size={14} />
        </button>
        <button
          type="button"
          className={`search-bar-toggle ${isRegex ? 'active' : ''}`}
          onClick={handleToggleRegex}
          aria-label="Toggle regex"
          aria-pressed={isRegex}
          title={isRegex ? 'Regex enabled' : 'Enable regex'}
        >
          <Regex size={14} />
        </button>
        {hasError && <span className="search-bar-error">{regexError}</span>}
      </div>
    )
  }
)
RegexSearchBar.displayName = 'RegexSearchBar'
