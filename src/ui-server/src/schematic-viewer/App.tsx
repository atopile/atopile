import { useEffect, useState, useCallback } from 'react';
import { SchematicScene } from './three/SchematicScene';
import { Toolbar, type SchematicBuildStatus } from './components/Toolbar';
import { SchematicSidebar } from './components/SchematicSidebar';
import {
  useSchematicStore,
  useCurrentSheet,
  useCurrentPorts,
  setAtoSchPath,
} from './stores/schematicStore';
import type { SchematicData } from './types/schematic';
import { useTheme } from './lib/theme';
import {
  onExtensionMessage,
  postToExtension,
} from './lib/vscodeApi';

// ── Sidebar size constraints ────────────────────────────────────

const SIDEBAR_MIN_W = 180;
const SIDEBAR_MAX_W = 500;
const SIDEBAR_DEFAULT_W = 320;

const SIDEBAR_WIDTH_STORAGE_KEY = 'schematic.viewer.sidebar.width';
const SIDEBAR_COLLAPSED_STORAGE_KEY = 'schematic.viewer.sidebar.collapsed';

interface SchematicBuildError {
  message: string;
  filePath?: string | null;
  line?: number | null;
  column?: number | null;
}

const INITIAL_BUILD_STATUS: SchematicBuildStatus = {
  phase: 'idle',
  dirty: false,
  viewingLastSuccessful: false,
  lastSuccessfulAt: null,
  message: null,
};

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
  const loadSchematicData = useSchematicStore((s) => s.loadSchematicData);
  const schematicData = useSchematicStore((s) => s.schematic);
  const isLoading = useSchematicStore((s) => s.isLoading);
  const loadError = useSchematicStore((s) => s.loadError);
  const sheet = useCurrentSheet();
  const ports = useCurrentPorts();
  const theme = useTheme();

  // ── Sidebar state ─────────────────────────────────────────────

  const [sidebarWidth, setSidebarWidth] = useState(readInitialSidebarWidth);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(readInitialSidebarCollapsed);
  const [buildStatus, setBuildStatus] = useState<SchematicBuildStatus>(INITIAL_BUILD_STATUS);
  const [buildErrors, setBuildErrors] = useState<SchematicBuildError[]>([]);
  const [lastSuccessfulSnapshot, setLastSuccessfulSnapshot] = useState<SchematicData | null>(null);

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
        const data = msg.data as SchematicData;
        useSchematicStore.getState().updateSchematicData(data);
        setLastSuccessfulSnapshot(data);
      } else if (msg.type === 'schematic-build-status') {
        const phase = typeof msg.phase === 'string'
          && ['idle', 'building', 'queued', 'success', 'failed'].includes(msg.phase)
          ? msg.phase
          : 'idle';
        setBuildStatus({
          phase: phase as SchematicBuildStatus['phase'],
          dirty: !!msg.dirty,
          viewingLastSuccessful: !!msg.viewingLastSuccessful,
          lastSuccessfulAt: typeof msg.lastSuccessfulAt === 'number' ? msg.lastSuccessfulAt : null,
          message: typeof msg.message === 'string' ? msg.message : null,
        });
      } else if (msg.type === 'schematic-build-errors') {
        const incoming = Array.isArray(msg.errors) ? msg.errors : [];
        const parsed: SchematicBuildError[] = incoming.map((err: any) => ({
          message: typeof err?.message === 'string' ? err.message : 'Build error',
          filePath: typeof err?.filePath === 'string' ? err.filePath : null,
          line: typeof err?.line === 'number' ? err.line : null,
          column: typeof err?.column === 'number' ? err.column : null,
        }));
        setBuildErrors(parsed);
      }
    });

    return () => {
      unsubscribe();
    };
  }, []);

  const openSelectionInSource = useCallback((selectionId: string | null): boolean => {
    if (!selectionId || !sheet) return false;
    const source = sheet.components.find((c) => c.id === selectionId)?.source
      ?? sheet.modules.find((m) => m.id === selectionId)?.source
      ?? ports.find((p) => p.id === selectionId)?.source
      ?? null;
    const fallbackAddress = selectionId.includes('::') ? selectionId : undefined;
    const request = source
      ? {
        address: source.address ?? fallbackAddress,
        filePath: source.filePath,
        line: source.line,
        column: source.column,
      }
      : (fallbackAddress ? { address: fallbackAddress } : null);
    if (!request?.address && !request?.filePath) return false;
    postToExtension({ type: 'openSource', ...request });
    return true;
  }, [sheet, ports]);

  const revertViewToLastSuccessful = useCallback(() => {
    if (!lastSuccessfulSnapshot) return;
    postToExtension({ type: 'revertToLastSuccessful' });
    loadSchematicData(lastSuccessfulSnapshot);
    setBuildStatus((prev) => ({
      ...prev,
      viewingLastSuccessful: true,
    }));
  }, [lastSuccessfulSnapshot, loadSchematicData]);

  const openBuildErrorSource = useCallback((err: SchematicBuildError) => {
    if (!err.filePath) return;
    postToExtension({
      type: 'openSource',
      filePath: err.filePath,
      line: err.line ?? undefined,
      column: err.column ?? undefined,
    });
  }, []);

  useEffect(() => {
    if (!schematicData) return;
    if (lastSuccessfulSnapshot) return;
    setLastSuccessfulSnapshot(schematicData);
  }, [schematicData, lastSuccessfulSnapshot]);

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

      // Jump to source: Cmd+. / Ctrl+.
      if (e.key === '.' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        openSelectionInSource(store.selectedComponentId);
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
        case 'f':
        case 'F':
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
  }, [openSelectionInSource]);

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        width: '100%',
        overflow: 'hidden',
        overscrollBehavior: 'none',
        background: theme.bgPrimary,
        color: theme.textPrimary,
      }}
    >
      <Toolbar
        buildStatus={buildStatus}
        sidebarCollapsed={sidebarCollapsed}
        onToggleSidebar={() => setSidebarCollapsed((prev) => !prev)}
      />

      {buildStatus.phase === 'failed' && (
        <div
          style={{
            padding: '8px 12px',
            borderBottom: `1px solid ${theme.borderColor}`,
            background: '#53202f44',
            color: '#f5a7ba',
            display: 'flex',
            alignItems: 'flex-start',
            gap: 10,
            flexWrap: 'wrap',
          }}
        >
          <div style={{ fontSize: 12, fontWeight: 600 }}>
            Build failed. Showing last successful schematic.
          </div>
          {lastSuccessfulSnapshot && (
            <button
              onClick={revertViewToLastSuccessful}
              style={{
                fontSize: 11,
                padding: '3px 10px',
                borderRadius: 3,
                border: `1px solid ${theme.borderColor}`,
                background: theme.bgTertiary,
                color: theme.textPrimary,
                cursor: 'pointer',
              }}
              onMouseEnter={(e) => { e.currentTarget.style.background = theme.bgHover; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = theme.bgTertiary; }}
            >
              Revert view to last successful
            </button>
          )}
          {!!buildStatus.message && (
            <div style={{ fontSize: 11, color: theme.textSecondary }}>
              {buildStatus.message}
            </div>
          )}
          {buildErrors.length > 0 && (
            <div
              style={{
                width: '100%',
                display: 'flex',
                flexDirection: 'column',
                gap: 4,
                marginTop: 4,
              }}
            >
              {buildErrors.slice(0, 8).map((err, idx) => {
                const location = err.filePath
                  ? `${err.filePath}${err.line ? `:${err.line}` : ''}`
                  : null;
                return (
                  <button
                    key={`${idx}:${err.message}`}
                    onClick={() => openBuildErrorSource(err)}
                    disabled={!err.filePath}
                    style={{
                      textAlign: 'left',
                      border: 'none',
                      background: 'transparent',
                      color: err.filePath ? theme.textPrimary : theme.textSecondary,
                      fontSize: 11,
                      cursor: err.filePath ? 'pointer' : 'default',
                      padding: 0,
                    }}
                  >
                    {location ? `${location} - ` : ''}{err.message}
                  </button>
                );
              })}
            </div>
          )}
        </div>
      )}

      <div style={{ display: 'flex', flex: 1, minHeight: 0, minWidth: 0, overflow: 'hidden' }}>
        {/* Main canvas */}
        <div style={{ flex: 1, minWidth: 0, minHeight: 0, position: 'relative', overflow: 'hidden' }}>
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

        {!sidebarCollapsed && (
          <>
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
            <SchematicSidebar
              width={sidebarWidth}
              onSetCollapsed={setSidebarCollapsed}
            />
          </>
        )}
      </div>
    </div>
  );
}

export default SchematicApp;
