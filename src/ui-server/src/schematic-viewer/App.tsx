import { useEffect, useRef, useState, useCallback } from 'react';
import { SchematicScene } from './three/SchematicScene';
import { Toolbar } from './components/Toolbar';
import { StructureTree } from './components/StructureTree';
import { SelectionDetails } from './components/SelectionDetails';
import { useSchematicStore, useCurrentSheet, setAtoSchPath } from './stores/schematicStore';
import { useTheme } from './lib/theme';
import { requestOpenSource, onExtensionMessage } from './lib/vscodeApi';

// ── Sidebar size constraints ────────────────────────────────────

const SIDEBAR_MIN_W = 180;
const SIDEBAR_MAX_W = 500;
const SIDEBAR_DEFAULT_W = 260;
const SPLIT_MIN_H = 60;

function SchematicApp() {
  const loadSchematic = useSchematicStore((s) => s.loadSchematic);
  const isLoading = useSchematicStore((s) => s.isLoading);
  const loadError = useSchematicStore((s) => s.loadError);
  const sheet = useCurrentSheet();
  const theme = useTheme();

  // ── Sidebar state ─────────────────────────────────────────────

  const [sidebarWidth, setSidebarWidth] = useState(SIDEBAR_DEFAULT_W);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  /** Height of the structure tree section (null = auto-fill) */
  const [treeHeight, setTreeHeight] = useState<number | null>(null);
  const sidebarRef = useRef<HTMLDivElement>(null);

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

  // ── Vertical resize (tree / details split) ────────────────────

  const handleSplitResize = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    const startY = e.clientY;
    const sidebar = sidebarRef.current;
    if (!sidebar) return;
    const sidebarRect = sidebar.getBoundingClientRect();
    const startH = treeHeight ?? (sidebarRect.height * 0.6);

    const onMove = (me: MouseEvent) => {
      const delta = me.clientY - startY;
      const maxH = sidebarRect.height - SPLIT_MIN_H;
      const newH = Math.min(maxH, Math.max(SPLIT_MIN_H, startH + delta));
      setTreeHeight(newH);
    };

    const onUp = () => {
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };

    document.body.style.cursor = 'ns-resize';
    document.body.style.userSelect = 'none';
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
  }, [treeHeight]);

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
              width: 4,
              flexShrink: 0,
              cursor: 'ew-resize',
              background: 'transparent',
              zIndex: 5,
            }}
            onMouseEnter={(e) => { e.currentTarget.style.background = theme.accent + '60'; }}
            onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
          />
        )}

        <div
          ref={sidebarRef}
          onClick={sidebarCollapsed ? () => setSidebarCollapsed(false) : undefined}
          style={{
            width: sidebarCollapsed ? 28 : sidebarWidth,
            flexShrink: 0,
            display: 'flex',
            flexDirection: 'column',
            background: theme.bgSecondary,
            borderLeft: `1px solid ${theme.borderColor}`,
            overflow: 'hidden',
            cursor: sidebarCollapsed ? 'pointer' : undefined,
          }}
        >
          {/* Sidebar header with collapse/expand toggle */}
          <div
            style={{
              height: 28,
              flexShrink: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: sidebarCollapsed ? 'center' : 'flex-end',
              borderBottom: sidebarCollapsed ? 'none' : `1px solid ${theme.borderColor}`,
              padding: sidebarCollapsed ? 0 : '0 4px',
            }}
          >
            <div
              onClick={(e) => { e.stopPropagation(); setSidebarCollapsed((c) => !c); }}
              style={{
                width: 22,
                height: 22,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: 'pointer',
                borderRadius: 3,
                fontSize: 10,
                color: theme.textMuted,
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.color = theme.textPrimary;
                e.currentTarget.style.background = theme.borderColor;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.color = theme.textMuted;
                e.currentTarget.style.background = 'transparent';
              }}
              title={sidebarCollapsed ? 'Show sidebar' : 'Hide sidebar'}
            >
              {sidebarCollapsed ? '\u25C0' : '\u25B6'}
            </div>
          </div>

          {/* Sidebar content (hidden when collapsed) */}
          {!sidebarCollapsed && (
            <>
              {/* Structure tree section */}
              <div
                style={{
                  flex: treeHeight ? `0 0 ${treeHeight}px` : '1 1 0',
                  minHeight: SPLIT_MIN_H,
                  overflowY: 'auto',
                  overflowX: 'hidden',
                }}
              >
                <StructureTree />
              </div>

              {/* Vertical split handle */}
              <div
                onMouseDown={handleSplitResize}
                style={{
                  height: 4,
                  flexShrink: 0,
                  cursor: 'ns-resize',
                  background: theme.borderColor,
                }}
                onMouseEnter={(e) => { e.currentTarget.style.background = theme.accent + '60'; }}
                onMouseLeave={(e) => { e.currentTarget.style.background = theme.borderColor; }}
              />

              {/* Selection details section */}
              <div
                style={{
                  flex: 1,
                  minHeight: SPLIT_MIN_H,
                  overflowY: 'auto',
                  overflowX: 'hidden',
                }}
              >
                <SelectionDetails />
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default SchematicApp;
