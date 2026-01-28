import { useEffect, useMemo, useState } from 'react'
import { ArrowLeft, Cpu, ExternalLink, Loader2, CheckCircle, AlertCircle, Download } from 'lucide-react'
import type { PartSearchItem } from '../types/build'
import type { SelectedPart } from './sidebar-modules'
import { api } from '../api/client'
import './PartsDetailPanel.css'

interface PartsDetailPanelProps {
  part: SelectedPart
  projectRoot: string | null
  onClose: () => void
}

function formatCurrency(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return '-'
  return `$${value.toFixed(4)}`
}

function formatStock(stock: number | null | undefined): string {
  if (stock == null) return '-'
  if (stock <= 0) return 'Out of stock'
  return stock.toLocaleString()
}

export function PartsDetailPanel({
  part,
  projectRoot,
  onClose,
}: PartsDetailPanelProps) {
  const [details, setDetails] = useState<PartSearchItem | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isInstalling, setIsInstalling] = useState(false)
  const [installError, setInstallError] = useState<string | null>(null)
  const [installSuccess, setInstallSuccess] = useState(false)
  const [isUninstalling, setIsUninstalling] = useState(false)
  const [uninstallError, setUninstallError] = useState<string | null>(null)
  const [uninstallSuccess, setUninstallSuccess] = useState(false)

  useEffect(() => {
    let active = true
    setIsLoading(true)
    setError(null)
    setDetails(null)
    api.parts.details(part.lcsc)
      .then((response) => {
        if (!active) return
        setDetails(response.part || null)
      })
      .catch((err) => {
        if (!active) return
        setError(err instanceof Error ? err.message : 'Failed to load part details')
      })
      .finally(() => {
        if (!active) return
        setIsLoading(false)
      })

    return () => {
      active = false
    }
  }, [part.lcsc])

  const attributes = useMemo(() => {
    if (!details?.attributes) return []
    return Object.entries(details.attributes).slice(0, 12)
  }, [details?.attributes])

  const handleInstall = async () => {
    if (!projectRoot) {
      setInstallError('Select a project to install parts.')
      return
    }
    setUninstallError(null)
    setUninstallSuccess(false)
    setIsInstalling(true)
    setInstallError(null)
    setInstallSuccess(false)
    try {
      const response = await api.parts.install(part.lcsc, projectRoot)
      if (!response.success) {
        setInstallError(response.error || 'Install failed')
      } else {
        setInstallSuccess(true)
      }
    } catch (err) {
      setInstallError(err instanceof Error ? err.message : 'Install failed')
    } finally {
      setIsInstalling(false)
    }
  }

  const description = details?.description || part.description || 'No description available.'
  const displayManufacturer = details?.manufacturer || part.manufacturer
  const displayMpn = details?.mpn || part.mpn
  const imageUrl = details?.image_url || part.image_url
  const isInstalled = (part.installed || installSuccess) && !uninstallSuccess
  const actionError = uninstallError || installError

  return (
    <div className="package-detail-panel parts-detail-panel">
      <div className="detail-panel-header">
        <div className="detail-header-left">
          <div className="detail-header-left-stack">
            <button className="detail-back-btn" onClick={onClose} title="Back">
              <ArrowLeft size={18} />
            </button>
            <Cpu size={20} className="detail-package-icon" />
          </div>
          <div className="detail-header-info">
            <div className="detail-title-row">
              <h2 className="detail-package-name">{displayMpn}</h2>
              {isInstalled && (
                <span className="detail-installed">
                  <CheckCircle size={14} />
                  Installed
                </span>
              )}
            </div>
            <div className="detail-package-meta">
              <p className="detail-package-blurb">{description}</p>
            </div>
          </div>
        </div>
      </div>

      {isLoading && (
        <div className="detail-panel-loading">
          <Loader2 size={24} className="spin" />
          <span>Loading part details...</span>
        </div>
      )}

      {!isLoading && error && (
        <div className="detail-panel-error">
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      {!isLoading && !error && (
        <div className="detail-panel-content">
          <div className="parts-detail-grid">
            {imageUrl && (
              <div className="detail-section parts-detail-section parts-image-section">
                <img src={imageUrl} alt={displayMpn} className="parts-image" />
              </div>
            )}
            <section className="detail-section parts-detail-section">
              <h3 className="detail-section-title">
                <Download size={14} />
                Install
              </h3>
              <div className="detail-install-row">
                <button
                  className={`detail-install-btn ${
                    isInstalled ? 'uninstall' : 'install'
                  } ${(isInstalling || isUninstalling) ? 'installing' : ''}`}
                  onClick={isInstalled ? async () => {
                    if (!projectRoot) {
                      setUninstallError('Select a project to uninstall parts.')
                      return
                    }
                    setIsUninstalling(true)
                    setInstallError(null)
                    setUninstallError(null)
                    try {
                      const response = await api.parts.uninstall(part.lcsc, projectRoot)
                      if (!response.success) {
                        setUninstallError(response.error || 'Uninstall failed')
                      } else {
                        setUninstallSuccess(true)
                        setInstallSuccess(false)
                      }
                    } catch (err) {
                      setUninstallError(err instanceof Error ? err.message : 'Uninstall failed')
                    } finally {
                      setIsUninstalling(false)
                    }
                  } : handleInstall}
                  disabled={isInstalling || isUninstalling}
                >
                  {(isInstalling || isUninstalling) ? (
                    <>
                      <Loader2 size={14} className="animate-spin" />
                      {isInstalled ? 'Uninstalling...' : 'Installing...'}
                    </>
                  ) : (
                    <>
                      <Download size={14} />
                      {isInstalled ? 'Uninstall' : 'Install'}
                    </>
                  )}
                </button>
              </div>
              {actionError && (
                <div className="detail-install-error">
                  <AlertCircle size={12} />
                  <span>{actionError}</span>
                </div>
              )}
              <div className="detail-install-meta">
                {isInstalled ? (
                  <>
                    <CheckCircle size={12} />
                    Installed
                  </>
                ) : (
                  <span>Not installed</span>
                )}
              </div>
            </section>
            <div className="detail-section parts-detail-section">
              <div className="parts-detail-section-title">Overview</div>
              <dl className="detail-info-list">
                <div className="detail-info-row">
                  <dt>Manufacturer</dt>
                  <dd className="detail-info-value">{displayManufacturer || '-'}</dd>
                </div>
                <div className="detail-info-row">
                  <dt>MPN</dt>
                  <dd className="detail-info-value">{displayMpn}</dd>
                </div>
                <div className="detail-info-row">
                  <dt>LCSC</dt>
                  <dd className="detail-info-value">
                    <span className="detail-info-mono">{part.lcsc}</span>
                  </dd>
                </div>
                <div className="detail-info-row">
                  <dt>Package</dt>
                  <dd className="detail-info-value">
                    <span className="detail-info-mono">{details?.package || part.package || '-'}</span>
                  </dd>
                </div>
                <div className="detail-info-row">
                  <dt>Stock</dt>
                  <dd className="detail-info-value">{formatStock(details?.stock)}</dd>
                </div>
                <div className="detail-info-row">
                  <dt>Unit price</dt>
                  <dd className="detail-info-value">{formatCurrency(details?.unit_cost)}</dd>
                </div>
                {details?.datasheet_url && (
                  <div className="detail-info-row">
                    <dt>Datasheet</dt>
                    <dd className="detail-info-value">
                      <a
                        className="parts-detail-link"
                        href={details.datasheet_url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Datasheet <ExternalLink size={12} />
                      </a>
                    </dd>
                  </div>
                )}
              </dl>
            </div>

            <div className="detail-section parts-detail-section">
              <div className="parts-detail-section-title">Footprint</div>
              <dl className="detail-info-list">
                <div className="detail-info-row">
                  <dt>Footprint</dt>
                  <dd className="detail-info-value">
                    <span className="detail-info-mono">
                      {details?.package || part.package || 'No footprint data yet'}
                    </span>
                  </dd>
                </div>
              </dl>
              <p className="parts-footprint-note detail-empty">
                Footprint preview will appear here once EasyEDA data is wired.
              </p>
            </div>

            <div className="detail-section parts-detail-section">
              <div className="parts-detail-section-title">Attributes</div>
              {attributes.length === 0 && (
                <div className="detail-empty">None</div>
              )}
              {attributes.length > 0 && (
                <dl className="detail-info-list">
                  {attributes.map(([key, value]) => (
                    <div key={key} className="detail-info-row">
                      <dt>{key}</dt>
                      <dd className="detail-info-value">
                        <span className="detail-info-mono">
                          {typeof value === 'string' ? value : JSON.stringify(value)}
                        </span>
                      </dd>
                    </div>
                  ))}
                </dl>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
