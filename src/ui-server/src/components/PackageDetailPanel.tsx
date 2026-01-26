import { useState, useEffect } from 'react'
import {
  X, Package, Download, ExternalLink,
  CheckCircle, Tag, Calendar, FileCode,
  Loader2, AlertCircle, Globe
} from 'lucide-react'
import type { PackageDetails } from '../types/build'
import { CopyableCodeBlock } from './shared'

interface PackageDetailProps {
  package: {
    name: string
    fullName: string
    version?: string
    description?: string
    installed?: boolean
    availableVersions?: { version: string; released: string }[]
    homepage?: string
    repository?: string
  }
  packageDetails: PackageDetails | null
  isLoading: boolean
  isInstalling: boolean
  installError: string | null
  error: string | null
  onClose: () => void
  onInstall: (version: string) => void
  onBuild?: (entry?: string) => void  // Optional, no longer used in UI
}

// Format download count for display (e.g., 12847 -> "12.8k")
function formatDownloads(count: number | null | undefined): string {
  if (count == null) return '0'
  if (count >= 1000000) {
    return (count / 1000000).toFixed(1).replace(/\.0$/, '') + 'M'
  }
  if (count >= 1000) {
    return (count / 1000).toFixed(1).replace(/\.0$/, '') + 'k'
  }
  return count.toString()
}

