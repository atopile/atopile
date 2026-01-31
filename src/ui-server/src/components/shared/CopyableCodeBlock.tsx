/**
 * CopyableCodeBlock - Reusable code display component with copy and open buttons.
 * Used in ProjectCard and DependencyCard for import/usage examples.
 */

import { useState } from 'react'
import { Copy, Check, FileCode } from 'lucide-react'
import { highlightAtoCode } from '../../utils/codeHighlight'
import './CopyableCodeBlock.css'

interface CopyableCodeBlockProps {
  /** The code to display */
  code: string
  /** Label shown in the header (e.g., "Import", "Usage") */
  label: string
  /** Optional callback when "open" button is clicked */
  onOpen?: () => void
  /** Whether to apply ato syntax highlighting */
  highlightAto?: boolean
}

export function CopyableCodeBlock({
  code,
  label,
  onOpen,
  highlightAto = false
}: CopyableCodeBlockProps) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async (e: React.MouseEvent) => {
    e.stopPropagation()
    try {
      await navigator.clipboard.writeText(code)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (error) {
      console.warn('Failed to copy', error)
    }
  }

  return (
    <div className="copyable-code">
      <div className="copyable-code-header">
        <span>{label}</span>
        <div className="actions">
          <button
            className={`copy-btn ${copied ? 'copied' : ''}`}
            onClick={handleCopy}
            title={copied ? 'Copied!' : 'Copy to clipboard'}
          >
            {copied ? <Check size={12} /> : <Copy size={12} />}
          </button>
          {onOpen && (
            <button
              className="open-btn"
              onClick={(e) => {
                e.stopPropagation()
                onOpen()
              }}
              title="Open in editor"
            >
              <FileCode size={12} />
            </button>
          )}
        </div>
      </div>
      <pre className="copyable-code-content">
        {highlightAto ? highlightAtoCode(code) : code}
      </pre>
    </div>
  )
}
