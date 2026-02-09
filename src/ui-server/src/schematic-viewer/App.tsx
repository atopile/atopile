import { useEffect, useState, useCallback } from 'react';
import { SchematicScene } from './three/SchematicScene';
import { Toolbar } from './components/Toolbar';
import { SchematicSidebar } from './components/SchematicSidebar';
import { useSchematicStore, useCurrentSheet, setAtoSchPath } from './stores/schematicStore';
import { useTheme } from './lib/theme';
import { requestOpenSource, onExtensionMessage } from './lib/vscodeApi';

// ── Sidebar size constraints ────────────────────────────────────

const SIDEBAR_MIN_W = 180;
const SIDEBAR_MAX_W = 500;
const SIDEBAR_DEFAULT_W = 320;

const SIDEBAR_WIDTH_STORAGE_KEY = 'schematic.viewer.sidebar.width';
const SIDEBAR_COLLAPSED_STORAGE_KEY = 'schematic.viewer.sidebar.collapsed';

function readInitialSidebarWidth() {
  if (typeof window === 'undefined') return SIDEBAR_DEFAULT_W;
  const rawValue = Number(window.localStorage.getItem(SIDEBAR_WIDTH_STORAGE_KEY));
  if (Number.isNaN(rawValue)) return SIDEBAR_DEFAULT_W;
  return Math.min(SIDEBAR_MAX_W, Math.max(SIDEBAR_MIN_W, rawValue));
}

function readInitialSidebarCollapsed() {
  if (typeof window === 'undefined') return false;
  return window.localStorage.getItem(SIDEBAR_COLLAPSED_STORAGE_KEY) === '1';
}

