import { useEffect, useMemo, useRef, useState } from 'react'
import { ArrowLeft, ExternalLink, Loader2, CheckCircle, AlertCircle, Download, Layers, Cuboid, Image } from 'lucide-react'
import type { PartSearchItem } from '../types/build'
import type { SelectedPart } from './sidebar-modules'
import { api } from '../api/client'
import { postMessage } from '../api/vscodeApi'
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
  const [isUninstalling, setIsUninstalling] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)
  // Track local override of installed state: null = use part.installed, true/false = override
  const [installedOverride, setInstalledOverride] = useState<boolean | null>(null)
  const [activeVisualTab, setActiveVisualTab] = useState<'image' | 'footprint' | '3d'>('image')

  useEffect(() => {
    let active = true

    // Check if we already have complete data (from search results)
    const hasCompleteData = part.stock != null && part.unit_cost != null && part.attributes != null

    if (hasCompleteData) {
      // Use the data we already have
      setDetails({
        lcsc: part.lcsc,
        mpn: part.mpn,
        manufacturer: part.manufacturer,
        description: part.description || '',
        package: part.package || '',
        datasheet_url: part.datasheet_url || '',
        image_url: part.image_url,
        stock: part.stock!,
        unit_cost: part.unit_cost!,
        is_basic: part.is_basic || false,
        is_preferred: part.is_preferred || false,
        price: [],
        attributes: part.attributes || {},
      })
      setIsLoading(false)
      return
    }

    // Fetch additional details
    setIsLoading(true)
    setError(null)
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
  }, [part.lcsc, part.stock, part.unit_cost, part.attributes])

  // Merge part props with fetched details (part props as fallback, details as primary)
  const mergedDetails = useMemo(() => {
    return {
      stock: details?.stock ?? part.stock,
      unit_cost: details?.unit_cost ?? part.unit_cost,
      is_basic: details?.is_basic ?? part.is_basic,
      is_preferred: details?.is_preferred ?? part.is_preferred,
      attributes: details?.attributes ?? part.attributes,
      package: details?.package ?? part.package,
      datasheet_url: details?.datasheet_url ?? part.datasheet_url,
    }
  }, [details, part])

  const attributes = useMemo(() => {
    if (!mergedDetails.attributes) return []
    return Object.entries(mergedDetails.attributes).slice(0, 12)
  }, [mergedDetails.attributes])

  // Cooldown timestamp to debounce rapid clicking
  const cooldownUntil = useRef(0)
  const COOLDOWN_MS = 1000 // 1 second cooldown between operations

  const handleInstall = async () => {
    if (!projectRoot) {
      setActionError('Select a project to install parts.')
      return
    }
    if (Date.now() < cooldownUntil.current) return
    if (isInstalling || isUninstalling) return

    setIsInstalling(true)
    setActionError(null)
    try {
      const response = await api.parts.install(part.lcsc, projectRoot)
      if (!response.success) {
        setActionError(response.error || 'Install failed')
      } else {
        setInstalledOverride(true)
        cooldownUntil.current = Date.now() + COOLDOWN_MS
      }
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Install failed')
    } finally {
      setIsInstalling(false)
    }
  }

  const handleUninstall = async () => {
    if (!projectRoot) {
      setActionError('Select a project to uninstall parts.')
      return
    }
    if (Date.now() < cooldownUntil.current) return
    if (isInstalling || isUninstalling) return

    setIsUninstalling(true)
    setActionError(null)
    try {
      const response = await api.parts.uninstall(part.lcsc, projectRoot)
      if (!response.success) {
        setActionError(response.error || 'Uninstall failed')
      } else {
        setInstalledOverride(false)
        cooldownUntil.current = Date.now() + COOLDOWN_MS
      }
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Uninstall failed')
    } finally {
      setIsUninstalling(false)
    }
  }

  const description = details?.description || part.description || 'No description available.'
  const displayManufacturer = details?.manufacturer || part.manufacturer
  const displayMpn = details?.mpn || part.mpn
  const imageUrl = details?.image_url || part.image_url
  const isInstalled = installedOverride !== null ? installedOverride : part.installed

  return (
    <div className="package-detail-panel parts-detail-panel">
      <div className="detail-panel-header">
        <button className="detail-back-btn" onClick={onClose} title="Back">
          <ArrowLeft size={18} />
        </button>
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
          <p className="detail-package-blurb">{description}</p>
        </div>
      </div>

      {error && (
        <div className="detail-panel-error">
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      <div className="detail-panel-content">
        <div className="parts-detail-grid">
          <div className="parts-detail-section">
            <div className="detail-install-row">
              <button
                className={`detail-install-btn ${
                  isInstalled ? 'uninstall' : 'install'
                } ${(isInstalling || isUninstalling) ? 'installing' : ''}`}
                onClick={isInstalled ? handleUninstall : handleInstall}
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
          </div>
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
                  <span className="detail-info-mono">{mergedDetails.package || '-'}</span>
                </dd>
              </div>
              <div className="detail-info-row">
                <dt>Stock</dt>
                <dd className="detail-info-value">
                  {isLoading && mergedDetails.stock == null ? (
                    <Loader2 size={12} className="parts-spinner" />
                  ) : (
                    formatStock(mergedDetails.stock)
                  )}
                </dd>
              </div>
              <div className="detail-info-row">
                <dt>Unit price</dt>
                <dd className="detail-info-value">
                  {isLoading && mergedDetails.unit_cost == null ? (
                    <Loader2 size={12} className="parts-spinner" />
                  ) : (
                    formatCurrency(mergedDetails.unit_cost)
                  )}
                </dd>
              </div>
              <div className="detail-info-row">
                <dt>Type</dt>
                <dd className="detail-info-value">
                  {isLoading && mergedDetails.is_basic == null && mergedDetails.is_preferred == null ? (
                    <Loader2 size={12} className="parts-spinner" />
                  ) : (
                    <span className={`parts-type-badge ${mergedDetails.is_basic ? 'basic' : mergedDetails.is_preferred ? 'preferred' : 'extended'}`}>
                      {mergedDetails.is_basic ? 'Basic' : mergedDetails.is_preferred ? 'Preferred' : 'Extended'}
                    </span>
                  )}
                </dd>
              </div>
              {(mergedDetails.datasheet_url || part.datasheet_url) && (
                <div className="detail-info-row">
                  <dt>Datasheet</dt>
                  <dd className="detail-info-value">
                    <button
                      className="parts-detail-link"
                      onClick={() => postMessage({ type: 'openInSimpleBrowser', url: (mergedDetails.datasheet_url || part.datasheet_url)! })}
                    >
                      Datasheet <ExternalLink size={12} />
                    </button>
                  </dd>
                </div>
              )}
            </dl>
          </div>

          <div className="detail-section parts-detail-section">
            <div className="parts-detail-section-title">Attributes</div>
            {isLoading && attributes.length === 0 ? (
              <div className="detail-empty"><Loader2 size={12} className="parts-spinner" /> Loading...</div>
            ) : attributes.length === 0 ? (
              <div className="detail-empty">None</div>
            ) : (
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
                  src={`${API_URL}/api/parts/${encodeURIComponent(part.lcsc)}/footprint.kicad_pcb${projectRoot ? `?project_root=${encodeURIComponent(projectRoot)}` : ''}`}
                  controls="basic"
                  controlslist="nodownload"
                  theme="kicad"
                  zoom="objects"
                  hideReferences
                />
              ) : (
                <StepViewer
                  src={`${API_URL}/api/parts/${encodeURIComponent(part.lcsc)}/model${projectRoot ? `?project_root=${encodeURIComponent(projectRoot)}` : ''}`}
                />
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
