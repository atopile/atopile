import { useEffect, useState, useCallback, useRef } from 'react';
import { SchematicScene } from './three/SchematicScene';
import { Toolbar, type SchematicBuildStatus } from './components/Toolbar';
import { SchematicSidebar } from './components/SchematicSidebar';
import {
  useSchematicStore,
  useCurrentSheet,
  useCurrentPorts,
  setAtoSchPath,
} from './stores/schematicStore';
import type {
  SchematicData,
  SchematicSheet,
  SchematicSourceRef,
} from './types/schematic';
import { useTheme } from './lib/theme';
import {
  onExtensionMessage,
  postToExtension,
} from './lib/vscodeApi';
import type {
  SchematicBOMData,
  SchematicVariablesData,
} from './types/artifacts';

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

interface SchematicArtifactsPayload {
  bomData: SchematicBOMData | null;
  variablesData: SchematicVariablesData | null;
}

interface ShowInSchematicRequest {
  filePath?: string | null;
  line?: number | null;
  column?: number | null;
  symbol?: string | null;
}

interface SchematicTargetCandidate {
  kind: 'component' | 'module';
  id: string;
  path: string[];
  score: number;
}

const INITIAL_BUILD_STATUS: SchematicBuildStatus = {
  phase: 'idle',
  dirty: false,
  viewingLastSuccessful: false,
  lastSuccessfulAt: null,
  message: null,
};

const IGNORED_SYMBOL_TOKENS = new Set([
  'new',
  'module',
  'component',
  'interface',
  'signal',
  'from',
  'import',
  'if',
  'else',
  'for',
  'while',
  'return',
]);

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

function normalizePathForMatch(value: string | null | undefined): string {
  if (!value) return '';
  return value.trim().replace(/\\/g, '/').toLowerCase();
}

function basenameForPath(pathValue: string): string {
  if (!pathValue) return '';
  const trimmed = pathValue.endsWith('/') ? pathValue.slice(0, -1) : pathValue;
  const idx = trimmed.lastIndexOf('/');
  return idx >= 0 ? trimmed.slice(idx + 1) : trimmed;
}

function normalizeLookupKey(value: string | null | undefined): string {
  if (!value) return '';
  let normalized = value;
  normalized = normalized.replace(/\|.*$/, '');
  if (normalized.includes('::')) {
    const parts = normalized.split('::');
    normalized = parts[parts.length - 1] ?? normalized;
  }
  normalized = normalized.toLowerCase();
  normalized = normalized.replace(/\[(\d+)\]/g, '_$1');
  normalized = normalized.replace(/[.\s/-]+/g, '_');
  normalized = normalized.replace(/[^a-z0-9_]/g, '_');
  normalized = normalized.replace(/_+/g, '_');
  normalized = normalized.replace(/^_+|_+$/g, '');
  return normalized;
}

