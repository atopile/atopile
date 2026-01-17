/**
 * Export menu component for saving the visualization.
 *
 * Supports PNG, SVG, and JSON export formats.
 */

import { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { useGraphStore } from '../stores/graphStore';
import { useFilterStore } from '../stores/filterStore';
import { useCollapseStore } from '../stores/collapseStore';
import { computeVisibleNodes, computeVisibleEdges } from '../lib/filterEngine';
import { exportToPng, exportToSvg, exportToJson } from '../lib/exportUtils';

export function ExportMenu() {
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const { data, index, positions } = useGraphStore();
  const { config } = useFilterStore();
  const { state: collapseState } = useCollapseStore();

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [isOpen]);

  // Compute visible sets
  const { visibleNodes, visibleEdges } = useMemo(() => {
    if (!data || !index) {
      return { visibleNodes: new Set<string>(), visibleEdges: new Set<string>() };
    }
    const visibleNodes = computeVisibleNodes(data, index, config, collapseState);
    const visibleEdges = computeVisibleEdges(data, config, visibleNodes);
    return { visibleNodes, visibleEdges };
  }, [data, index, config, collapseState]);

  const handleExportPng = useCallback(() => {
    const canvas = document.querySelector('canvas');
    if (canvas) {
      const timestamp = new Date().toISOString().slice(0, 10);
      exportToPng(canvas, `graph-${timestamp}.png`);
    }
    setIsOpen(false);
  }, []);

  const handleExportSvg = useCallback(() => {
    if (!data) return;
    const timestamp = new Date().toISOString().slice(0, 10);
    exportToSvg(data, positions, visibleNodes, visibleEdges, {
      filename: `graph-${timestamp}.svg`,
    });
    setIsOpen(false);
  }, [data, positions, visibleNodes, visibleEdges]);

  const handleExportJson = useCallback(() => {
    if (!data) return;
    const timestamp = new Date().toISOString().slice(0, 10);
    exportToJson(data, positions, visibleNodes, visibleEdges, `graph-${timestamp}.json`);
    setIsOpen(false);
  }, [data, positions, visibleNodes, visibleEdges]);

  if (!data) return null;

  return (
    <div ref={menuRef} className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="p-2 text-text-secondary hover:text-text-primary hover:bg-panel-border rounded transition-colors"
        title="Export visualization"
      >
        <svg
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
          <polyline points="7 10 12 15 17 10" />
          <line x1="12" y1="15" x2="12" y2="3" />
        </svg>
      </button>

      {isOpen && (
        <div className="absolute right-0 top-full mt-1 w-48 bg-panel-bg border border-panel-border rounded-lg shadow-xl z-50 overflow-hidden">
          <div className="p-2 border-b border-panel-border">
            <span className="text-xs font-medium text-text-secondary">
              Export As
            </span>
          </div>

          <div className="p-1">
            <button
              onClick={handleExportPng}
              className="w-full flex items-center gap-3 px-3 py-2 text-sm text-text-primary hover:bg-panel-border rounded transition-colors"
            >
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <rect x="3" y="3" width="18" height="18" rx="2" />
                <circle cx="8.5" cy="8.5" r="1.5" />
                <path d="M21 15l-5-5L5 21" />
              </svg>
              <span>PNG Image</span>
              <span className="ml-auto text-xs text-text-secondary">
                Screenshot
              </span>
            </button>

            <button
              onClick={handleExportSvg}
              className="w-full flex items-center gap-3 px-3 py-2 text-sm text-text-primary hover:bg-panel-border rounded transition-colors"
            >
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
                <line x1="16" y1="13" x2="8" y2="13" />
                <line x1="16" y1="17" x2="8" y2="17" />
              </svg>
              <span>SVG Vector</span>
              <span className="ml-auto text-xs text-text-secondary">2D</span>
            </button>

            <button
              onClick={handleExportJson}
              className="w-full flex items-center gap-3 px-3 py-2 text-sm text-text-primary hover:bg-panel-border rounded transition-colors"
            >
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
                <path d="M10 12a1 1 0 0 0-1 1v1a1 1 0 0 1-1 1 1 1 0 0 1 1 1v1a1 1 0 0 0 1 1" />
                <path d="M14 18a1 1 0 0 0 1-1v-1a1 1 0 0 1 1-1 1 1 0 0 1-1-1v-1a1 1 0 0 0-1-1" />
              </svg>
              <span>JSON Data</span>
              <span className="ml-auto text-xs text-text-secondary">
                + positions
              </span>
            </button>
          </div>

          <div className="p-2 border-t border-panel-border bg-graph-bg/50">
            <span className="text-[10px] text-text-secondary">
              Exporting {visibleNodes.size} nodes, {visibleEdges.size} edges
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
