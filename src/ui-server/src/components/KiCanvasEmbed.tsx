import { createElement, useEffect, useRef, useState } from 'react'

const SCRIPT_ID = 'kicanvas-script'
const SCRIPT_SRC = '/vendored/kicanvas.js'

interface KiCanvasEmbedProps {
  src: string
  controls?: 'none' | 'basic' | 'full'
  controlslist?: string
  theme?: 'kicad' | 'witchhazel'
  zoom?: 'objects' | 'page'
  className?: string
  style?: React.CSSProperties
  onError?: (error: string) => void
}

interface KiCanvasEmbedElement extends HTMLElement {
  src?: string
  controls?: string
  controlslist?: string
  theme?: string
  zoom?: string
}

export default function KiCanvasEmbed({
  src,
  controls = 'full',
  controlslist,
  theme = 'kicad',
  zoom = 'objects',
  className,
  style,
  onError,
}: KiCanvasEmbedProps) {
  const embedRef = useRef<KiCanvasEmbedElement>(null)
  const [isReady, setIsReady] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (typeof window === 'undefined') return

    const ensureReady = () => {
      if (window.customElements?.get('kicanvas-embed')) {
        setIsReady(true)
      }
    }

    ensureReady()
    if (isReady) return

    const existing = document.getElementById(SCRIPT_ID) as HTMLScriptElement | null
    if (existing) {
      existing.addEventListener('load', ensureReady, { once: true })
      return () => existing.removeEventListener('load', ensureReady)
    }

    const script = document.createElement('script')
    script.id = SCRIPT_ID
    script.src = SCRIPT_SRC
    script.async = true
    script.addEventListener('load', ensureReady, { once: true })
    document.head.appendChild(script)

    return () => {
      script.removeEventListener('load', ensureReady)
    }
  }, [isReady])

  // Pre-check if src URL is valid using GET (HEAD not supported by all endpoints)
  useEffect(() => {
    setIsLoading(true)
    setError(null)

    const controller = new AbortController()
    fetch(src, { signal: controller.signal })
      .then((response) => {
        if (!response.ok) {
          const msg = response.status === 404
            ? 'Footprint not available'
            : `Failed to load footprint (${response.status})`
          setError(msg)
          onError?.(msg)
          setIsLoading(false)
        }
        // If OK, let kicanvas handle the actual loading
      })
      .catch((err) => {
        if (err.name === 'AbortError') return
        setError('Failed to load footprint')
        onError?.('Failed to load footprint')
        setIsLoading(false)
      })

    return () => {
      controller.abort()
    }
  }, [src, onError])

  useEffect(() => {
    const embed = embedRef.current
    if (!embed || !isReady) return

    const handleLoad = () => {
      console.log('[KiCanvas] Load event fired')
      setIsLoading(false)
    }
    const handleError = (e: Event) => {
      console.log('[KiCanvas] Error event fired', e)
      setIsLoading(false)
    }

    // Listen for various possible event names
    embed.addEventListener('kicanvas:load', handleLoad)
    embed.addEventListener('kicanvas:loaded', handleLoad)
    embed.addEventListener('load', handleLoad)
    embed.addEventListener('error', handleError)
    embed.addEventListener('kicanvas:error', handleError)

    // Fallback timeout - if no events fire after 5 seconds, assume loaded
    const timeout = setTimeout(() => {
      console.log('[KiCanvas] Timeout reached, assuming loaded')
      setIsLoading(false)
    }, 5000)

    return () => {
      clearTimeout(timeout)
      embed.removeEventListener('kicanvas:load', handleLoad)
      embed.removeEventListener('kicanvas:loaded', handleLoad)
      embed.removeEventListener('load', handleLoad)
      embed.removeEventListener('error', handleError)
      embed.removeEventListener('kicanvas:error', handleError)
    }
  }, [isReady])

  return (
    <div className="detail-visual-frame detail-visual-stack">
      {error ? (
        <div className="detail-visual-empty">
          {error}
        </div>
      ) : !isReady ? (
        <div className="detail-visual-spinner">
          <span className="spinner" />
          <span>Loading viewer...</span>
        </div>
      ) : (
        <>
          {createElement('kicanvas-embed', {
            key: src,
            ref: embedRef,
            src,
            controls,
            controlslist,
            theme,
            zoom,
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
              <span>Loading footprint...</span>
            </div>
          )}
        </>
      )}
    </div>
  )
}
