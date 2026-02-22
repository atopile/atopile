import { useEffect } from 'react';
import { TreeScene } from './three/TreeScene';
import { Toolbar } from './components/Toolbar';
import { Inspector } from './components/Inspector';
import { Legend } from './components/Legend';
import { useTreeStore } from './stores/treeStore';
import { useTheme } from './utils/theme';
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
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100vh',
        width: '100vw',
        overflow: 'hidden',
        background: theme.bgPrimary,
        color: theme.textPrimary,
      }}
    >
      <Toolbar />
      <div style={{ display: 'flex', flex: 1, minHeight: 0 }}>
        {/* Main canvas */}
        <div style={{ flex: 1, position: 'relative' }}>
          {isLoading && (
            <div style={{
              position: 'absolute', inset: 0,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              zIndex: 10,
            }}>
              <div style={{ fontSize: 14, color: theme.textMuted }}>
                Loading tree data...
              </div>
            </div>
          )}
          {loadError && (
            <div style={{
              position: 'absolute', inset: 0,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              zIndex: 10,
            }}>
              <div style={{ textAlign: 'center', maxWidth: 400, padding: '0 16px' }}>
                <div style={{ fontSize: 14, fontWeight: 600, color: '#f38ba8' }}>
                  Failed to load data
                </div>
                <div style={{ fontSize: 12, color: theme.textMuted, marginTop: 8 }}>
                  {loadError}
                </div>
                <div style={{ fontSize: 12, color: theme.textMuted, marginTop: 16 }}>
                  Build the project to generate tree data.
                </div>
              </div>
            </div>
          )}
          {graphData && !isLoading && <TreeScene />}
          {graphData && graphData.nodes.length === 0 && !isLoading && !loadError && (
            <div style={{
              position: 'absolute', inset: 0,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <div style={{ fontSize: 14, color: theme.textMuted }}>
                No tree data found. Make sure your design has power/I2C interfaces.
              </div>
            </div>
          )}
        </div>

        {/* Right sidebar */}
        <div
          style={{
            width: 224,
            display: 'flex',
            flexDirection: 'column',
            overflowY: 'auto',
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
