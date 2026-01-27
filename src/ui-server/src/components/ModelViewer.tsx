import { createElement, useEffect, useRef, useState } from 'react'

const MODEL_VIEWER_SRC =
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

  useEffect(() => {
    if (typeof window === 'undefined') return

    const ensureReady = () => {
      if (window.customElements?.get('model-viewer')) {
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
    script.src = MODEL_VIEWER_SRC
    script.type = 'module'
    script.async = true
    script.addEventListener('load', ensureReady, { once: true })
    document.head.appendChild(script)

    return () => {
      script.removeEventListener('load', ensureReady)
    }
  }, [isReady])

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
      {!isReady ? (
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
