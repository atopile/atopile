/**
 * GerberViewer - Renders Gerber files using tracespace.
 *
 * This component fetches a gerber zip file, extracts the gerber files,
 * and renders them as layered SVGs using the tracespace library.
 */

import { useEffect, useState, useMemo } from 'react';
import { createParser, Root } from '@tracespace/parser';
import { plot, ImageTree } from '@tracespace/plotter';
import { render, sizeToViewBox, SvgElement } from '@tracespace/renderer';
import { toHtml } from 'hast-util-to-html';
import { Loader2, AlertCircle, Layers } from 'lucide-react';
import JSZip from 'jszip';

interface GerberViewerProps {
  src: string;
  className?: string;
  style?: React.CSSProperties;
}

interface GerberLayer {
  name: string;
  type: 'copper' | 'soldermask' | 'silkscreen' | 'paste' | 'drill' | 'outline' | 'other';
  side: 'top' | 'bottom' | 'inner' | 'all';
  svg: string;
  viewBox: [number, number, number, number] | null;
  visible: boolean;
}

// Layer type detection based on filename patterns
function detectLayerType(filename: string): { type: GerberLayer['type']; side: GerberLayer['side'] } {
  const lower = filename.toLowerCase();

  // Copper layers
  if (lower.includes('f.cu') || lower.includes('gtl') || (lower.includes('top') && lower.includes('copper'))) {
    return { type: 'copper', side: 'top' };
  }
  if (lower.includes('b.cu') || lower.includes('gbl') || (lower.includes('bottom') && lower.includes('copper'))) {
    return { type: 'copper', side: 'bottom' };
  }
  if (lower.includes('.cu') || lower.includes('inner') || lower.includes('in1') || lower.includes('in2')) {
    return { type: 'copper', side: 'inner' };
  }

  // Soldermask
  if (lower.includes('f.mask') || lower.includes('gts') || (lower.includes('soldermask') && lower.includes('top'))) {
    return { type: 'soldermask', side: 'top' };
  }
  if (lower.includes('b.mask') || lower.includes('gbs') || (lower.includes('soldermask') && lower.includes('bottom'))) {
    return { type: 'soldermask', side: 'bottom' };
  }

  // Silkscreen
  if (lower.includes('f.silk') || lower.includes('gto') || (lower.includes('silkscreen') && lower.includes('top'))) {
    return { type: 'silkscreen', side: 'top' };
  }
  if (lower.includes('b.silk') || lower.includes('gbo') || (lower.includes('silkscreen') && lower.includes('bottom'))) {
    return { type: 'silkscreen', side: 'bottom' };
  }

  // Paste
  if (lower.includes('f.paste') || lower.includes('gtp')) {
    return { type: 'paste', side: 'top' };
  }
  if (lower.includes('b.paste') || lower.includes('gbp')) {
    return { type: 'paste', side: 'bottom' };
  }

  // Edge cuts / outline
  if (lower.includes('edge') || lower.includes('outline') || lower.includes('gko') || lower.includes('gm1')) {
    return { type: 'outline', side: 'all' };
  }

  // Drill
  if (lower.includes('drill') || lower.includes('.drl') || lower.includes('.xln')) {
    return { type: 'drill', side: 'all' };
  }

  return { type: 'other', side: 'all' };
}

// Layer colors based on type
function getLayerColor(type: GerberLayer['type'], side: GerberLayer['side']): string {
  switch (type) {
    case 'copper':
      return side === 'top' ? '#C87533' : '#B87333';
    case 'soldermask':
      return side === 'top' ? 'rgba(0, 128, 0, 0.6)' : 'rgba(0, 100, 0, 0.6)';
    case 'silkscreen':
      return '#FFFFFF';
    case 'paste':
      return '#C0C0C0';
    case 'outline':
      return '#FFFF00';
    case 'drill':
      return '#000000';
    default:
      return '#808080';
  }
}

