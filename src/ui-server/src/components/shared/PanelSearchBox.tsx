import { useRef, useEffect } from 'react'
import { Search, X } from 'lucide-react'
import './PanelSearchBox.css'

interface PanelSearchBoxProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  autoFocus?: boolean
}

export function PanelSearchBox({
  value,
  onChange,
  placeholder = 'Search...',
  autoFocus = false,
}: PanelSearchBoxProps) {
  const inputRef = useRef<HTMLInputElement>(null)

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

  return (
    <div className="panel-search-box">
      <Search size={14} className="panel-search-icon" />
      <input
        ref={inputRef}
        type="text"
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
      {value && (
        <button
          className="panel-search-clear"
          onClick={() => onChange('')}
          aria-label="Clear search"
        >
          <X size={12} />
        </button>
      )}
    </div>
  )
}
