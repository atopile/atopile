/**
 * VersionSelector - Dropdown for selecting package versions.
 * Used in ProjectCard and DependencyCard for version selection.
 */

import { useState, useEffect, useRef } from 'react'
import { ChevronDown, Check } from 'lucide-react'
import './VersionSelector.css'

interface VersionSelectorProps {
  /** List of available versions */
  versions: string[]
  /** Currently selected version */
  selectedVersion: string
  /** Callback when version changes */
  onVersionChange: (version: string) => void
  /** The latest version (for "latest" tag) */
  latestVersion?: string
  /** If true, shows as static text instead of dropdown */
  readOnly?: boolean
}

export function VersionSelector({
  versions,
  selectedVersion,
  onVersionChange,
  latestVersion,
  readOnly = false
}: VersionSelectorProps) {
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const validVersions = versions.filter(v => v && v !== 'unknown')
  if (validVersions.length === 0) return null

  const validSelectedVersion = selectedVersion && selectedVersion !== 'unknown' ? selectedVersion : null
  const displayVersion = validSelectedVersion || validVersions[0] || ''

  // Read-only mode - just show the version
  if (readOnly) {
    return (
      <span className="version-display" title={`Version ${displayVersion}`}>
        {displayVersion}
      </span>
    )
  }

  return (
    <div className="version-selector" ref={dropdownRef}>
      <button
        className="version-selector-btn"
        onClick={(e) => {
          e.stopPropagation()
          setIsOpen(!isOpen)
        }}
        title="Select version"
      >
        <span className="version-selector-value">{displayVersion}</span>
        <ChevronDown size={10} />
      </button>
      {isOpen && (
        <div className="version-selector-menu">
          {validVersions.map((v) => (
            <button
              key={v}
              className={`version-option ${v === selectedVersion ? 'selected' : ''}`}
              onClick={(e) => {
                e.stopPropagation()
                onVersionChange(v)
                setIsOpen(false)
              }}
            >
              <span>{v}</span>
              {v === latestVersion && <span className="latest-tag">latest</span>}
              {v === selectedVersion && <Check size={12} className="selected-check" />}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
