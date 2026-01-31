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

import { useEffect, useState, useCallback } from 'react';
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
} from 'lucide-react';
import JSZip from 'jszip';
import './GerberViewer.css';

interface GerberViewerProps {
  src: string;
  className?: string;
  style?: React.CSSProperties;
}

type ViewSide = 'top' | 'bottom';

export default function GerberViewer({ src, className, style }: GerberViewerProps) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [topSvg, setTopSvg] = useState<string | null>(null);
  const [bottomSvg, setBottomSvg] = useState<string | null>(null);
  const [layers, setLayers] = useState<Layer[]>([]);
  const [viewSide, setViewSide] = useState<ViewSide>('top');
  const [layersPanelCollapsed, setLayersPanelCollapsed] = useState(true);

  useEffect(() => {
    const loadGerbers = async () => {
      setLoading(true);
      setError(null);

      try {
        // Fetch the zip file
        console.log('[GerberViewer] Fetching:', src);
        const response = await fetch(src);
        if (!response.ok) {
          throw new Error(`Failed to fetch gerbers: ${response.status} ${response.statusText}`);
        }

        const arrayBuffer = await response.arrayBuffer();
        console.log('[GerberViewer] Received', arrayBuffer.byteLength, 'bytes');
        const zip = await JSZip.loadAsync(arrayBuffer);

        // Extract files from zip as File objects
        const files: File[] = [];
        const allEntries = Object.keys(zip.files);
        console.log('[GerberViewer] Zip contains', allEntries.length, 'entries:', allEntries);

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
            console.log('[GerberViewer] Skipping non-gerber file:', baseName, 'ext:', ext);
            continue;
          }

          // Get content as text string first (gerbers are text files)
          const textContent = await zipEntry.async('string');
          // Create File with text/plain type for proper FileReader handling
          const file = new File([textContent], baseName, { type: 'text/plain' });
          files.push(file);
          console.log('[GerberViewer] Added file:', baseName, 'size:', textContent.length, 'preview:', textContent.substring(0, 50));
        }

        if (files.length === 0) {
          throw new Error('No valid gerber files found in archive');
        }

        console.log('[GerberViewer] Processing', files.length, 'gerber files with tracespace');

        // Use tracespace pipeline
        const readResult = await read(files);
        console.log('[GerberViewer] Read result - layers:', readResult.layers.length, readResult.layers.map(l => `${l.type}:${l.side}`));

        const plotResult = plot(readResult);
        console.log('[GerberViewer] Plot result:', Object.keys(plotResult));

        const renderLayersResult = renderLayers(plotResult);
        console.log('[GerberViewer] Render layers result:', Object.keys(renderLayersResult));

        const boardResult = renderBoard(renderLayersResult);
        console.log('[GerberViewer] Board result - top:', !!boardResult.top, 'bottom:', !!boardResult.bottom);

        // Convert to SVG strings
        const topSvgStr = stringifySvg(boardResult.top);
        const bottomSvgStr = stringifySvg(boardResult.bottom);

        console.log('[GerberViewer] SVG lengths - top:', topSvgStr.length, 'bottom:', bottomSvgStr.length);

        // Debug: Log first 500 chars of top SVG to see its structure
        if (topSvgStr) {
          console.log('[GerberViewer] Top SVG preview:', topSvgStr.substring(0, 500));
        }

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

  const currentSvg = viewSide === 'top' ? topSvg : bottomSvg;

  // Debug: log when SVG changes
  useEffect(() => {
    console.log('[GerberViewer] currentSvg changed, length:', currentSvg?.length || 0, 'viewSide:', viewSide);
  }, [currentSvg, viewSide]);

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
    <div className={`gerber-viewer ${className || ''}`} style={style}>
      <TransformWrapper
        initialScale={1}
        minScale={0.1}
        maxScale={20}
        centerOnInit
        wheel={{ smoothStep: 0.05 }}
        panning={{ velocityDisabled: true }}
        doubleClick={{ disabled: true }}
      >
        {({ zoomIn, zoomOut, resetTransform, instance }) => (
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
                  onClick={() => resetTransform()}
                  title="Reset view"
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
            </div>
          </>
        )}
      </TransformWrapper>

      {/* Layers panel */}
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
              {layers.map((layer) => (
                <div key={layer.id} className="gerber-layer-item">
                  <span
                    className={`gerber-layer-indicator gerber-layer-${layer.type}`}
                  />
                  <span className="gerber-layer-name" title={layer.filename}>
                    {layer.type}
                  </span>
                  <span className="gerber-layer-side">
                    {layer.side}
                  </span>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
