import { useState, useEffect } from 'react'
import {
  X, Package, Download, Home, Globe, ExternalLink,
  CheckCircle, Tag, Calendar, FileCode, Play,
  Loader2, AlertCircle, TrendingUp, History, Scale
} from 'lucide-react'
import type { PackageDetails } from '../types/build'

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
  error: string | null
  onClose: () => void
  onInstall: (version: string) => void
  onBuild: (entry?: string) => void
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

export function PackageDetailPanel({
  package: pkg,
  packageDetails,
  isLoading,
  error,
  onClose,
  onInstall,
  onBuild
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

  const [selectedVersion, setSelectedVersion] = useState(details?.version || pkg.version || '')

  // Update selected version when details load
  useEffect(() => {
    if (details?.version) {
      setSelectedVersion(details.version)
    }
  }, [details?.version])

  // Get description from details or package
  const description = details?.description || details?.summary || pkg.description
  const isInstalled = details?.installed ?? pkg.installed
  const installedVersion = details?.installedVersion || pkg.version

  return (
    <div className="package-detail-panel">
      {/* Header */}
      <div className="detail-panel-header">
        <div className="detail-header-left">
          <Package size={20} className="detail-package-icon" />
          <div className="detail-header-info">
            <h2 className="detail-package-name">{pkg.fullName}</h2>
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

        {/* Package Stats (from registry) */}
        {details && !isLoading && (
          <section className="detail-section detail-stats">
            <div className="detail-stats-row">
              <div className="detail-stat">
                <Download size={14} />
                <span>{formatDownloads(details.downloads)} downloads</span>
              </div>
              {details.downloadsThisWeek != null && (
                <div className="detail-stat">
                  <TrendingUp size={14} />
                  <span>{formatDownloads(details.downloadsThisWeek)}/week</span>
                </div>
              )}
              <div className="detail-stat">
                <History size={14} />
                <span>{details.versionCount || 0} releases</span>
              </div>
              {details.license && (
                <div className="detail-stat">
                  <Scale size={14} />
                  <span>{details.license}</span>
                </div>
              )}
            </div>
          </section>
        )}

        {/* Stats placeholder while loading */}
        {isLoading && (
          <section className="detail-section detail-stats">
            <div className="detail-stats-row">
              <div className="detail-stat loading-placeholder">Loading stats...</div>
            </div>
          </section>
        )}

        {/* Actions */}
        <section className="detail-section detail-actions">
          <div className="detail-install-row">
            {/* Version dropdown */}
            {availableVersions.length > 0 ? (
              <select
                className="detail-version-select"
                value={selectedVersion}
                onChange={(e) => setSelectedVersion(e.target.value)}
              >
                {availableVersions.map((v, idx) => (
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
              className={`detail-install-btn ${isInstalled ? 'update' : 'install'}`}
              onClick={() => onInstall(selectedVersion || details?.version || pkg.version || '')}
              disabled={isLoading}
            >
              <Download size={14} />
              {isInstalled ? 'Update' : 'Install'}
            </button>
            <button
              className="detail-build-btn"
              onClick={() => onBuild()}
              title="Build this package (installs if needed)"
              disabled={isLoading}
            >
              <Play size={14} />
              Build
            </button>
          </div>

          {/* Release date info */}
          {availableVersions.length > 0 && (
            <div className="detail-version-info">
              <Calendar size={12} />
              Released: {formatReleaseDate(availableVersions.find(v => v.version === selectedVersion)?.releasedAt)}
            </div>
          )}
        </section>

        {/* Links */}
        {(pkg.homepage || pkg.repository) && (
          <section className="detail-section detail-links">
            {pkg.homepage && (
              <a href={pkg.homepage} className="detail-link" target="_blank" rel="noopener">
                <Home size={14} />
                Homepage
                <ExternalLink size={10} />
              </a>
            )}
            {pkg.repository && (
              <a href={pkg.repository} className="detail-link" target="_blank" rel="noopener">
                <Globe size={14} />
                Repository
                <ExternalLink size={10} />
              </a>
            )}
          </section>
        )}

        {/* Exports - placeholder until backend provides symbol introspection */}
        <section className="detail-section">
          <h3 className="detail-section-title">
            <FileCode size={14} />
            Exported Symbols
          </h3>
          <p className="muted">Symbol introspection coming soon</p>
        </section>

        {/* Usage Example */}
        <section className="detail-section">
          <h3 className="detail-section-title">
            <FileCode size={14} />
            Usage Example
          </h3>
          <pre className="detail-code-block">
{`from "${pkg.fullName}/${pkg.name}.ato" import RP2040

module MyBoard:
    mcu = new RP2040
    
    # Connect interfaces
    power ~ mcu.power
    i2c ~ mcu.i2c`}
          </pre>
        </section>
      </div>
    </div>
  )
}