function normalizeSymbolToken(value: string | null | undefined): string {
  if (!value) return '';
  const cleaned = value
    .trim()
    .replace(/^['"`]+|['"`]+$/g, '')
    .replace(/[,:;(){}\[\]]+$/g, '');
  const normalized = normalizeLookupKey(cleaned);
  if (!normalized || IGNORED_SYMBOL_TOKENS.has(normalized)) return '';
  return normalized;
}

function sourceFileFromAddress(address: string | null | undefined): string {
  if (!address) return '';
  const primary = address.split('|')[0] ?? address;
  const filePart = primary.split('::')[0] ?? '';
  return normalizePathForMatch(filePart);
}

function scoreLineDistance(
  targetLine: number | undefined,
  sourceLine: number | undefined,
): number {
  if (targetLine == null || sourceLine == null) return 0;
  const delta = Math.abs(sourceLine - targetLine);
  if (delta === 0) return 220;
  if (delta <= 1) return 180;
  if (delta <= 3) return 130;
  if (delta <= 8) return 80;
  if (delta <= 20) return 35;
  return 0;
}

function scoreNameMatch(
  tokenKey: string,
  id: string,
  name: string,
): number {
  if (!tokenKey) return 0;
  const idKey = normalizeLookupKey(id);
  const nameKey = normalizeLookupKey(name);
  let score = 0;

  if (idKey === tokenKey) score = Math.max(score, 190);
  else if (idKey.endsWith(`_${tokenKey}`)) score = Math.max(score, 160);
  else if (idKey.includes(tokenKey)) score = Math.max(score, 120);

  if (nameKey === tokenKey) score = Math.max(score, 170);
  else if (nameKey.endsWith(`_${tokenKey}`)) score = Math.max(score, 145);
  else if (nameKey.includes(tokenKey)) score = Math.max(score, 105);

  return score;
}

function scoreSourceMatch({
  source,
  fileKey,
  fileBase,
  targetLine,
  tokenKey,
}: {
  source: SchematicSourceRef | null | undefined;
  fileKey: string;
  fileBase: string;
  targetLine: number | undefined;
  tokenKey: string;
}): number {
  if (!source) return 0;
  let score = 0;

  const sourceFiles = [
    normalizePathForMatch(source.filePath),
    sourceFileFromAddress(source.address),
  ].filter((entry): entry is string => !!entry);

  if (fileKey) {
    if (sourceFiles.some((entry) => entry === fileKey)) {
      score += 220;
    } else if (fileBase && sourceFiles.some((entry) => basenameForPath(entry) === fileBase)) {
      score += 95;
    }
  }

  score += scoreLineDistance(
    targetLine,
    typeof source.line === 'number' ? source.line : undefined,
  );

  if (tokenKey) {
    const instanceKey = normalizeLookupKey(source.instancePath);
    const addressKey = normalizeLookupKey(source.address);

    if (instanceKey === tokenKey) score += 200;
    else if (instanceKey.endsWith(`_${tokenKey}`)) score += 170;
    else if (instanceKey.includes(tokenKey)) score += 120;

    if (addressKey === tokenKey) score += 185;
    else if (addressKey.endsWith(`_${tokenKey}`)) score += 155;
    else if (addressKey.includes(tokenKey)) score += 105;
  }

  return score;
}

function parseShowInSchematicRequest(
  message: { [key: string]: unknown },
): ShowInSchematicRequest | null {
  const filePath = typeof message.filePath === 'string' ? message.filePath : null;
  const line = typeof message.line === 'number' ? message.line : null;
  const column = typeof message.column === 'number' ? message.column : null;
  const symbol = typeof message.symbol === 'string' ? message.symbol : null;
  if (!filePath && line == null && !symbol) return null;
  return { filePath, line, column, symbol };
}

function findBestSchematicTarget(
  data: SchematicData,
  request: ShowInSchematicRequest,
): SchematicTargetCandidate | null {
  const fileKey = normalizePathForMatch(request.filePath);
  const fileBase = basenameForPath(fileKey);
  const tokenKey = normalizeSymbolToken(request.symbol);
  const targetLine = typeof request.line === 'number' && Number.isFinite(request.line)
    ? request.line
    : undefined;

  const minimumScore = tokenKey ? 110 : 180;
  let best: SchematicTargetCandidate | null = null;

  const isBetterTarget = (
    candidate: SchematicTargetCandidate,
    currentBest: SchematicTargetCandidate | null,
  ): boolean => {
    if (!currentBest) return true;
    const delta = candidate.score - currentBest.score;
    if (delta > 10) return true;
    if (delta < -10) return false;

    // For token-based requests, prefer navigating deeper and landing on concrete symbols.
    if (tokenKey) {
      if (candidate.path.length !== currentBest.path.length) {
        return candidate.path.length > currentBest.path.length;
      }
      if (candidate.kind !== currentBest.kind) {
        return candidate.kind === 'component';
      }
    }

    if (delta !== 0) return delta > 0;
    return candidate.id < currentBest.id;
  };

  const consider = (
    kind: 'component' | 'module',
    path: string[],
    id: string,
    name: string,
    source: SchematicSourceRef | null | undefined,
  ) => {
    const sourceScore = scoreSourceMatch({
      source,
      fileKey,
      fileBase,
      targetLine,
      tokenKey,
    });
    const nameScore = scoreNameMatch(tokenKey, id, name);

    let score = Math.max(sourceScore, nameScore);
    if (sourceScore > 0 && nameScore > 0) score += 35;
    if (fileKey && sourceScore === 0 && nameScore < 130) score -= 25;
    if (tokenKey) {
      if (kind === 'component') score += 22;
      if (path.length > 0) score += Math.min(path.length * 12, 36);
    }
    if (score < minimumScore) return;

    const candidate: SchematicTargetCandidate = {
      kind,
      id,
      path: [...path],
      score,
    };
    if (isBetterTarget(candidate, best)) {
      best = candidate;
    }
  };

  const visit = (sheet: SchematicSheet, path: string[]) => {
    for (const component of sheet.components) {
      consider('component', path, component.id, component.name, component.source);
    }
    for (const module of sheet.modules) {
      consider('module', path, module.id, module.name, module.source);
      visit(module.sheet, [...path, module.id]);
    }
  };

  visit(data.root, []);
  return best;
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
  const pendingShowInSchematicRef = useRef<ShowInSchematicRequest | null>(null);

  // ── Sidebar state ─────────────────────────────────────────────

  const [sidebarWidth, setSidebarWidth] = useState(readInitialSidebarWidth);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(readInitialSidebarCollapsed);
  const [buildStatus, setBuildStatus] = useState<SchematicBuildStatus>(INITIAL_BUILD_STATUS);
  const [buildErrors, setBuildErrors] = useState<SchematicBuildError[]>([]);
  const [lastSuccessfulSnapshot, setLastSuccessfulSnapshot] = useState<SchematicData | null>(null);
  const [artifacts, setArtifacts] = useState<SchematicArtifactsPayload>({
    bomData: null,
    variablesData: null,
  });

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

  const showInSchematic = useCallback((request: ShowInSchematicRequest): boolean => {
    const store = useSchematicStore.getState();
    if (!store.schematic) return false;
    const target = findBestSchematicTarget(store.schematic, request);
    if (!target) {
      postToExtension({
        type: 'showInSchematicResult',
        found: false,
        symbol: request.symbol ?? undefined,
        filePath: request.filePath ?? undefined,
        line: request.line ?? undefined,
        column: request.column ?? undefined,
      });
      return true;
    }

    store.navigateToPath([...target.path]);
    store.selectNet(null);
    store.selectComponents([target.id]);
    store.requestFocusOnItem(target.id, target.path);
    postToExtension({
      type: 'showInSchematicResult',
      found: true,
      targetId: target.id,
      path: target.path,
    });
    return true;
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
      } else if (msg.type === 'schematic-artifacts') {
        setArtifacts({
          bomData: (msg.bomData && typeof msg.bomData === 'object')
            ? msg.bomData as SchematicBOMData
            : null,
          variablesData: (msg.variablesData && typeof msg.variablesData === 'object')
            ? msg.variablesData as SchematicVariablesData
            : null,
        });
      } else if (msg.type === 'showInSchematic') {
        const request = parseShowInSchematicRequest(msg);
        if (!request) return;
        const handled = showInSchematic(request);
        if (handled) {
          pendingShowInSchematicRef.current = null;
        } else {
          pendingShowInSchematicRef.current = request;
        }
      }
    });

    return () => {
      unsubscribe();
    };
  }, [showInSchematic]);

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

  useEffect(() => {
    const pending = pendingShowInSchematicRef.current;
    if (!pending) return;
    if (showInSchematic(pending)) {
      pendingShowInSchematicRef.current = null;
    }
  }, [schematicData, showInSchematic]);

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
              bomData={artifacts.bomData}
              variablesData={artifacts.variablesData}
            />
          </>
        )}
      </div>
    </div>
  );
}

export default SchematicApp;