export default function GerberViewer({ src, className, style }: GerberViewerProps) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [layers, setLayers] = useState<GerberLayer[]>([]);
  const [viewBox, setViewBox] = useState<string>('0 0 100 100');

  useEffect(() => {
    const loadGerbers = async () => {
      setLoading(true);
      setError(null);

      try {
        // Fetch the zip file
        const response = await fetch(src);
        if (!response.ok) {
          throw new Error(`Failed to fetch gerbers: ${response.statusText}`);
        }

        const arrayBuffer = await response.arrayBuffer();
        const zip = await JSZip.loadAsync(arrayBuffer);

        const parsedLayers: GerberLayer[] = [];
        let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;

        // Process each file in the zip
        for (const [filename, zipEntry] of Object.entries(zip.files)) {
          if (zipEntry.dir) continue;

          // Skip non-gerber files
          const ext = filename.toLowerCase().split('.').pop();
          if (!ext || !['gbr', 'ger', 'gtl', 'gbl', 'gts', 'gbs', 'gto', 'gbo', 'gtp', 'gbp', 'gko', 'gm1', 'drl', 'xln', 'exc'].includes(ext)) {
            // Also check for KiCad naming
            if (!filename.includes('-') && !filename.includes('.')) continue;
          }

          try {
            const content = await zipEntry.async('string');
            const { type, side } = detectLayerType(filename);

            // Parse the gerber file using createParser
            const parser = createParser();
            parser.feed(content);
            const parsed: Root = parser.results();

            // Plot to image tree (use any to avoid type compatibility issues between package versions)
            const plotted: ImageTree = plot(parsed as Parameters<typeof plot>[0]);

            // Get viewBox from plotted image
            let layerViewBox: [number, number, number, number] | null = null;
            if (plotted.size) {
              layerViewBox = sizeToViewBox(plotted.size);
              const [vx, vy, vw, vh] = layerViewBox;
              minX = Math.min(minX, vx);
              minY = Math.min(minY, vy);
              maxX = Math.max(maxX, vx + vw);
              maxY = Math.max(maxY, vy + vh);
            }

            // Render to SVG element (HAST)
            const svgElement: SvgElement = render(plotted);

            // Convert HAST to HTML string (cast to avoid type compatibility issues)
            const svg = toHtml(svgElement as Parameters<typeof toHtml>[0]);

            parsedLayers.push({
              name: filename,
              type,
              side,
              svg,
              viewBox: layerViewBox,
              visible: type !== 'paste', // Hide paste by default
            });
          } catch (parseError) {
            console.warn(`Failed to parse ${filename}:`, parseError);
          }
        }

        if (parsedLayers.length === 0) {
          throw new Error('No valid gerber files found in archive');
        }

        // Sort layers by rendering order
        const layerOrder = ['outline', 'drill', 'copper', 'soldermask', 'silkscreen', 'paste', 'other'];
        parsedLayers.sort((a, b) => {
          const aOrder = layerOrder.indexOf(a.type);
          const bOrder = layerOrder.indexOf(b.type);
          return aOrder - bOrder;
        });

        setLayers(parsedLayers);

        // Set combined viewBox
        if (minX !== Infinity) {
          const padding = 1;
          setViewBox(`${minX - padding} ${minY - padding} ${maxX - minX + padding * 2} ${maxY - minY + padding * 2}`);
        }

      } catch (err) {
        console.error('Error loading gerbers:', err);
        setError(err instanceof Error ? err.message : 'Failed to load gerbers');
      } finally {
        setLoading(false);
      }
    };

    loadGerbers();
  }, [src]);

  const toggleLayer = (index: number) => {
    setLayers(prev => prev.map((layer, i) =>
      i === index ? { ...layer, visible: !layer.visible } : layer
    ));
  };

  // Combine visible layers into a single SVG
  const combinedSvg = useMemo(() => {
    const visibleLayers = layers.filter(l => l.visible);
    if (visibleLayers.length === 0) return null;

    // Extract inner content from each SVG
    const layerContents = visibleLayers.map(layer => {
      // Extract the content between <svg> tags
      const match = layer.svg.match(/<svg[^>]*>([\s\S]*)<\/svg>/);
      if (match) {
        const color = getLayerColor(layer.type, layer.side);
        // Wrap in a group with the layer color
        return `<g style="color: ${color}; fill: currentColor; stroke: currentColor;">${match[1]}</g>`;
      }
      return '';
    });

    return layerContents.join('\n');
  }, [layers]);

  if (loading) {
    return (
      <div className={`gerber-viewer gerber-viewer-loading ${className || ''}`} style={style}>
        <Loader2 className="spinning" size={24} />
        <span>Loading gerbers...</span>
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

  return (
    <div className={`gerber-viewer ${className || ''}`} style={style}>
      <div className="gerber-viewer-container">
        <svg
          viewBox={viewBox}
          className="gerber-svg"
          style={{ background: '#1a1a2e' }}
          dangerouslySetInnerHTML={{ __html: combinedSvg || '' }}
        />
      </div>
      <div className="gerber-layer-controls">
        <div className="gerber-layer-title">
          <Layers size={14} />
          Layers
        </div>
        {layers.map((layer, index) => (
          <label key={layer.name} className="gerber-layer-toggle">
            <input
              type="checkbox"
              checked={layer.visible}
              onChange={() => toggleLayer(index)}
            />
            <span
              className="gerber-layer-color"
              style={{ background: getLayerColor(layer.type, layer.side) }}
            />
            <span className="gerber-layer-name" title={layer.name}>
              {layer.type} ({layer.side})
            </span>
          </label>
        ))}
      </div>
    </div>
  );
}
