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

  // Set kicanvas board colors from computed theme values and trigger redraw
  // This resolves the nested CSS variable issue where getPropertyValue returns unresolved vars
  useEffect(() => {
    if (typeof window === 'undefined') return

    const updateBoardColors = () => {
      const bgColor = getComputedStyle(document.documentElement).getPropertyValue('--bg-primary').trim()
      if (bgColor) {
        document.documentElement.style.setProperty('--kicanvas-board-bg', bgColor)
        document.documentElement.style.setProperty('--kicanvas-board-grid', bgColor)
      }

      // Also trigger kicanvas to update its theme and redraw
      const embed = embedRef.current
      if (embed) {
        const viewer = (embed as unknown as {
          viewer?: {
            update_theme?: () => void
            theme?: { background?: unknown; grid?: unknown }
            renderer?: { background_color?: unknown }
            draw?: () => void
          }
        }).viewer

        if (viewer?.update_theme) {
          viewer.update_theme()
          viewer.draw?.()
        }
      }
    }

    // Update on mount and when theme changes
    updateBoardColors()

    // Watch for theme changes via data-theme attribute
    const observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        if (mutation.attributeName === 'data-theme' || mutation.attributeName === 'class') {
          // Small delay to let CSS variables update first
          setTimeout(updateBoardColors, 50)
        }
      }
    })
    observer.observe(document.documentElement, { attributes: true })

    return () => observer.disconnect()
  }, [isReady])

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

      // Access the viewer with extended type for various zoom methods
      const viewer = (embed as unknown as {
        viewer?: {
          layers?: { set_visibility?: (layer: string, visible: boolean) => void }
          zoom_to_page?: () => void
          zoom_to_fit?: () => void
          zoom_all?: () => void
          fit?: () => void
          camera?: {
            fit_to_bbox?: (bbox: unknown) => void
            zoom_to_bbox?: (bbox: unknown) => void
          }
          draw?: () => void
          grid?: {
            visible?: boolean
            enabled?: boolean
          }
          set_grid_visible?: (visible: boolean) => void
          show_grid?: boolean
          renderer?: {
            grid_visible?: boolean
            show_grid?: boolean
          }
        }
      }).viewer

      // Disable grid dots
      if (viewer) {
        // Try various methods to disable the grid
        if (viewer.grid) {
          viewer.grid.visible = false
          viewer.grid.enabled = false
        }
        if (viewer.set_grid_visible) {
          viewer.set_grid_visible(false)
        }
        if ('show_grid' in viewer) {
          viewer.show_grid = false
        }
        if (viewer.renderer) {
          if ('grid_visible' in viewer.renderer) {
            viewer.renderer.grid_visible = false
          }
          if ('show_grid' in viewer.renderer) {
            viewer.renderer.show_grid = false
          }
        }
      }

      // Hide reference designators if requested
      if (hideReferences && viewer?.layers?.set_visibility) {
        // Hide front and back silkscreen (reference designators)
        viewer.layers.set_visibility('F.Silkscreen', false)
        viewer.layers.set_visibility('B.Silkscreen', false)
      }

      // Style toolbar buttons and hide grid in shadow DOM
      const styleShadowDOM = () => {
        const shadowRoot = embed.shadowRoot
        if (!shadowRoot) return

        // Get computed theme colors
        const bgPrimary = getComputedStyle(document.documentElement).getPropertyValue('--bg-primary').trim() || '#1e1e2e'
        const bgSecondary = getComputedStyle(document.documentElement).getPropertyValue('--bg-secondary').trim() || '#313244'
        const textPrimary = getComputedStyle(document.documentElement).getPropertyValue('--text-primary').trim() || '#cdd6f4'
        const borderSubtle = getComputedStyle(document.documentElement).getPropertyValue('--border-subtle').trim() || '#45475a'
        const bgHover = getComputedStyle(document.documentElement).getPropertyValue('--bg-hover').trim() || '#45475a'

        // Inject CSS to hide grid and style toolbar
        const styleId = 'atopile-kicanvas-overrides'
        if (!shadowRoot.getElementById(styleId)) {
          const style = document.createElement('style')
          style.id = styleId
          style.textContent = `
            /* Hide grid dots/lines */
            .grid, [class*="grid"], canvas.grid, .grid-layer, .grid-overlay {
              display: none !important;
              visibility: hidden !important;
              opacity: 0 !important;
            }

            /* Set grid colors to transparent/background */
            :host {
              --grid-color: transparent !important;
              --grid-bg: transparent !important;
              --grid: transparent !important;
              --board-grid: ${bgPrimary} !important;
              --kicanvas-board-grid: ${bgPrimary} !important;
            }

            /* Style toolbar buttons */
            button {
              background: ${bgSecondary} !important;
              color: ${textPrimary} !important;
              border: 1px solid ${borderSubtle} !important;
              border-radius: 4px !important;
            }
            button:hover {
              background: ${bgHover} !important;
            }

            /* Style toolbar containers */
            [class*="toolbar"], [class*="controls"], [class*="status-bar"] {
              background: ${bgSecondary} !important;
              border-color: ${borderSubtle} !important;
            }
          `
          shadowRoot.appendChild(style)
        }

        // Also directly style buttons for browsers that don't support !important in shadow DOM
        const buttons = shadowRoot.querySelectorAll('button')
        buttons.forEach((btn: HTMLButtonElement) => {
          btn.style.background = bgSecondary
          btn.style.color = textPrimary
          btn.style.border = `1px solid ${borderSubtle}`
          btn.style.borderRadius = '4px'
          btn.addEventListener('mouseenter', () => {
            btn.style.background = bgHover
          })
          btn.addEventListener('mouseleave', () => {
            btn.style.background = bgSecondary
          })
        })
      }

      // Re-zoom after hiding layers to center on remaining visible content
      // Try various zoom methods that KiCanvas may support
      setTimeout(() => {
        // Style shadow DOM (toolbar buttons, hide grid)
        styleShadowDOM()

        // Try zoom_to_fit first (fits to visible content)
        if (viewer?.zoom_to_fit) {
          viewer.zoom_to_fit()
        } else if (viewer?.fit) {
          viewer.fit()
        } else if (viewer?.zoom_all) {
          viewer.zoom_all()
        } else if (viewer?.zoom_to_page) {
          viewer.zoom_to_page()
        }
        viewer?.draw?.()
      }, 100) // Slightly longer delay to ensure layer changes are processed
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
