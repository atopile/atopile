import { useEffect } from 'react';
import { TreeScene } from './three/TreeScene';
import { Toolbar } from './components/Toolbar';
import { Inspector } from './components/Inspector';
import { Legend } from './components/Legend';
import { useTreeStore } from './stores/treeStore';
import { useTheme } from './lib/theme';
import type { ViewerMode } from './types/tree';

function App() {
  const { loadData, isLoading, loadError, setMode, graphData } = useTreeStore();
  const theme = useTheme();

  useEffect(() => {
    // Check for config injected by VSCode webview
    const injectedConfig = (window as any).__TREE_VIEWER_CONFIG__;

    let mode: ViewerMode;
    let dataUrl: string;

    if (injectedConfig) {
      mode = injectedConfig.type || 'power';
      dataUrl = injectedConfig.dataUrl;
    } else {
      const params = new URLSearchParams(window.location.search);
      mode = (params.get('type') as ViewerMode) || 'power';
      dataUrl = params.get('data') || (mode === 'power' ? './power_tree.json' : './i2c_tree.json');
    }

    setMode(mode);
    loadData(dataUrl);
  }, []);

  return (
    <div
      className="flex flex-col h-screen w-screen overflow-hidden"
      style={{ background: theme.bgPrimary, color: theme.textPrimary }}
    >
      <Toolbar />
      <div className="flex flex-1 min-h-0">
        {/* Main canvas */}
        <div className="flex-1 relative">
          {isLoading && (
            <div className="absolute inset-0 flex items-center justify-center z-10">
              <div className="text-sm animate-pulse" style={{ color: theme.textMuted }}>
                Loading tree data...
              </div>
            </div>
          )}
          {loadError && (
            <div className="absolute inset-0 flex items-center justify-center z-10">
              <div className="text-center space-y-2 max-w-md px-4">
                <div className="text-sm font-semibold" style={{ color: '#f38ba8' }}>
                  Failed to load data
                </div>
                <div className="text-xs" style={{ color: theme.textMuted }}>
                  {loadError}
                </div>
                <div className="text-xs mt-4" style={{ color: theme.textMuted }}>
                  Build the project to generate tree data.
                </div>
              </div>
            </div>
          )}
          {graphData && !isLoading && <TreeScene />}
          {graphData && graphData.nodes.length === 0 && !isLoading && !loadError && (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-sm" style={{ color: theme.textMuted }}>
                No tree data found. Make sure your design has power/I2C interfaces.
              </div>
            </div>
          )}
        </div>

        {/* Right sidebar */}
        <div
          className="w-56 flex flex-col overflow-y-auto"
          style={{
            background: theme.bgSecondary,
            borderLeft: `1px solid ${theme.borderColor}`,
          }}
        >
          <Inspector />
          <div style={{ borderTop: '1px solid var(--border-subtle)' }} />
          <Legend />
        </div>
      </div>
    </div>
  );
}

export default App;
