/**
 * GerberViewer - Renders Gerber files using @tracespace/core for realistic PCB renders.
 *
 * Features:
 * - Realistic PCB stackup rendering (copper, soldermask, silkscreen)
 * - Smooth pan/zoom with react-zoom-pan-pinch
 * - Top/Bottom view toggle
 * - Collapsible layers panel
 * - Theme-aware styling
 */

import { useEffect, useState, useCallback, useMemo, useRef } from 'react';
import {
  read,
  plot,
  renderLayers,
  renderBoard,
  stringifySvg,
  type Layer,
} from '@tracespace/core';
import { TransformWrapper, TransformComponent } from 'react-zoom-pan-pinch';
import {
  Loader2,
  AlertCircle,
  Layers,
  ChevronLeft,
  ChevronRight,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  FlipVertical2,
  Maximize2,
} from 'lucide-react';
import JSZip from 'jszip';
import './GerberViewer.css';

interface GerberViewerProps {
  src: string;
  className?: string;
  style?: React.CSSProperties;
  hideControls?: boolean;
  hideZoomControls?: boolean;
  hideLayersPanel?: boolean;
}

type ViewSide = 'top' | 'bottom';

export default function GerberViewer({ src, className, style, hideControls = false, hideZoomControls = false, hideLayersPanel = false }: GerberViewerProps) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [topSvg, setTopSvg] = useState<string | null>(null);
  const [bottomSvg, setBottomSvg] = useState<string | null>(null);
  const [layers, setLayers] = useState<Layer[]>([]);
  const [viewSide, setViewSide] = useState<ViewSide>('top');
  const [layersPanelCollapsed, setLayersPanelCollapsed] = useState(true);
  const [hiddenLayers, setHiddenLayers] = useState<Set<string>>(new Set());
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const loadGerbers = async () => {
      setLoading(true);
      setError(null);

      try {
        const response = await fetch(src);
        if (!response.ok) {
          throw new Error(`Failed to fetch gerbers: ${response.status} ${response.statusText}`);
        }

        const arrayBuffer = await response.arrayBuffer();
        const zip = await JSZip.loadAsync(arrayBuffer);

        // Extract files from zip as File objects
        const files: File[] = [];

        for (const [filename, zipEntry] of Object.entries(zip.files)) {
          if (zipEntry.dir) continue;

          // Get the base filename (without directory path)
          const baseName = filename.split('/').pop() || filename;

          // Skip non-gerber files
          const ext = baseName.toLowerCase().split('.').pop() || '';
          const isGerberExt = [
            'gbr', 'ger', 'gtl', 'gbl', 'gts', 'gbs', 'gto', 'gbo',
            'gtp', 'gbp', 'gko', 'gm1', 'gm2', 'gm3', 'drl', 'xln', 'exc',
            'gta', 'gba'  // adhesive layers
          ].includes(ext);

          // Also accept KiCad-style naming (with underscores or dots)
          const isKiCadNaming = baseName.includes('-') && (
            baseName.includes('_Cu') || baseName.includes('.Cu') ||
            baseName.includes('_Mask') || baseName.includes('.Mask') ||
            baseName.includes('_Silk') || baseName.includes('.Silk') ||
            baseName.includes('_Paste') || baseName.includes('.Paste') ||
            baseName.includes('_Edge') || baseName.includes('.Edge') ||
            baseName.includes('-PTH') ||
            baseName.includes('-NPTH')
          );

          if (!isGerberExt && !isKiCadNaming) {
            continue;
          }

          // Get content as text string first (gerbers are text files)
          const textContent = await zipEntry.async('string');
          // Create File with text/plain type for proper FileReader handling
          const file = new File([textContent], baseName, { type: 'text/plain' });
          files.push(file);
        }

        if (files.length === 0) {
          throw new Error('No valid gerber files found in archive');
        }

        // Use tracespace pipeline
        const readResult = await read(files);
        const plotResult = plot(readResult);
        const renderLayersResult = renderLayers(plotResult);
        const boardResult = renderBoard(renderLayersResult);

        // Convert to SVG strings
        const topSvgStr = stringifySvg(boardResult.top);
        const bottomSvgStr = stringifySvg(boardResult.bottom);

        setTopSvg(topSvgStr);
        setBottomSvg(bottomSvgStr);
        setLayers(readResult.layers);

      } catch (err) {
        console.error('[GerberViewer] Error loading gerbers:', err);
        setError(err instanceof Error ? err.message : 'Failed to load gerbers');
      } finally {
        setLoading(false);
      }
    };

    loadGerbers();
  }, [src]);

  const toggleViewSide = useCallback(() => {
    setViewSide(prev => prev === 'top' ? 'bottom' : 'top');
  }, []);

  const toggleLayerVisibility = useCallback((layerId: string) => {
    setHiddenLayers(prev => {
      const next = new Set(prev);
      if (next.has(layerId)) {
        next.delete(layerId);
      } else {
        next.add(layerId);
      }
      return next;
    });
  }, []);

  // Generate CSS to hide layers
  const layerVisibilityStyle = useMemo(() => {
    if (hiddenLayers.size === 0) return '';

    // Map layer IDs to CSS selectors for tracespace SVG classes
    const selectors: string[] = [];
    hiddenLayers.forEach(layerId => {
      // tracespace uses class names like "id_type" format
      selectors.push(`.gerber-svg-container [class*="${layerId}"] { opacity: 0 !important; }`);
    });
    return selectors.join('\n');
  }, [hiddenLayers]);

  const currentSvg = viewSide === 'top' ? topSvg : bottomSvg;

  if (loading) {
    return (
      <div className={`gerber-viewer gerber-viewer-loading ${className || ''}`} style={style}>
        <Loader2 className="spinning" size={24} />
        <span>Rendering PCB...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`gerber-viewer gerber-viewer-error ${className || ''}`} style={style}>
        <AlertCircle size={24} />
        <span>{error}</span>
      </div>
    );
  }

  // Handle case where loading completed but no SVG was generated
  if (!topSvg && !bottomSvg) {
    return (
      <div className={`gerber-viewer gerber-viewer-error ${className || ''}`} style={style}>
        <AlertCircle size={24} />
        <span>Failed to render PCB - no SVG generated</span>
        <span style={{ fontSize: '0.8em', opacity: 0.7 }}>Layers found: {layers.length}</span>
      </div>
    );
  }

  return (
    <div className={`gerber-viewer ${className || ''}`} style={style} ref={containerRef}>
      {/* Dynamic styles for layer visibility */}
      {layerVisibilityStyle && <style>{layerVisibilityStyle}</style>}

      <TransformWrapper
        initialScale={1}
        minScale={0.05}
        maxScale={50}
        centerOnInit={false}
        limitToBounds={false}
        wheel={{ step: 0.15 }}
        panning={{ velocityDisabled: true }}
        doubleClick={{ mode: 'reset' }}
        onInit={(ref) => {
          // Center the view after a short delay to ensure content is rendered
          setTimeout(() => {
            ref.centerView(0.8);
          }, 100);
        }}
      >
        {({ zoomIn, zoomOut, resetTransform, centerView, instance }) => (
          <>
            <TransformComponent
              wrapperClass="gerber-transform-wrapper"
              contentClass="gerber-transform-content"
            >
              <div
                className="gerber-svg-container"
                dangerouslySetInnerHTML={{ __html: currentSvg || '' }}
              />
            </TransformComponent>

            {/* Controls overlay */}
            {!hideControls && (
              <div className="gerber-controls">
                {/* View toggle */}
                <div className="gerber-view-toggle">
                  <button
                    className={`gerber-view-btn ${viewSide === 'top' ? 'active' : ''}`}
                    onClick={() => setViewSide('top')}
                  >
                    Top
                  </button>
                  <button
                    className={`gerber-view-btn ${viewSide === 'bottom' ? 'active' : ''}`}
                    onClick={() => setViewSide('bottom')}
                  >
                    Bottom
                  </button>
                </div>

                {/* Zoom controls */}
                {!hideZoomControls && (
                  <div className="gerber-zoom-controls">
                    <button
                      className="gerber-zoom-btn"
                      onClick={() => zoomIn()}
                      title="Zoom in"
                    >
                      <ZoomIn size={14} />
                    </button>
                    <button
                      className="gerber-zoom-btn"
                      onClick={() => zoomOut()}
                      title="Zoom out"
                    >
                      <ZoomOut size={14} />
                    </button>
                    <button
                      className="gerber-zoom-btn"
                      onClick={() => centerView(0.8)}
                      title="Fit to view"
                    >
                      <Maximize2 size={14} />
                    </button>
                    <button
                      className="gerber-zoom-btn"
                      onClick={() => resetTransform()}
                      title="Reset view (100%)"
                    >
                      <RotateCcw size={14} />
                    </button>
                    <button
                      className="gerber-zoom-btn"
                      onClick={toggleViewSide}
                      title="Flip board"
                    >
                      <FlipVertical2 size={14} />
                    </button>
                    <span className="gerber-zoom-level">
                      {Math.round((instance?.transformState?.scale || 1) * 100)}%
                    </span>
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </TransformWrapper>

      {/* Layers panel */}
      {!hideControls && !hideLayersPanel && (
        <div className={`gerber-layer-controls ${layersPanelCollapsed ? 'collapsed' : ''}`}>
          <button
            className="gerber-layer-collapse-btn"
            onClick={() => setLayersPanelCollapsed(!layersPanelCollapsed)}
            title={layersPanelCollapsed ? 'Show layers' : 'Hide layers'}
          >
            {layersPanelCollapsed ? <ChevronLeft size={14} /> : <ChevronRight size={14} />}
          </button>
          {!layersPanelCollapsed && (
            <>
              <div className="gerber-layer-title">
                <Layers size={14} />
                Layers ({layers.length})
              </div>
              <div className="gerber-layer-list">
                {layers.map((layer) => {
                  const isVisible = !hiddenLayers.has(layer.id);
                  return (
                    <button
                      key={layer.id}
                      className={`gerber-layer-item ${isVisible ? '' : 'hidden-layer'}`}
                      onClick={() => toggleLayerVisibility(layer.id)}
                      title={`Click to ${isVisible ? 'hide' : 'show'} ${layer.type} layer`}
                    >
                      <input
                        type="checkbox"
                        checked={isVisible}
                        onChange={() => {}}
                        className="gerber-layer-checkbox"
                      />
                      <span
                        className={`gerber-layer-indicator gerber-layer-${layer.type}`}
                      />
                      <span className="gerber-layer-name" title={layer.filename}>
                        {layer.type}
                      </span>
                      <span className="gerber-layer-side">
                        {layer.side}
                      </span>
                    </button>
                  );
                })}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
