import { useState, useRef, useEffect, useCallback } from 'react';
import { Badge } from '../shared/Badge';
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '../shared/Table';
import type { StackupLayer } from './StackupViewer';

const MIN_HEIGHT_PX = 4;

const LAYER_COLORS: Record<string, string> = {
  COPPER: 'var(--ctp-peach)',
  CORE: 'var(--ctp-green)',
  SUBSTRATE: 'var(--ctp-green)',
  SOLDER_MASK: 'var(--ctp-teal)',
  SILK_SCREEN: 'var(--ctp-lavender)',
  PASTE: 'var(--ctp-overlay1)',
  PREPREG: 'var(--ctp-sapphire)',
};

function getLayerColor(layerType: string | null): string {
  const key = layerType?.toUpperCase() ?? '';
  return LAYER_COLORS[key] ?? 'var(--ctp-overlay0)';
}

function getLayerBadgeVariant(layerType: string | null) {
  switch (layerType?.toUpperCase()) {
    case 'COPPER':
      return 'warning' as const;
    case 'CORE':
    case 'SUBSTRATE':
    case 'PREPREG':
      return 'success' as const;
    case 'SOLDER_MASK':
      return 'info' as const;
    default:
      return 'secondary' as const;
  }
}

function formatThickness(mm: number | null): string {
  if (mm == null) return '-';
  if (mm >= 0.1) return `${mm.toFixed(2)} mm`;
  return `${(mm * 1000).toFixed(0)} \u00b5m`;
}

interface StackupCrossSectionProps {
  layers: StackupLayer[];
  totalThicknessMm: number;
}

export function StackupCrossSection({
  layers,
  totalThicknessMm,
}: StackupCrossSectionProps) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [availableHeight, setAvailableHeight] = useState(600);
  const rowRefs = useRef<(HTMLTableRowElement | null)[]>([]);

  const updateHeight = useCallback(() => {
    if (containerRef.current) {
      setAvailableHeight(containerRef.current.clientHeight);
    }
  }, []);

  useEffect(() => {
    updateHeight();
    const observer = new ResizeObserver(updateHeight);
    if (containerRef.current) {
      observer.observe(containerRef.current);
    }
    return () => observer.disconnect();
  }, [updateHeight]);

  // Calculate scale: pixels per mm
  const scaleFactor =
    totalThicknessMm > 0 ? availableHeight / totalThicknessMm : 1;

  // Compute heights with minimum
  const layerHeights = layers.map((layer) => {
    const thickness = layer.thicknessMm ?? 0;
    return Math.max(thickness * scaleFactor, MIN_HEIGHT_PX);
  });

  const handleHover = useCallback((index: number | null) => {
    setHoveredIndex(index);
  }, []);

  return (
    <div className="stackup-body">
      <div className="stackup-cross-section" ref={containerRef}>
        <div className="stackup-layers">
          {layers.map((layer, i) => {
            const color = getLayerColor(layer.layerType);
            const isHovered = hoveredIndex === i;
            return (
              <div
                key={layer.index}
                className={`stackup-layer${isHovered ? ' stackup-layer--hovered' : ''}`}
                style={{
                  height: `${layerHeights[i]}px`,
                  backgroundColor: color,
                }}
                onMouseEnter={() => handleHover(i)}
                onMouseLeave={() => handleHover(null)}
              >
                {layerHeights[i] >= 14 && (
                  <span className="stackup-layer-label">
                    {layer.layerType ?? '?'}
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </div>

      <div className="stackup-table-panel">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>#</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Material</TableHead>
              <TableHead>Thickness</TableHead>
              <TableHead>{'\u03b5r'}</TableHead>
              <TableHead>tan{'\u03b4'}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {layers.map((layer, i) => {
              const isHovered = hoveredIndex === i;
              return (
                <TableRow
                  key={layer.index}
                  ref={(el: HTMLTableRowElement | null) => {
                    rowRefs.current[i] = el;
                  }}
                  className={isHovered ? 'table-row--hovered' : ''}
                  onMouseEnter={() => handleHover(i)}
                  onMouseLeave={() => handleHover(null)}
                >
                  <TableCell>{layer.index}</TableCell>
                  <TableCell>
                    <div className="stackup-swatch-cell">
                      <span
                        className="stackup-swatch"
                        style={{ backgroundColor: getLayerColor(layer.layerType) }}
                      />
                      <Badge variant={getLayerBadgeVariant(layer.layerType)}>
                        {layer.layerType ?? 'Unknown'}
                      </Badge>
                    </div>
                  </TableCell>
                  <TableCell>
                    {layer.material ?? <span className="stackup-null">-</span>}
                  </TableCell>
                  <TableCell>{formatThickness(layer.thicknessMm)}</TableCell>
                  <TableCell>
                    {layer.relativePermittivity != null ? (
                      layer.relativePermittivity.toFixed(2)
                    ) : (
                      <span className="stackup-null">-</span>
                    )}
                  </TableCell>
                  <TableCell>
                    {layer.lossTangent != null ? (
                      layer.lossTangent.toFixed(4)
                    ) : (
                      <span className="stackup-null">-</span>
                    )}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