// Format release date for display
function formatReleaseDate(dateStr: string | null | undefined): string {
  if (!dateStr) return 'Unknown'
  try {
    const date = new Date(dateStr)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

    if (diffDays < 1) return 'Today'
    if (diffDays === 1) return 'Yesterday'
    if (diffDays < 7) return `${diffDays} days ago`
    if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`
    if (diffDays < 365) return `${Math.floor(diffDays / 30)} months ago`
    return date.toLocaleDateString()
  } catch {
    return dateStr
  }
}

function compareVersionsDesc(a: string, b: string): number {
  const aParts = a.split('.').map(part => parseInt(part, 10));
  const bParts = b.split('.').map(part => parseInt(part, 10));
  const maxLen = Math.max(aParts.length, bParts.length);
  for (let i = 0; i < maxLen; i += 1) {
    const aVal = Number.isFinite(aParts[i]) ? aParts[i] : 0;
    const bVal = Number.isFinite(bParts[i]) ? bParts[i] : 0;
    if (aVal !== bVal) return bVal - aVal;
  }
  return b.localeCompare(a);
}

export function PackageDetailPanel({
  package: pkg,
  packageDetails,
  isLoading,
  isInstalling,
  installError,
  error,
  onClose,
  onInstall,
}: PackageDetailProps) {
  // Use details from API if available, fallback to basic package info
  const details = packageDetails

  // Get available versions from details or package
  const availableVersions = details?.versions || pkg.availableVersions?.map(v => ({
    version: v.version,
    releasedAt: v.released,
    requiresAtopile: undefined,
    size: undefined
  })) || []

  const sortedVersions = [...availableVersions].sort((a, b) => {
    if (a.releasedAt && b.releasedAt) {
      return new Date(b.releasedAt).getTime() - new Date(a.releasedAt).getTime()
    }
    return compareVersionsDesc(a.version, b.version)
  })

  const latestAvailableVersion = sortedVersions[0]?.version || ''
  const [selectedVersion, setSelectedVersion] = useState(
    latestAvailableVersion || details?.version || pkg.version || ''
  )

  // Update selected version when details load
  useEffect(() => {
    if (!sortedVersions.length) return
    if (!selectedVersion || selectedVersion === details?.installedVersion || selectedVersion === pkg.version) {
      setSelectedVersion(sortedVersions[0]?.version || selectedVersion)
    }
  }, [sortedVersions, details?.installedVersion, pkg.version, selectedVersion])

  // Get description from details or package
  const description = details?.description || details?.summary || pkg.description
  const isInstalled = details?.installed ?? pkg.installed
  const installedVersion = details?.installedVersion || pkg.version
  const usageContent = details?.usageContent?.trim()

  return (
    <div className="package-detail-panel">
      {/* Header */}
      <div className="detail-panel-header">
        <div className="detail-header-left">
          <Package size={20} className="detail-package-icon" />
          <div className="detail-header-info">
            <h2 className="detail-package-name">{pkg.name}</h2>
            <div className="detail-package-meta">
              {(details?.version || pkg.version) && (
                <span className="detail-version">
                  <Tag size={12} />
                  v{details?.version || pkg.version}
                </span>
              )}
              {isInstalled && (
                <span className="detail-installed">
                  <CheckCircle size={12} />
                  Installed{installedVersion ? ` (v${installedVersion})` : ''}
                </span>
              )}
            </div>
          </div>
        </div>
        <button className="detail-close-btn" onClick={onClose}>
          <X size={18} />
        </button>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="detail-panel-loading">
          <Loader2 size={24} className="spin" />
          <span>Loading package details...</span>
        </div>
      )}

      {/* Error State */}
      {error && !isLoading && (
        <div className="detail-panel-error">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      {/* Content */}
      <div className="detail-panel-content">
        {/* Description */}
        {description && (
          <section className="detail-section">
            <p className="detail-description">{description}</p>
          </section>
        )}


        {/* Actions */}
        <section className="detail-section detail-actions">
          <div className="detail-install-row">
            {/* Version dropdown */}
            {sortedVersions.length > 0 ? (
              <select
                className="detail-version-select"
                value={selectedVersion}
                onChange={(e) => setSelectedVersion(e.target.value)}
              >
                {sortedVersions.map((v, idx) => (
                  <option key={v.version} value={v.version}>
                    v{v.version}{idx === 0 ? ' (latest)' : ''}
                  </option>
                ))}
              </select>
            ) : isLoading ? (
              <select className="detail-version-select" disabled>
                <option>Loading versions...</option>
              </select>
            ) : (
              <select className="detail-version-select" disabled>
                <option>v{pkg.version || 'unknown'}</option>
              </select>
            )}

            <button
              className={`detail-install-btn ${isInstalled ? 'update' : 'install'} ${isInstalling ? 'installing' : ''}`}
              onClick={() => onInstall(selectedVersion || details?.version || pkg.version || '')}
              disabled={isLoading || isInstalling}
            >
              {isInstalling ? (
                <>
                  <Loader2 size={14} className="animate-spin" />
                  Installing...
                </>
              ) : (
                <>
                  <Download size={14} />
                  {isInstalled ? 'Update' : 'Install'}
                </>
              )}
            </button>
          </div>

          {/* Install error message */}
          {installError && (
            <div className="detail-install-error">
              <AlertCircle size={12} />
              <span>{installError}</span>
            </div>
          )}

          {/* Release date info */}
          {sortedVersions.length > 0 && (
            <div className="detail-version-info">
              <Calendar size={12} />
              Released: {formatReleaseDate(sortedVersions.find(v => v.version === selectedVersion)?.releasedAt)}
            </div>
          )}
        </section>

        {/* Usage Example - code view panel */}
        <section className="detail-section">
          <h3 className="detail-section-title">
            <FileCode size={14} />
            Usage
          </h3>
          <div className="detail-usage-code">
            {usageContent ? (
              <CopyableCodeBlock
                label="usage.ato"
                code={usageContent}
                highlightAto
              />
            ) : (
              <div className="detail-usage-empty">
                {isInstalled ? 'No usage.ato found for this package.' : 'Available after installing.'}
              </div>
            )}
          </div>
        </section>
      </div>

      {/* Footer Bar - Package metadata and actions */}
      <div className="detail-panel-footer">
        <div className="detail-footer-stats">
          {details?.publisher && (
            <span className="footer-stat">{details.publisher}</span>
          )}
          {details && (
            <span className="footer-stat">
              <Download size={12} />
              {formatDownloads(details.downloads)}
            </span>
          )}
          {details?.license && (
            <span className="footer-stat">{details.license}</span>
          )}
        </div>
        {pkg.homepage && (
          <a
            href={pkg.homepage}
            className="footer-browser-btn"
            target="_blank"
            rel="noopener"
            title="Open in browser"
          >
            <Globe size={14} />
            <span>Open</span>
            <ExternalLink size={10} />
          </a>
        )}
      </div>
    </div>
  )
}
