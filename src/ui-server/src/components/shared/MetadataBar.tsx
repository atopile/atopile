/**
 * MetadataBar - Displays package metadata (downloads, versions, license).
 */

import { Download, ExternalLink, Loader2 } from 'lucide-react'
import { formatDownloads } from '../../utils/packageUtils'
import './MetadataBar.css'

interface MetadataBarProps {
  /** Number of downloads */
  downloads?: number | null
  /** Number of versions available */
  versionCount?: number
  /** License type (e.g., "MIT") */
  license?: string | null
  /** Homepage URL */
  homepage?: string | null
  /** Whether metadata is loading */
  isLoading?: boolean
}

export function MetadataBar({
  downloads,
  versionCount,
  license,
  homepage,
  isLoading
}: MetadataBarProps) {
  // If loading, show placeholder bar with spinners
  if (isLoading) {
    return (
      <div className="metadata-bar">
        <span className="meta-item loading">
          <Loader2 size={11} className="spin" />
        </span>
        <span className="meta-item loading">
          <Loader2 size={11} className="spin" />
        </span>
        <span className="meta-item loading">
          <Loader2 size={11} className="spin" />
        </span>
      </div>
    )
  }

  const hasContent = (downloads && downloads > 0) || (versionCount && versionCount > 0) || license || homepage

  if (!hasContent) return null

  return (
    <div className="metadata-bar">
      {downloads !== undefined && downloads !== null && downloads > 0 && (
        <span className="meta-item">
          <Download size={11} />
          {formatDownloads(downloads)}
        </span>
      )}
      {versionCount !== undefined && versionCount > 0 && (
        <span className="meta-item">{versionCount} versions</span>
      )}
      {license && (
        <span className="meta-item">{license}</span>
      )}
      {homepage && (
        <a
          href={homepage}
          className="meta-item link"
          target="_blank"
          rel="noopener noreferrer"
          onClick={(e) => e.stopPropagation()}
        >
          <ExternalLink size={11} />
          Homepage
        </a>
      )}
    </div>
  )
}
