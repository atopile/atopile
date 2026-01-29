import { createElement, useEffect, useRef, useState } from 'react'

const SCRIPT_ID = 'kicanvas-script'
const SCRIPT_SRC = 'vendored/kicanvas.js'

interface KiCanvasEmbedProps {
  src: string
  controls?: 'none' | 'basic' | 'full'
  controlslist?: string
  theme?: 'kicad' | 'witchhazel'
  zoom?: 'objects' | 'page'
  className?: string
  style?: React.CSSProperties
  onError?: (error: string) => void
  hideReferences?: boolean
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
  hideReferences = false,
}: KiCanvasEmbedProps) {
  const embedRef = useRef<KiCanvasEmbedElement>(null)
  const [isReady, setIsReady] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Set kicanvas board colors from computed theme values
  // This resolves the nested CSS variable issue where getPropertyValue returns unresolved vars
  useEffect(() => {
    if (typeof window === 'undefined') return

    const updateBoardColors = () => {
      const bgColor = getComputedStyle(document.documentElement).getPropertyValue('--bg-primary').trim()
      if (bgColor) {
        document.documentElement.style.setProperty('--kicanvas-board-bg', bgColor)
        document.documentElement.style.setProperty('--kicanvas-board-grid', bgColor)
      }
    }

    // Update on mount and when theme changes
    updateBoardColors()

    // Watch for theme changes via data-theme attribute
    const observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        if (mutation.attributeName === 'data-theme' || mutation.attributeName === 'class') {
          updateBoardColors()
        }
      }
    })
    observer.observe(document.documentElement, { attributes: true })

    return () => observer.disconnect()
  }, [])

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
      setIsLoading(false)

      // Access the viewer
      const viewer = (embed as unknown as {
        viewer?: {
          layers?: { set_visibility?: (layer: string, visible: boolean) => void }
          zoom_to_page?: () => void
          draw?: () => void
        }
      }).viewer

      // Hide reference designators if requested
      if (hideReferences && viewer?.layers?.set_visibility) {
        // Hide front and back silkscreen (reference designators)
        viewer.layers.set_visibility('F.Silkscreen', false)
        viewer.layers.set_visibility('B.Silkscreen', false)
      }

      // Zoom to page bounds (excludes text items that extend beyond board)
      // This gives a cleaner view focused on the actual footprint/board
      if (viewer?.zoom_to_page) {
        // Small delay to ensure layer visibility changes are applied
        setTimeout(() => {
          viewer.zoom_to_page?.()
          viewer.draw?.()
        }, 50)
      }
    }
    const handleError = () => setIsLoading(false)

    // Listen for various possible event names
    embed.addEventListener('kicanvas:load', handleLoad)
    embed.addEventListener('kicanvas:loaded', handleLoad)
    embed.addEventListener('load', handleLoad)
    embed.addEventListener('error', handleError)
    embed.addEventListener('kicanvas:error', handleError)

    // Fallback timeout - if no events fire after 5 seconds, assume loaded
    const timeout = setTimeout(() => setIsLoading(false), 5000)

    return () => {
      clearTimeout(timeout)
      embed.removeEventListener('kicanvas:load', handleLoad)
      embed.removeEventListener('kicanvas:loaded', handleLoad)
      embed.removeEventListener('load', handleLoad)
      embed.removeEventListener('error', handleError)
      embed.removeEventListener('kicanvas:error', handleError)
    }
  }, [isReady, src, hideReferences])

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
