import { createElement, useEffect, useRef, useState } from 'react'

// Use bundled model-viewer from VS Code extension if available, otherwise fall back to CDN
const MODEL_VIEWER_SRC =
  (window as { __ATOPILE_MODEL_VIEWER_URL__?: string }).__ATOPILE_MODEL_VIEWER_URL__ ||
  'https://ajax.googleapis.com/ajax/libs/model-viewer/4.1.0/model-viewer.min.js'
const SCRIPT_ID = 'model-viewer-script'

interface ModelViewerProps {
  src: string
  className?: string
  style?: React.CSSProperties
}

interface ModelViewerElement extends HTMLElement {
  src?: string
  'auto-rotate'?: string
  'camera-controls'?: string
  'tone-mapping'?: string
  'environment-image'?: string
  'exposure'?: string
  'shadow-intensity'?: string
  'shadow-softness'?: string
  'ar'?: string
  'ar-modes'?: string
}

export default function ModelViewer({ src, className, style }: ModelViewerProps) {
  const viewerRef = useRef<ModelViewerElement>(null)
  const [isReady, setIsReady] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (typeof window === 'undefined') return

    let cancelled = false
    let pollInterval: ReturnType<typeof setInterval> | null = null

    const checkReady = () => {
      if (window.customElements?.get('model-viewer')) {
        if (pollInterval) clearInterval(pollInterval)
        if (!cancelled) setIsReady(true)
        return true
      }
      return false
    }

    // Already registered?
    if (checkReady()) return

    // Poll for registration after script loads (model-viewer registers async)
    const startPolling = () => {
      let attempts = 0
      pollInterval = setInterval(() => {
        if (checkReady() || cancelled) {
          if (pollInterval) clearInterval(pollInterval)
          return
        }
        attempts++
        if (attempts > 50) { // 5 seconds max
          if (pollInterval) clearInterval(pollInterval)
          if (!cancelled) setError('3D viewer failed to initialize')
        }
      }, 100)
    }

    const existing = document.getElementById(SCRIPT_ID) as HTMLScriptElement | null
    if (existing) {
      // Script already added, just poll for element registration
      startPolling()
      return () => {
        cancelled = true
        if (pollInterval) clearInterval(pollInterval)
      }
    }

    const script = document.createElement('script')
    script.id = SCRIPT_ID
    script.src = MODEL_VIEWER_SRC
    script.type = 'module'
    script.async = true
    script.addEventListener('load', () => startPolling(), { once: true })
    script.addEventListener('error', () => {
      if (!cancelled) setError('Failed to load 3D viewer')
    }, { once: true })
    document.head.appendChild(script)

    return () => {
      cancelled = true
      if (pollInterval) clearInterval(pollInterval)
    }
  }, [])

  useEffect(() => {
    setIsLoading(true)
  }, [src])

  useEffect(() => {
    const viewer = viewerRef.current
    if (!viewer || !isReady) return

    const handleLoad = () => setIsLoading(false)
    const handleError = () => setIsLoading(false)

    viewer.addEventListener('load', handleLoad)
    viewer.addEventListener('error', handleError)
    return () => {
      viewer.removeEventListener('load', handleLoad)
      viewer.removeEventListener('error', handleError)
    }
  }, [isReady])

  return (
    <div className="detail-visual-frame detail-visual-stack">
      {error ? (
        <div className="detail-visual-empty">{error}</div>
      ) : !isReady ? (
        <div className="detail-visual-spinner">
          <span className="spinner" />
          <span>Loading 3D...</span>
        </div>
      ) : (
        <>
          {createElement('model-viewer', {
            key: src,
            ref: viewerRef,
            src,
            'auto-rotate': 'true',
            'camera-controls': 'true',
            'tone-mapping': 'neutral',
            exposure: '1.2',
            'shadow-intensity': '0.7',
            'shadow-softness': '0.8',
            ar: 'true',
            'ar-modes': 'webxr scene-viewer quick-look',
            className,
            style: {
              width: '100%',
              height: '100%',
              ...style,
            },
          })}
          {isLoading && (
            <div className="detail-visual-spinner">
              <span className="spinner" />
              <span>Loading 3D...</span>
            </div>
          )}
        </>
      )}
    </div>
  )
}
