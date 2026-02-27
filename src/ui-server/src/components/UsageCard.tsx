/**
 * UsageCard - Displays import and usage snippets in a collapsible card.
 */

import { useState } from 'react'
import { ChevronDown, Code } from 'lucide-react'
import { CopyableCodeBlock } from './shared/CopyableCodeBlock'
import './UsageCard.css'

interface UsageCardProps {
  importCode: string
  usageCode: string
  onOpenUsage?: () => void
}

export function UsageCard({ importCode, usageCode, onOpenUsage }: UsageCardProps) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="usage-card" onClick={(e) => e.stopPropagation()}>
      <div
        className="usage-card-header"
        onClick={(e) => {
          e.stopPropagation()
          setExpanded(!expanded)
        }}
      >
        <span className="usage-card-expand">
          <ChevronDown
            size={12}
            className={`expand-icon ${expanded ? 'expanded' : ''}`}
          />
        </span>
        <Code size={14} className="usage-card-icon" />
        <span className="usage-card-title">Usage</span>
      </div>

      {expanded && (
        <div className="usage-card-content">
          <CopyableCodeBlock
            code={importCode}
            label="Import"
            highlightAto={true}
          />
          <CopyableCodeBlock
            code={usageCode}
            label="Usage"
            highlightAto={true}
            onOpen={onOpenUsage}
          />
        </div>
      )}
    </div>
  )
}
