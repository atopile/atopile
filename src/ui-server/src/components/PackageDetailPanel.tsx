import { useState, useEffect, useMemo, useRef } from 'react'
import {
  ArrowLeft, Package, Download, ExternalLink,
  CheckCircle, FileCode,
  Loader2, AlertCircle, Layers, Cuboid, ChevronDown, ChevronRight
} from 'lucide-react'
import type { PackageDetails } from '../types/build'
import MarkdownRenderer from './MarkdownRenderer'
import ModelViewer from './ModelViewer'
import KiCanvasEmbed from './KiCanvasEmbed'
import { API_URL } from '../api/config'

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
  onUninstall: () => void
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

function formatDate(dateStr?: string | null): string {
  if (!dateStr) return 'N/A'
  try {
    const date = new Date(dateStr)
    if (Number.isNaN(date.getTime())) return dateStr
    return date.toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  } catch {
    return dateStr
  }
}

function formatBytes(bytes?: number | null): string {
  if (!bytes) return 'N/A'
  const units = ['B', 'KB', 'MB', 'GB']
  let value = bytes
  let unitIndex = 0
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024
    unitIndex += 1
  }
  const rounded = value >= 10 ? Math.round(value) : Math.round(value * 10) / 10
  return `${rounded} ${units[unitIndex]}`
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
  onUninstall,
}: PackageDetailProps) {
  const [infoCollapsed, setInfoCollapsed] = useState(true)
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
  const installedFromList = typeof pkg.installed === 'boolean' ? pkg.installed : undefined
  const isInstalled = installedFromList ?? details?.installed ?? false
  const installedVersion = isInstalled ? (pkg.version || details?.installedVersion) : undefined
  const isUpdateAvailable = Boolean(
    isInstalled &&
    selectedVersion &&
    installedVersion &&
    selectedVersion !== installedVersion
  )
  const showUninstall = Boolean(isInstalled && !isUpdateAvailable)
  const packageTitle = pkg.fullName || pkg.name
  const releaseDate = sortedVersions.find(v => v.version === selectedVersion)?.releasedAt

  const selectedVersionInfo = sortedVersions.find(v => v.version === selectedVersion)
  const buildTargets = useMemo(() => {
    const targets = new Set<string>()
    details?.builds?.forEach(target => {
      if (typeof target === 'string') {
        targets.add(target)
      } else {
        targets.add(target.name)
      }
    })
    details?.layouts?.forEach(layout => targets.add(layout.buildName))
    details?.importStatements?.forEach(statement => targets.add(statement.buildName))
    details?.artifacts?.forEach(artifact => {
      if (artifact.buildName) targets.add(artifact.buildName)
    })
    return Array.from(targets)
  }, [details?.builds, details?.layouts, details?.importStatements, details?.artifacts])

  const [selectedBuildTarget, setSelectedBuildTarget] = useState<string>('')
  const [activeVisualTab, setActiveVisualTab] = useState<'3d' | 'layout'>('3d')
  const [buildDropdownOpen, setBuildDropdownOpen] = useState(false)
  const buildDropdownRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!buildTargets.length) {
      if (selectedBuildTarget) setSelectedBuildTarget('')
      return
    }
    if (!selectedBuildTarget || !buildTargets.includes(selectedBuildTarget)) {
      setSelectedBuildTarget(buildTargets[0])
    }
  }, [buildTargets, selectedBuildTarget])

  const layoutForTarget = details?.layouts?.find(layout => layout.buildName === selectedBuildTarget)
  const modelArtifact = useMemo(() => {
    if (!selectedBuildTarget) return null
    const expectedFilename = `${selectedBuildTarget}/${selectedBuildTarget}.pcba.glb`
    const artifacts = details?.artifacts || []
    return (
      artifacts.find(artifact => artifact.filename === expectedFilename) ||
      artifacts.find(artifact => artifact.buildName === selectedBuildTarget && artifact.filename.endsWith('.pcba.glb')) ||
      null
    )
  }, [details?.artifacts, selectedBuildTarget])

  const proxyAssetUrl = (url?: string | null) => {
    if (!url) return ''
    let filename = 'asset'
    try {
      const parsed = new URL(url)
      const parts = parsed.pathname.split('/')
      filename = parts[parts.length - 1] || filename
    } catch {
      // ignore
    }
    return `${API_URL}/api/packages/proxy/${encodeURIComponent(filename)}?url=${encodeURIComponent(url)}`
  }

  const authorLine = details?.authors?.length
    ? details.authors.map(author => author.name).join(', ')
    : 'N/A'

  useEffect(() => {
    if (!buildDropdownOpen) return
    const handleClickOutside = (event: MouseEvent) => {
      if (!buildDropdownRef.current) return
      if (!buildDropdownRef.current.contains(event.target as Node)) {
        setBuildDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [buildDropdownOpen])

  return (
    <div className="package-detail-panel">
      {/* Header */}
      <div className="detail-panel-header">
        <div className="detail-header-left">
          <div className="detail-header-left-stack">
            <button className="detail-back-btn" onClick={onClose} title="Back">
              <ArrowLeft size={18} />
            </button>
            <Package size={20} className="detail-package-icon" />
          </div>
          <div className="detail-header-info">
            <div className="detail-title-row">
              <h2 className="detail-package-name">{packageTitle}</h2>
            </div>
            <div className="detail-package-meta">
              <p className="detail-package-blurb">
                {description || 'No description available.'}
              </p>
            </div>
          </div>
        </div>
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
        {/* Install */}
        <section className="detail-section">
          <h3 className="detail-section-title">
            <Download size={14} />
            Install
          </h3>
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
              className={`detail-install-btn ${
                isUpdateAvailable ? 'update' : showUninstall ? 'uninstall' : 'install'
              } ${isInstalling ? 'installing' : ''}`}
              onClick={() =>
                showUninstall
                  ? onUninstall()
                  : onInstall(selectedVersion || details?.version || pkg.version || '')
              }
              disabled={isLoading || isInstalling}
            >
              {isInstalling ? (
                <>
                  <Loader2 size={14} className="animate-spin" />
                  {showUninstall ? 'Uninstalling...' : 'Installing...'}
                </>
              ) : (
                <>
                  <Download size={14} />
                  {isUpdateAvailable ? 'Update' : showUninstall ? 'Uninstall' : 'Install'}
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

          <div className="detail-install-meta">
            {isInstalled ? (
              <>
                <CheckCircle size={12} />
                Installed{installedVersion ? ` (v${installedVersion})` : ''}
              </>
            ) : (
              <span>Not installed</span>
            )}
          </div>
        </section>

        {/* Information */}
        <section className={`detail-section detail-section-collapsible ${infoCollapsed ? 'collapsed' : ''}`}>
          <div className="detail-section-header">
            <div className="detail-section-header-left">
              <button
                type="button"
                className="detail-collapse-toggle"
                onClick={() => setInfoCollapsed((prev) => !prev)}
                aria-expanded={!infoCollapsed}
                aria-label={infoCollapsed ? 'Expand information' : 'Collapse information'}
              >
                {infoCollapsed ? <ChevronRight size={12} /> : <ChevronDown size={12} />}
              </button>
              <h3 className="detail-section-title">
                <Package size={14} />
                Information
              </h3>
            </div>
            {(details?.homepage || pkg.homepage) && (
              <a
                href={details?.homepage || pkg.homepage}
                target="_blank"
                rel="noopener"
                className="detail-open-icon"
                title="Open in browser"
              >
                <ExternalLink size={12} />
              </a>
            )}
          </div>
          {!infoCollapsed && (
            <dl className="detail-info-list">
            {details?.publisher && (
              <div className="detail-info-row">
                <dt>Publisher</dt>
                <dd className="detail-info-value">{details.publisher}</dd>
              </div>
            )}
            <div className="detail-info-row">
              <dt>Published</dt>
              <dd className="detail-info-value">{formatDate(details?.createdAt)}</dd>
            </div>
            <div className="detail-info-row">
              <dt>Last updated</dt>
              <dd className="detail-info-value">{formatDate(details?.releasedAt)}</dd>
            </div>
            {sortedVersions.length > 0 && (
              <div className="detail-info-row">
                <dt>Latest version</dt>
                <dd className="detail-info-value">
                  <span className="detail-info-mono">v{latestAvailableVersion}</span>
                </dd>
              </div>
            )}
            {sortedVersions.length > 0 && (
              <div className="detail-info-row">
                <dt>Latest release</dt>
                <dd className="detail-info-value">{formatReleaseDate(releaseDate)}</dd>
              </div>
            )}
            <div className="detail-info-row">
              <dt>Authors</dt>
              <dd className="detail-info-value">{authorLine}</dd>
            </div>
            <div className="detail-info-row">
              <dt>License</dt>
              <dd className="detail-info-value">
                {details?.license || 'N/A'}
              </dd>
            </div>
            {details?.downloads !== undefined && (
              <div className="detail-info-row">
                <dt>Downloads</dt>
                <dd className="detail-info-value">
                  {formatDownloads(details.downloads)}
                </dd>
              </div>
            )}
            {details?.versionCount !== undefined && (
              <div className="detail-info-row">
                <dt>Versions</dt>
                <dd className="detail-info-value">{details.versionCount}</dd>
              </div>
            )}
            <div className="detail-info-row">
              <dt>ato version compatibility</dt>
              <dd className="detail-info-value">
                <span className="detail-info-mono">{selectedVersionInfo?.requiresAtopile || 'N/A'}</span>
              </dd>
            </div>
            <div className="detail-info-row">
              <dt>File size</dt>
              <dd className="detail-info-value">
                {formatBytes(selectedVersionInfo?.size)}
              </dd>
            </div>
            </dl>
          )}
        </section>

        {/* Visuals */}
        <section className="package-visual-section">
          <div className="package-visual-header">
            <div className="package-visual-tabs">
              <button
                className={`package-visual-tab ${activeVisualTab === '3d' ? 'active' : ''}`}
                onClick={() => setActiveVisualTab('3d')}
              >
                <Cuboid size={14} />
                3D Model
              </button>
              <button
                className={`package-visual-tab ${activeVisualTab === 'layout' ? 'active' : ''}`}
                onClick={() => setActiveVisualTab('layout')}
              >
                <Layers size={14} />
                Layout
              </button>
            </div>
            {buildTargets.length > 1 && (
              <div className="build-selector detail-target-dropdown" ref={buildDropdownRef}>
                <button
                  className={`selector-trigger ${buildDropdownOpen ? 'open' : ''}`}
                  onClick={() => setBuildDropdownOpen(!buildDropdownOpen)}
                >
                  <span className="selector-label">{selectedBuildTarget || 'Select build'}</span>
                  <ChevronDown className={`selector-chevron ${buildDropdownOpen ? 'rotated' : ''}`} />
                </button>
                {buildDropdownOpen && (
                  <div className="selector-dropdown">
                    <div className="selector-list">
                      {buildTargets.map(target => (
                        <div
                          key={target}
                          className={`selector-item ${target === selectedBuildTarget ? 'selected' : ''}`}
                          onClick={() => {
                            setSelectedBuildTarget(target)
                            setBuildDropdownOpen(false)
                          }}
                        >
                          <span className="selector-item-label">{target}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
          <div className="package-visual-content">
            {activeVisualTab === '3d' ? (
              selectedBuildTarget ? (
                modelArtifact ? (
                  <ModelViewer
                    key={modelArtifact.url}
                    src={proxyAssetUrl(modelArtifact.url)}
                    className="detail-visual-frame"
                  />
                ) : (
                  <div className="detail-visual-empty">
                    No 3D model found for "{selectedBuildTarget}".
                  </div>
                )
              ) : (
                <div className="detail-visual-empty">Select a build target to preview 3D.</div>
              )
            ) : selectedBuildTarget ? (
              layoutForTarget ? (
                <KiCanvasEmbed
                  key={layoutForTarget.url}
                  src={proxyAssetUrl(layoutForTarget.url)}
                  className="detail-visual-frame"
                />
              ) : (
                <div className="detail-visual-empty">
                  No layout found for "{selectedBuildTarget}".
                </div>
              )
            ) : (
              <div className="detail-visual-empty">Select a build target to preview layout.</div>
            )}
          </div>
        </section>

        {/* Readme */}
        <section className="detail-section">
          <h3 className="detail-section-title">
            <FileCode size={14} />
            Readme
          </h3>
          {details?.readme ? (
            <MarkdownRenderer content={details.readme} />
          ) : (
            <div className="detail-empty">
              Readme not available.
            </div>
          )}
        </section>

      </div>
    </div>
  )
}
