/**
 * Top toolbar with layout, view, and search controls.
 */

import { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import { useGraphStore } from '../stores/graphStore';
import { useViewStore, type ColorScheme } from '../stores/viewStore';
import { useSelectionStore } from '../stores/selectionStore';
import { useFilterStore } from '../stores/filterStore';
import { useCollapseStore } from '../stores/collapseStore';
import { useNavigationStore } from '../stores/navigationStore';
import { computeVisibleNodesWithNavigation, computeVisibleEdges } from '../lib/filterEngine';
import { HelpButton } from './HelpPanel';
import { ExportMenu } from './ExportMenu';
import { AtopileLogo } from './AtopileLogo';

const COLOR_SCHEME_OPTIONS: Array<{ value: ColorScheme; label: string }> = [
  { value: 'type', label: 'Type' },
  { value: 'depth', label: 'Depth' },
  { value: 'trait', label: 'Trait' },
  { value: 'parent', label: 'Parent' },
];

export function Toolbar() {
  const { data, index, runLayout, isLayoutRunning, layoutProgress, bounds, cancelLayout } =
    useGraphStore();
  const { zoom, showLabels, toggleLabels, fitToView, resetView, colorScheme, setColorScheme } = useViewStore();
  const { selectedNodes, clearSelection, setFocusedNode } =
    useSelectionStore();
  const { setReachability, config } = useFilterStore();
  const { state: collapseState } = useCollapseStore();
  const { currentRootId, viewDepth, depthEnabled } = useNavigationStore();

  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<
    Array<{ id: string; name: string | null; typeName: string | null }>
  >([]);
  const [showSearchResults, setShowSearchResults] = useState(false);
  const [reachabilityHops, setReachabilityHops] = useState(3);
  const [dropdownPosition, setDropdownPosition] = useState<{ top: number; left: number } | null>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const searchContainerRef = useRef<HTMLDivElement>(null);

  // Compute visible nodes for search filtering and layout
  const visibleNodes = useMemo(() => {
    if (!data || !index) return new Set<string>();
    const navigation = { currentRootId, viewDepth, depthEnabled };
    return computeVisibleNodesWithNavigation(data, index, config, collapseState, navigation);
  }, [data, index, config, collapseState, currentRootId, viewDepth, depthEnabled]);

  // Compute visible edges for layout
  const visibleEdges = useMemo(() => {
    if (!data) return new Set<string>();
    return computeVisibleEdges(data, config, visibleNodes);
  }, [data, config, visibleNodes]);

  // Global keyboard shortcut for search focus (Ctrl+K or Cmd+K)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        searchInputRef.current?.focus();
        searchInputRef.current?.select();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Search functionality - only searches visible nodes
  // Shows results on focus even without query
  useEffect(() => {
    if (!data) {
      setSearchResults([]);
      return;
    }

    const query = searchQuery.toLowerCase().trim();

    // Filter visible nodes, optionally matching query
    const results = data.nodes
      .filter((node) => {
        if (!visibleNodes.has(node.id)) return false;
        if (!query) return true; // Show all visible nodes when no query

        return (
          node.name?.toLowerCase().includes(query) ||
          node.typeName?.toLowerCase().includes(query) ||
          node.id.toLowerCase().includes(query)
        );
      })
      .slice(0, 20)
      .map((n) => ({ id: n.id, name: n.name, typeName: n.typeName }));

    setSearchResults(results);
  }, [data, searchQuery, visibleNodes]);

  // Calculate dropdown position when showing results
  useEffect(() => {
    if (showSearchResults && searchContainerRef.current) {
      const rect = searchContainerRef.current.getBoundingClientRect();
      setDropdownPosition({
        top: rect.bottom + 4,
        left: rect.left,
      });
    }
  }, [showSearchResults]);

  const handleSearchSelect = useCallback(
    (nodeId: string) => {
      setFocusedNode(nodeId);
      setSearchQuery('');
      setShowSearchResults(false);
    },
    [setFocusedNode]
  );

  const handleSearchKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && searchResults.length > 0) {
        handleSearchSelect(searchResults[0].id);
      } else if (e.key === 'Escape') {
        setShowSearchResults(false);
        searchInputRef.current?.blur();
      }
    },
    [searchResults, handleSearchSelect]
  );

  const handleReachability = useCallback(() => {
    if (selectedNodes.size === 0) return;

    setReachability(
      true,
      selectedNodes,
      new Set(['composition', 'connection']),
      reachabilityHops
    );
  }, [selectedNodes, setReachability, reachabilityHops]);

  const handleClearReachability = useCallback(() => {
    setReachability(false);
  }, [setReachability]);

  if (!data) return null;

  return (
    <div className="h-14 bg-gradient-to-r from-panel-bg to-panel-bg/95 border-b border-panel-border px-4 flex items-center gap-3 shadow-sm flex-shrink-0 overflow-hidden">
      {/* Logo and title */}
      <div className="flex items-center gap-2 pr-3 border-r border-panel-border/50">
        <AtopileLogo size={28} className="text-[#f95015]" />
        <div className="flex flex-col">
          <span className="text-sm font-semibold text-text-primary leading-none">atopile</span>
          <span className="text-[10px] text-text-secondary leading-none">graph viewer</span>
        </div>
      </div>

      {/* Search */}
      <div className="relative" ref={searchContainerRef}>
        <div className="flex items-center gap-2">
          <div className="relative">
            <input
              ref={searchInputRef}
              type="text"
              placeholder="Search nodes... (Ctrl+K)"
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setShowSearchResults(true);
              }}
              onFocus={() => setShowSearchResults(true)}
              onBlur={() => setTimeout(() => setShowSearchResults(false), 200)}
              onKeyDown={handleSearchKeyDown}
              className="w-56 px-3 py-1.5 text-sm bg-graph-bg border border-panel-border rounded text-text-primary placeholder-text-secondary focus:outline-none focus:border-accent"
            />
            {searchQuery && (
              <button
                onClick={() => {
                  setSearchQuery('');
                  setSearchResults([]);
                }}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-text-secondary hover:text-text-primary"
              >
                <svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor">
                  <path d="M3 3l8 8M11 3l-8 8" stroke="currentColor" strokeWidth="1.5" />
                </svg>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Search results dropdown - rendered with fixed position to escape overflow:hidden */}
      {showSearchResults && searchResults.length > 0 && dropdownPosition && (
        <div
          className="fixed w-72 bg-panel-bg border border-panel-border rounded shadow-xl max-h-64 overflow-y-auto z-[9999]"
          style={{ top: dropdownPosition.top, left: dropdownPosition.left }}
        >
          {searchResults.map((result) => (
            <button
              key={result.id}
              onClick={() => handleSearchSelect(result.id)}
              className="w-full px-3 py-2 text-left text-sm hover:bg-panel-border transition-colors flex items-center gap-2"
            >
              <span className="text-text-primary truncate flex-1">
                {result.name || result.id}
              </span>
              {result.typeName && (
                <span className="text-xs text-text-secondary truncate max-w-[100px]">
                  {result.typeName}
                </span>
              )}
            </button>
          ))}
        </div>
      )}

      <div className="h-8 w-px bg-panel-border/50" />

      {/* Layout controls */}
      <div className="flex items-center gap-1.5">
        <button
          onClick={() => (isLayoutRunning ? cancelLayout() : runLayout(visibleNodes, visibleEdges))}
          className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all flex items-center gap-2 ${
            isLayoutRunning
              ? 'bg-red-500/20 text-red-400 hover:bg-red-500/30 border border-red-500/30'
              : 'bg-panel-border/80 hover:bg-panel-border text-text-primary border border-transparent'
          }`}
        >
          {isLayoutRunning ? (
            <>
              <span className="w-3 h-3 border-2 border-red-400 border-t-transparent rounded-full animate-spin" />
              Cancel ({Math.round(layoutProgress * 100)}%)
            </>
          ) : (
            <>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="3" />
                <path d="M12 2v4M12 18v4M2 12h4M18 12h4" />
                <path d="M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
              </svg>
              Layout
            </>
          )}
        </button>
        <button
          onClick={() => fitToView(bounds)}
          className="px-3 py-1.5 text-xs font-medium bg-panel-border/80 rounded-md hover:bg-panel-border transition-all text-text-primary border border-transparent"
          title="Fit to view (F)"
        >
          Fit
        </button>
        <button
          onClick={resetView}
          className="px-3 py-1.5 text-xs font-medium bg-panel-border/80 rounded-md hover:bg-panel-border transition-all text-text-primary border border-transparent"
          title="Reset view (H)"
        >
          Home
        </button>
      </div>

      <div className="h-8 w-px bg-panel-border/50" />

      {/* View options */}
      <div className="flex items-center gap-2">
        <button
          onClick={toggleLabels}
          className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
            showLabels
              ? 'bg-accent text-white shadow-sm'
              : 'bg-panel-border/80 hover:bg-panel-border text-text-primary border border-transparent'
          }`}
          title="Toggle labels (L)"
        >
          Labels
        </button>
        <div className="flex items-center gap-1.5 px-2 py-1 bg-panel-border/50 rounded-md">
          <span className="text-[10px] text-text-secondary uppercase tracking-wider">Color</span>
          <select
            value={colorScheme}
            onChange={(e) => setColorScheme(e.target.value as ColorScheme)}
            className="px-2 py-0.5 text-xs bg-graph-bg border border-panel-border/50 rounded text-text-primary cursor-pointer focus:outline-none focus:border-accent"
          >
            {COLOR_SCHEME_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
        <span className="text-xs text-text-secondary px-2 py-1 bg-graph-bg/50 rounded tabular-nums font-mono">
          {(zoom * 100).toFixed(0)}%
        </span>
      </div>

      <div className="h-8 w-px bg-panel-border/50" />

      {/* Reachability */}
      <div className="flex items-center gap-1.5 px-2 py-1 bg-panel-border/30 rounded-md">
        <span className="text-[10px] text-text-secondary uppercase tracking-wider">Reach</span>
        <input
          type="number"
          min={1}
          max={10}
          value={reachabilityHops}
          onChange={(e) => setReachabilityHops(parseInt(e.target.value) || 3)}
          className="w-10 px-1.5 py-0.5 text-xs bg-graph-bg border border-panel-border/50 rounded text-text-primary text-center focus:outline-none focus:border-accent"
        />
        <button
          onClick={handleReachability}
          disabled={selectedNodes.size === 0}
          className={`px-2 py-1 text-xs font-medium rounded transition-all ${
            selectedNodes.size === 0
              ? 'bg-panel-border/30 text-text-secondary/50 cursor-not-allowed'
              : 'bg-panel-border/80 hover:bg-panel-border text-text-primary'
          }`}
          title="Show nodes reachable from selection"
        >
          Go
        </button>
        {config.reachability?.enabled && (
          <button
            onClick={handleClearReachability}
            className="px-2 py-1 text-xs font-medium bg-accent/80 rounded hover:bg-accent transition-all text-white"
          >
            Clear
          </button>
        )}
      </div>

      <div className="flex-1" />

      {/* Selection info */}
      {selectedNodes.size > 0 && (
        <div className="flex items-center gap-2 px-2 py-1 bg-amber-500/10 rounded-md border border-amber-500/20">
          <span className="text-xs text-amber-400 font-medium">
            {selectedNodes.size} selected
          </span>
          <button
            onClick={clearSelection}
            className="px-2 py-0.5 text-xs bg-amber-500/20 text-amber-300 rounded hover:bg-amber-500/30 transition-all"
            title="Clear selection (Esc)"
          >
            Clear
          </button>
        </div>
      )}

      {/* Export and Help buttons */}
      <ExportMenu />
      <HelpButton />
    </div>
  );
}
