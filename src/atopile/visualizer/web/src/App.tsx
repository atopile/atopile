/**
 * Main App component for the graph visualizer.
 */

import { useEffect } from 'react';
import { GraphScene } from './three/GraphScene';
import { Sidebar } from './components/Sidebar';
import { Toolbar } from './components/Toolbar';
import { Inspector } from './components/Inspector';
import { Tooltip } from './components/Tooltip';
import { Minimap } from './components/Minimap';
import { Breadcrumbs } from './components/Breadcrumbs';
import { useGraphStore } from './stores/graphStore';
import { useFilterStore } from './stores/filterStore';

function App() {
  const { loadGraph, data, isLoading, loadError } = useGraphStore();
  const { initializeFromData } = useFilterStore();

  // Load graph on mount
  useEffect(() => {
    // Try to load graph.json from the same directory
    loadGraph('./graph.json');
  }, [loadGraph]);

  // Initialize filter store when data loads
  useEffect(() => {
    if (data) {
      initializeFromData(data);
    }
  }, [data, initializeFromData]);

  return (
    <div className="grid grid-cols-[288px_1fr_320px] grid-rows-[56px_1fr] h-screen w-screen bg-graph-bg text-text-primary overflow-hidden">
      {/* Top toolbar spans full width */}
      <div className="col-span-3">
        <Toolbar />
      </div>

      {/* Left sidebar */}
      <Sidebar />

      {/* Main content area */}
      <div className="flex flex-col min-w-0 overflow-hidden">
        {/* Breadcrumb navigation */}
        <Breadcrumbs />

        {/* Graph canvas */}
        <div className="flex-1 relative min-h-0">
          {isLoading && (
            <div className="absolute inset-0 flex items-center justify-center bg-graph-bg/80 z-10">
              <div className="text-center">
                <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-accent mx-auto mb-3"></div>
                <div className="text-text-secondary">Loading graph...</div>
              </div>
            </div>
          )}

          {loadError && (
            <div className="absolute inset-0 flex items-center justify-center bg-graph-bg/80 z-10">
              <div className="text-red-400 max-w-md text-center p-4">
                <div className="text-4xl mb-3">⚠</div>
                <div className="text-lg font-semibold mb-2">Error loading graph</div>
                <div className="text-sm">{loadError}</div>
                <div className="mt-4 text-xs text-text-secondary">
                  Make sure graph.json is available at the server root.
                </div>
              </div>
            </div>
          )}

          <GraphScene />

          {/* Minimap overlay */}
          <Minimap />
        </div>

        {/* Status bar */}
        <StatusBar />
      </div>

      {/* Right panel - Inspector */}
      <Inspector />

      {/* Floating tooltip */}
      <Tooltip />
    </div>
  );
}

function StatusBar() {
  const { data, positions, isLayoutRunning } = useGraphStore();

  if (!data) return null;

  return (
    <div className="h-6 bg-panel-bg border-t border-panel-border px-4 flex items-center text-xs text-text-secondary">
      <span>
        {data.metadata.totalNodes} nodes, {data.metadata.totalEdges} edges
      </span>
      <span className="mx-2">|</span>
      <span>{positions.size} visible</span>
      {isLayoutRunning && (
        <>
          <span className="mx-2">|</span>
          <span className="text-accent">Computing layout...</span>
        </>
      )}
    </div>
  );
}

export default App;
