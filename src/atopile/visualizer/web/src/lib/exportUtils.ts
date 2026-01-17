/**
 * Utilities for exporting the graph visualization.
 *
 * Supports PNG export from Three.js canvas and SVG generation.
 */

import type { GraphData, NodePosition } from '../types/graph';

/**
 * Export the Three.js canvas as a PNG image.
 */
export function exportToPng(
  canvas: HTMLCanvasElement,
  filename: string = 'graph.png'
): void {
  // Get data URL from canvas
  const dataUrl = canvas.toDataURL('image/png');

  // Create download link
  const link = document.createElement('a');
  link.download = filename;
  link.href = dataUrl;
  link.click();
}

/**
 * Export the graph as an SVG file.
 * Creates a 2D projection of the graph for SVG export.
 */
export function exportToSvg(
  data: GraphData,
  positions: Map<string, NodePosition>,
  visibleNodes: Set<string>,
  visibleEdges: Set<string>,
  options: {
    width?: number;
    height?: number;
    padding?: number;
    nodeRadius?: number;
    filename?: string;
  } = {}
): void {
  const {
    width = 1920,
    height = 1080,
    padding = 50,
    nodeRadius = 5,
    filename = 'graph.svg',
  } = options;

  // Calculate bounds from positions
  let minX = Infinity,
    maxX = -Infinity;
  let minY = Infinity,
    maxY = -Infinity;

  for (const nodeId of visibleNodes) {
    const pos = positions.get(nodeId);
    if (pos) {
      minX = Math.min(minX, pos.x);
      maxX = Math.max(maxX, pos.x);
      minY = Math.min(minY, pos.y);
      maxY = Math.max(maxY, pos.y);
    }
  }

  // Scale to fit
  const graphWidth = maxX - minX || 1;
  const graphHeight = maxY - minY || 1;
  const availableWidth = width - padding * 2;
  const availableHeight = height - padding * 2;
  const scale = Math.min(availableWidth / graphWidth, availableHeight / graphHeight);

  const scaleX = (x: number) => padding + (x - minX) * scale;
  const scaleY = (y: number) => padding + (y - minY) * scale;

  // Color map for node types
  const typeColors: Record<string, string> = {
    Resistor: '#22c55e',
    Capacitor: '#3b82f6',
    Inductor: '#a855f7',
    LED: '#eab308',
    Diode: '#f97316',
    Electrical: '#06b6d4',
    ElectricPower: '#ef4444',
    ElectricLogic: '#8b5cf6',
    I2C: '#ec4899',
    SPI: '#f43f5e',
    UART: '#84cc16',
    USB: '#6366f1',
    default: '#9ca3af',
  };

  const getNodeColor = (typeName: string | null): string => {
    if (!typeName) return typeColors.default;
    if (typeColors[typeName]) return typeColors[typeName];
    for (const [key, color] of Object.entries(typeColors)) {
      if (typeName.includes(key)) return color;
    }
    return typeColors.default;
  };

  // Edge type colors
  const edgeColors: Record<string, string> = {
    composition: '#22c55e',
    connection: '#3b82f6',
    trait: '#a855f7',
    pointer: '#64748b',
    operand: '#f97316',
    type: '#06b6d4',
    next: '#eab308',
  };

  // Build SVG elements
  const svgParts: string[] = [];

  // SVG header
  svgParts.push(
    `<?xml version="1.0" encoding="UTF-8"?>`,
    `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">`,
    `  <rect width="100%" height="100%" fill="#0f172a"/>`,
    `  <g id="edges">`
  );

  // Draw edges
  for (const edgeId of visibleEdges) {
    const edge = data.edges.find((e) => e.id === edgeId);
    if (!edge) continue;

    const sourcePos = positions.get(edge.source);
    const targetPos = positions.get(edge.target);

    if (!sourcePos || !targetPos) continue;
    if (!visibleNodes.has(edge.source) || !visibleNodes.has(edge.target)) continue;

    const x1 = scaleX(sourcePos.x);
    const y1 = scaleY(sourcePos.y);
    const x2 = scaleX(targetPos.x);
    const y2 = scaleY(targetPos.y);

    const color = edgeColors[edge.type] || '#64748b';
    const opacity = edge.type === 'composition' ? 0.6 : 0.3;

    svgParts.push(
      `    <line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${color}" stroke-opacity="${opacity}" stroke-width="1"/>`
    );
  }

  svgParts.push(`  </g>`, `  <g id="nodes">`);

  // Draw nodes
  const nodesById = new Map(data.nodes.map((n) => [n.id, n]));

  for (const nodeId of visibleNodes) {
    const node = nodesById.get(nodeId);
    const pos = positions.get(nodeId);

    if (!node || !pos) continue;

    const x = scaleX(pos.x);
    const y = scaleY(pos.y);
    const color = getNodeColor(node.typeName);
    const radius = node.childCount > 10 ? nodeRadius * 1.5 : nodeRadius;

    svgParts.push(
      `    <circle cx="${x}" cy="${y}" r="${radius}" fill="${color}"/>`
    );
  }

  svgParts.push(`  </g>`, `</svg>`);

  // Create and download file
  const svgContent = svgParts.join('\n');
  const blob = new Blob([svgContent], { type: 'image/svg+xml' });
  const url = URL.createObjectURL(blob);

  const link = document.createElement('a');
  link.download = filename;
  link.href = url;
  link.click();

  URL.revokeObjectURL(url);
}

/**
 * Export graph data as JSON for external tools.
 */
export function exportToJson(
  data: GraphData,
  positions: Map<string, NodePosition>,
  visibleNodes: Set<string>,
  visibleEdges: Set<string>,
  filename: string = 'graph-data.json'
): void {
  const exportData = {
    metadata: data.metadata,
    nodes: data.nodes
      .filter((n) => visibleNodes.has(n.id))
      .map((n) => ({
        ...n,
        position: positions.get(n.id),
      })),
    edges: data.edges.filter((e) => visibleEdges.has(e.id)),
    exportedAt: new Date().toISOString(),
  };

  const json = JSON.stringify(exportData, null, 2);
  const blob = new Blob([json], { type: 'application/json' });
  const url = URL.createObjectURL(blob);

  const link = document.createElement('a');
  link.download = filename;
  link.href = url;
  link.click();

  URL.revokeObjectURL(url);
}
