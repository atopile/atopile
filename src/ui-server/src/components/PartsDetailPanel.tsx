import { useEffect, useMemo, useState } from 'react'
import { ArrowLeft, Cpu, ExternalLink, Loader2, CheckCircle, AlertCircle, Download, Layers, Cuboid, Image } from 'lucide-react'
import type { PartSearchItem } from '../types/build'
import type { SelectedPart } from './sidebar-modules'
import { api } from '../api/client'
import { API_URL } from '../api/config'
import KiCanvasEmbed from './KiCanvasEmbed'
import StepViewer from './StepViewer'
import './PartsDetailPanel.css'

interface PartsDetailPanelProps {
  part: SelectedPart
  projectRoot: string | null
  onClose: () => void
}

function formatCurrency(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return '-'
  if (value < 0.01) return `$${value.toFixed(4)}`
  return `$${value.toFixed(2)}`
}

function formatStock(stock: number | null | undefined): string {
  if (stock == null) return '-'
  if (stock <= 0) return 'Out of stock'
  if (stock >= 1_000_000) return `${(stock / 1_000_000).toFixed(1)}M`
  if (stock >= 1_000) return `${(stock / 1_000).toFixed(1)}K`
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
  const [activeVisualTab, setActiveVisualTab] = useState<'image' | 'footprint' | '3d'>('image')

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
            <section className="detail-section parts-detail-section">
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
                <div className="detail-info-row">
                  <dt>Type</dt>
                  <dd className="detail-info-value">
                    <span className={`parts-type-badge ${details?.is_basic ? 'basic' : details?.is_preferred ? 'preferred' : 'extended'}`}>
                      {details?.is_basic ? 'Basic' : details?.is_preferred ? 'Preferred' : 'Extended'}
                    </span>
                  </dd>
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

            <div className="parts-visual-section">
              <div className="parts-visual-tabs">
                <button
                  className={`parts-visual-tab ${activeVisualTab === 'image' ? 'active' : ''}`}
                  onClick={() => setActiveVisualTab('image')}
                >
                  <Image size={14} />
                  Image
                </button>
                <button
                  className={`parts-visual-tab ${activeVisualTab === 'footprint' ? 'active' : ''}`}
                  onClick={() => setActiveVisualTab('footprint')}
                >
                  <Layers size={14} />
                  Footprint
                </button>
                <button
                  className={`parts-visual-tab ${activeVisualTab === '3d' ? 'active' : ''}`}
                  onClick={() => setActiveVisualTab('3d')}
                >
                  <Cuboid size={14} />
                  3D Model
                </button>
              </div>
              <div className="parts-visual-content">
                {activeVisualTab === 'image' ? (
                  imageUrl ? (
                    <img src={imageUrl} alt={displayMpn} className="parts-visual-image" />
                  ) : (
                    <div className="parts-visual-empty">No image available</div>
                  )
                ) : activeVisualTab === 'footprint' ? (
                  <KiCanvasEmbed
                    src={`${API_URL}/api/parts/${encodeURIComponent(part.lcsc)}/footprint.kicad_pcb`}
                    controls="basic"
                    theme="kicad"
                    zoom="objects"
                  />
                ) : (
                  <StepViewer
                    src={`${API_URL}/api/parts/${encodeURIComponent(part.lcsc)}/model`}
                  />
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
