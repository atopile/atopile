import { useEffect } from 'react';
import { SchematicScene } from './three/SchematicScene';
import { Toolbar } from './components/Toolbar';
import { SymbolInspector } from './components/SymbolInspector';
import { useSchematicStore, useCurrentSheet } from './stores/schematicStore';
import { useTheme } from './lib/theme';

function App() {
  const { loadSchematic, isLoading, loadError, schematic } =
    useSchematicStore();
  const sheet = useCurrentSheet();
  const theme = useTheme();

  // ── Load schematic data on mount ─────────────────────────────

  useEffect(() => {
    // VSCode webview: check for injected config
    const config = (window as any).__SCHEMATIC_VIEWER_CONFIG__;
    if (config?.dataUrl) {
      loadSchematic(config.dataUrl);
      return;
    }

    // Dev mode: URL param or static demo
    const params = new URLSearchParams(window.location.search);
    const url = params.get('data') || './samples/demo-schematic.json';
    loadSchematic(url);
  }, []);

  // ── Keyboard shortcuts ───────────────────────────────────────

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore when typing in inputs
      const tag = (e.target as HTMLElement)?.tagName;
      if (['INPUT', 'TEXTAREA'].includes(tag)) return;

      const store = useSchematicStore.getState();

      switch (e.key) {
        // Backspace → navigate up one hierarchy level
        case 'Backspace':
          e.preventDefault();
          store.navigateUp();
          break;

        // Escape → deselect everything
        case 'Escape':
          store.selectComponent(null);
          store.selectNet(null);
          break;

        // R → rotate selected 90° CCW (KiCad default)
        case 'r':
        case 'R':
          if (!e.ctrlKey && !e.metaKey) {
            store.rotateSelected();
          }
          break;

        // X → mirror horizontally (KiCad: flip around Y axis)
        case 'x':
        case 'X':
          if (!e.ctrlKey && !e.metaKey) {
            store.mirrorSelectedX();
          }
          break;

        // Y → mirror vertically (KiCad: flip around X axis)
        case 'y':
        case 'Y':
          if (!e.ctrlKey && !e.metaKey) {
            store.mirrorSelectedY();
          }
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
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
              <div
                className="text-sm animate-pulse"
                style={{ color: theme.textMuted }}
              >
                Loading schematic...
              </div>
            </div>
          )}

          {loadError && (
            <div className="absolute inset-0 flex items-center justify-center z-10">
              <div className="text-center space-y-2 max-w-md px-4">
                <div
                  className="text-sm font-semibold"
                  style={{ color: '#f38ba8' }}
                >
                  Failed to load schematic
                </div>
                <div
                  className="text-xs"
                  style={{ color: theme.textMuted }}
                >
                  {loadError}
                </div>
              </div>
            </div>
          )}

          {sheet && !isLoading && <SchematicScene />}
        </div>

        {/* Right sidebar */}
        <div
          className="w-56 flex-shrink-0 overflow-y-auto"
          style={{
            background: theme.bgSecondary,
            borderLeft: `1px solid ${theme.borderColor}`,
          }}
        >
          <SymbolInspector />
        </div>
      </div>
    </div>
  );
}

export default App;