function SchematicApp() {
  const loadSchematic = useSchematicStore((s) => s.loadSchematic);
  const isLoading = useSchematicStore((s) => s.isLoading);
  const loadError = useSchematicStore((s) => s.loadError);
  const sheet = useCurrentSheet();
  const theme = useTheme();

  // ── Sidebar state ─────────────────────────────────────────────

  const [sidebarWidth, setSidebarWidth] = useState(readInitialSidebarWidth);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(readInitialSidebarCollapsed);

  // ── Horizontal resize (sidebar width) ─────────────────────────

  const handleWidthResize = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    const startX = e.clientX;
    const startW = sidebarWidth;

    const onMove = (me: MouseEvent) => {
      // Dragging left edge of sidebar: moving left = wider
      const delta = startX - me.clientX;
      const newW = Math.min(SIDEBAR_MAX_W, Math.max(SIDEBAR_MIN_W, startW + delta));
      setSidebarWidth(newW);
    };

    const onUp = () => {
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };

    document.body.style.cursor = 'ew-resize';
    document.body.style.userSelect = 'none';
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
  }, [sidebarWidth]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    window.localStorage.setItem(SIDEBAR_WIDTH_STORAGE_KEY, String(sidebarWidth));
  }, [sidebarWidth]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    window.localStorage.setItem(SIDEBAR_COLLAPSED_STORAGE_KEY, sidebarCollapsed ? '1' : '0');
  }, [sidebarCollapsed]);

  // ── Load schematic data on mount ─────────────────────────────

  useEffect(() => {
    // VSCode webview: check for injected config
    const cfg = (window as any).__SCHEMATIC_VIEWER_CONFIG__;
    if (cfg?.atoSchPath) {
      setAtoSchPath(cfg.atoSchPath);
    }
    if (cfg?.dataUrl) {
      loadSchematic(cfg.dataUrl);
      return;
    }

    // Dev mode: URL param or static demo
    const params = new URLSearchParams(window.location.search);
    const url = params.get('data') || './samples/demo-schematic.json';
    loadSchematic(url);
  }, []);

  // ── VSCode extension messaging ─────────────────────────────

  useEffect(() => {
    // Listen for messages from the extension
    const unsubscribe = onExtensionMessage((msg) => {
      if (msg.type === 'activeFile') {
        // The extension notifies us which file is active.
        // Future: match file to module/component and highlight it.
      } else if (msg.type === 'update-schematic' && msg.data) {
        // External rebuild: update data without resetting navigation
        useSchematicStore.getState().updateSchematicData(msg.data as any);
      }
    });

    // When a component is selected, notify the extension
    const unsub = useSchematicStore.subscribe(
      (s) => s.selectedComponentId,
      (selectedId) => {
        if (selectedId) {
          // Send the component address to the extension for source lookup
          requestOpenSource(selectedId);
        }
      },
    );

    return () => {
      unsubscribe();
      unsub();
    };
  }, []);

  // ── Keyboard shortcuts ───────────────────────────────────────

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore when typing in inputs
      const tag = (e.target as HTMLElement)?.tagName;
      if (['INPUT', 'TEXTAREA'].includes(tag)) return;

      const store = useSchematicStore.getState();

      // Undo: Cmd+Z / Ctrl+Z
      if (e.key === 'z' && (e.metaKey || e.ctrlKey) && !e.shiftKey) {
        e.preventDefault();
        store.undo();
        return;
      }
      // Redo: Cmd+Shift+Z / Ctrl+Shift+Z
      if (e.key === 'z' && (e.metaKey || e.ctrlKey) && e.shiftKey) {
        e.preventDefault();
        store.redo();
        return;
      }

      const GRID = 2.54;

      switch (e.key) {
        case 'Backspace':
          e.preventDefault();
          store.navigateUp();
          break;
        case 'Escape':
          store.selectComponent(null);
          store.selectNet(null);
          store.closeContextMenu();
          break;
        case 'r':
        case 'R':
          if (!e.ctrlKey && !e.metaKey) {
            store.rotateSelected();
          }
          break;
        case 'x':
        case 'X':
          if (!e.ctrlKey && !e.metaKey) {
            store.mirrorSelectedX();
          }
          break;
        case 'y':
        case 'Y':
          if (!e.ctrlKey && !e.metaKey) {
            store.mirrorSelectedY();
          }
          break;
        case 'ArrowLeft':
          e.preventDefault();
          store.nudgeSelected(-GRID, 0);
          break;
        case 'ArrowRight':
          e.preventDefault();
          store.nudgeSelected(GRID, 0);
          break;
        case 'ArrowUp':
          e.preventDefault();
          store.nudgeSelected(0, GRID);
          break;
        case 'ArrowDown':
          e.preventDefault();
          store.nudgeSelected(0, -GRID);
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
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
            <div
              style={{
                position: 'absolute',
                inset: 0,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                zIndex: 10,
              }}
            >
              <div
                style={{
                  fontSize: 14,
                  color: theme.textMuted,
                  animation: 'pulse 2s ease-in-out infinite',
                }}
              >
                Loading schematic...
              </div>
            </div>
          )}

          {loadError && (
            <div
              style={{
                position: 'absolute',
                inset: 0,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                zIndex: 10,
              }}
            >
              <div
                style={{
                  textAlign: 'center',
                  maxWidth: 400,
                  padding: '0 16px',
                }}
              >
                <div
                  style={{
                    fontSize: 14,
                    fontWeight: 600,
                    color: '#f38ba8',
                    marginBottom: 8,
                  }}
                >
                  Failed to load schematic
                </div>
                <div style={{ fontSize: 12, color: theme.textMuted }}>
                  {loadError}
                </div>
              </div>
            </div>
          )}

          {sheet && !isLoading && <SchematicScene />}
        </div>

        {/* Right sidebar — always rendered, collapses to narrow strip */}

        {/* Horizontal resize handle (only when expanded) */}
        {!sidebarCollapsed && (
          <div
            onMouseDown={handleWidthResize}
            style={{
              width: 6,
              flexShrink: 0,
              cursor: 'ew-resize',
              background: 'transparent',
              zIndex: 5,
            }}
            onMouseEnter={(e) => { e.currentTarget.style.background = `${theme.accent}55`; }}
            onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
          />
        )}

        <SchematicSidebar
          width={sidebarWidth}
          collapsed={sidebarCollapsed}
          onSetCollapsed={setSidebarCollapsed}
        />
      </div>
    </div>
  );
}

export default SchematicApp;
