/**
 * Log viewer component - STATELESS.
 * Receives AppState from extension, sends actions back.
 */

import { useEffect, useState, useMemo, useRef, useCallback } from 'react';
import AnsiToHtml from 'ansi-to-html';
import { ArrowDownToLine, Clock, Timer } from 'lucide-react';
import { BuildSelector, type Selection, type Project, type BuildTarget } from './BuildSelector';
import type { AppState, LogLevel, LogEntry, Build } from '../types/build';
import { logDataSize, startMark } from '../perf';
import './LogViewer.css';

const vscode = acquireVsCodeApi();

const ALL_LEVELS: LogLevel[] = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'ALERT'];

// Convert AppState builds to BuildSelector Project format
function buildsToProjects(builds: Build[]): Project[] {
  const projectMap = new Map<string, Project>();

  // Map Build status to BuildTarget status
  const mapStatus = (status: Build['status']): BuildTarget['status'] => {
    switch (status) {
      case 'failed': return 'error';
      case 'queued': return 'idle';
      case 'building': return 'building';
      case 'success': return 'success';
      case 'warning': return 'warning';
      default: return 'idle';
    }
  };

  for (const build of builds) {
    const projectName = build.project_name || 'Unknown';

    if (!projectMap.has(projectName)) {
      projectMap.set(projectName, {
        id: projectName,
        name: projectName,
        type: 'project',
        path: '',
        builds: [],
      });
    }

    const project = projectMap.get(projectName)!;
    const buildTarget: BuildTarget = {
      id: build.display_name,
      name: build.name,
      entry: build.display_name,
      status: mapStatus(build.status),
      errors: build.errors,
      warnings: build.warnings,
    };
    project.builds.push(buildTarget);
  }

  return Array.from(projectMap.values());
}

// Convert selectedBuildName to Selection format
function buildNameToSelection(selectedBuildName: string | null, builds: Build[]): Selection {
  if (!selectedBuildName) {
    return { type: 'none' };
  }

  const build = builds.find(b => b.display_name === selectedBuildName);
  if (!build) {
    return { type: 'none' };
  }

  const projectName = build.project_name || 'Unknown';
  return {
    type: 'build',
    projectId: projectName,
    buildId: build.display_name,
    label: build.display_name,
  };
}

// Send action to extension
const action = (name: string, data?: object) => {
  vscode.postMessage({ type: 'action', action: name, ...data });
};

// ANSI to HTML converter instance
const ansiConverter = new AnsiToHtml({
  fg: '#e5e5e5',
  bg: 'transparent',
  newline: true,
  escapeXML: true,
});

/**
 * Render text with ANSI color codes as styled HTML.
 */
function AnsiText({ text }: { text: string }) {
  const html = useMemo(() => ansiConverter.toHtml(text), [text]);
  return <span dangerouslySetInnerHTML={{ __html: html }} />;
}

function FilterButton({
  level,
  count,
  isEnabled,
  onToggle,
}: {
  level: LogLevel;
  count: number;
  isEnabled: boolean;
  onToggle: () => void;
}) {
  const isDisabled = count === 0;
  const levelClass = level.toLowerCase();

  return (
    <button
      className={`filter-btn ${levelClass} ${isEnabled && !isDisabled ? 'active' : ''}`}
      onClick={() => !isDisabled && onToggle()}
      disabled={isDisabled}
    >
      {level}
      <span className="count">{count}</span>
    </button>
  );
}

function formatTimestamp(isoString: string, mode: 'absolute' | 'delta', prevTimestamp?: string): string {
  try {
    const date = new Date(isoString);

    if (mode === 'delta' && prevTimestamp) {
      const prevDate = new Date(prevTimestamp);
      const deltaMs = date.getTime() - prevDate.getTime();

      if (deltaMs < 1000) {
        return `+${deltaMs}ms`;
      } else if (deltaMs < 60000) {
        return `+${(deltaMs / 1000).toFixed(2)}s`;
      } else {
        const mins = Math.floor(deltaMs / 60000);
        const secs = ((deltaMs % 60000) / 1000).toFixed(1);
        return `+${mins}m${secs}s`;
      }
    }

    return date.toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  } catch {
    return isoString;
  }
}

function LogEntryRow({
  entry,
  timestampMode,
  prevTimestamp,
  isSearchMatch,
}: {
  entry: LogEntry;
  timestampMode: 'absolute' | 'delta';
  prevTimestamp?: string;
  isSearchMatch: boolean;
}) {
  const [isExpanded, setIsExpanded] = useState(false);
  const levelClass = entry.level.toLowerCase();

  // Check if message is multi-line or long enough to need expansion
  const messageLines = entry.message.split('\n');
  const isMultiLine = messageLines.length > 1;
  const isLongMessage = entry.message.length > 120;
  const hasTracebacks = !!(entry.ato_traceback || entry.exc_info);
  const isExpandable = isMultiLine || isLongMessage || hasTracebacks;

  const isHighlight = entry.level === 'WARNING' || entry.level === 'ERROR' || entry.level === 'ALERT';

  // Get the first line for collapsed display
  const firstLine = messageLines[0];
  const displayMessage = isExpanded ? entry.message : (
    isLongMessage && !isMultiLine ? entry.message.slice(0, 120) + '...' : firstLine
  );

  const handleClick = () => {
    if (isExpandable) {
      setIsExpanded(!isExpanded);
    }
  };

  return (
    <div
      className={`log-entry ${isHighlight ? levelClass : ''} ${isSearchMatch ? 'search-match' : ''} ${isExpandable ? 'expandable' : ''} ${isExpanded ? 'expanded' : ''}`}
      onClick={handleClick}
    >
      <span className="log-timestamp">{formatTimestamp(entry.timestamp, timestampMode, prevTimestamp)}</span>
      <span className={`log-level ${levelClass}`}>{entry.level}</span>
      <div className="log-body">
        {isExpanded ? (
          // Expanded view - full message in a pre-like div
          <>
            <div className="log-message-expanded">
              <span className="expand-chevron expanded">▶</span>
              <pre className="log-message-content"><AnsiText text={entry.message} /></pre>
            </div>
            {hasTracebacks && (
              <div className="tracebacks">
                {entry.ato_traceback && (
                  <div className="traceback-section">
                    <div className="traceback-label ato">ato traceback</div>
                    <pre className="traceback-content ato"><AnsiText text={entry.ato_traceback} /></pre>
                  </div>
                )}
                {entry.exc_info && (
                  <div className="traceback-section">
                    <div className="traceback-label">python traceback</div>
                    <pre className="traceback-content python"><AnsiText text={entry.exc_info} /></pre>
                  </div>
                )}
              </div>
            )}
          </>
        ) : (
          // Collapsed view - single line with badges
          <div className="log-message-row">
            {isExpandable && (
              <span className="expand-chevron">▶</span>
            )}
            <span className="log-message collapsed">
              <AnsiText text={displayMessage} />
            </span>
            {isMultiLine && (
              <span className="line-count">+{messageLines.length - 1} lines</span>
            )}
            {hasTracebacks && (
              <span className="has-traceback">traceback</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export function LogViewer() {
  // Single piece of state: AppState from extension
  const [state, setState] = useState<AppState | null>(null);
  const logRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      const msg = event.data;
      if (msg.type === 'state') {
        const endMark = startMark('logviewer:state-receive');
        logDataSize('logviewer:state-payload', msg.data);
        setState(msg.data);
        endMark({ logEntries: msg.data?.logEntries?.length ?? 0 });
      } else if (msg.type === 'update') {
        // Handle partial updates including incremental log appends
        setState(prev => {
          if (!prev) return msg.data;

          // Handle incremental log append (optimization for large log files)
          if (msg.data._appendLogEntries) {
            const newEntries = msg.data._appendLogEntries;
            const { _appendLogEntries, ...rest } = msg.data;
            return {
              ...prev,
              ...rest,
              logEntries: [...(prev.logEntries || []), ...newEntries],
            };
          }

          // Shallow merge for other fields
          return { ...prev, ...msg.data };
        });
      }
    };
    window.addEventListener('message', handleMessage);
    vscode.postMessage({ type: 'ready' });
    return () => window.removeEventListener('message', handleMessage);
  }, []);

  // Auto-scroll when logAutoScroll is enabled
  useEffect(() => {
    if (state?.logAutoScroll && logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [state?.logEntries, state?.logAutoScroll]);

  // Handle keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'f') {
        e.preventDefault();
        searchInputRef.current?.focus();
      }
      if (e.key === 'Escape' && state?.logSearchQuery) {
        action('setLogSearchQuery', { query: '' });
        searchInputRef.current?.blur();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [state?.logSearchQuery]);

  // Handle scroll - detect when user scrolls away from bottom
  const handleScroll = useCallback(() => {
    if (!logRef.current || !state) return;
    const { scrollTop, scrollHeight, clientHeight } = logRef.current;
    const atBottom = scrollHeight - scrollTop - clientHeight < 100;
    if (state.logAutoScroll !== atBottom) {
      action('setLogAutoScroll', { enabled: atBottom });
    }
  }, [state?.logAutoScroll]);

  // Server-side filtered logs - no client-side filtering needed
  // The server already applies level, stage, and search filters
  const displayedEntries = useMemo(() => {
    if (!state) return [];
    // logEntries are already filtered by the server
    return state.logEntries;
  }, [state?.logEntries]);

  // Level counts - use server-provided counts if available, otherwise calculate
  const levelCounts = useMemo(() => {
    if (!state) return { DEBUG: 0, INFO: 0, WARNING: 0, ERROR: 0, ALERT: 0 };
    
    // Prefer server-provided counts (from /api/logs/counts)
    if (state.logCounts) {
      return state.logCounts;
    }
    
    // Fallback: calculate from current entries (for backward compatibility)
    const entries = state.logEntries;
    return {
      DEBUG: entries.filter(e => e.level === 'DEBUG').length,
      INFO: entries.filter(e => e.level === 'INFO').length,
      WARNING: entries.filter(e => e.level === 'WARNING').length,
      ERROR: entries.filter(e => e.level === 'ERROR').length,
      ALERT: entries.filter(e => e.level === 'ALERT').length,
    };
  }, [state?.logCounts, state?.logEntries]);

  // Search matches for highlighting (still needed for UI highlighting)
  const searchMatches = useMemo(() => {
    if (!state?.logSearchQuery.trim()) return new Set<number>();
    const query = state.logSearchQuery.toLowerCase();
    const matches = new Set<number>();
    displayedEntries.forEach((entry, idx) => {
      if (
        entry.message.toLowerCase().includes(query) ||
        entry.logger.toLowerCase().includes(query) ||
        entry.stage?.toLowerCase().includes(query)
      ) {
        matches.add(idx);
      }
    });
    return matches;
  }, [displayedEntries, state?.logSearchQuery]);

  // Convert state to BuildSelector format (must be before early return to maintain hook order)
  const projects = useMemo(
    () => (state ? buildsToProjects(state.builds) : []),
    [state?.builds]
  );
  const selection = useMemo(
    () => (state ? buildNameToSelection(state.selectedBuildName, state.builds) : { type: 'none' as const }),
    [state?.selectedBuildName, state?.builds]
  );

  const handleSelectionChange = useCallback((newSelection: Selection) => {
    if (!state) return;
    if (newSelection.type === 'none') {
      // "All" selected - pass null to show logs from all builds
      action('selectBuild', { buildName: null, projectName: null });
    } else if (newSelection.buildId) {
      // Specific build selected
      action('selectBuild', { buildName: newSelection.buildId, projectName: null });
    } else if (newSelection.projectId) {
      // Project selected (not a specific build) - filter by project
      action('selectBuild', { buildName: null, projectName: newSelection.projectId });
    }
  }, [state?.builds]);

  if (!state) {
    return <div className="log-viewer loading">Loading...</div>;
  }

  return (
    <div className="log-viewer">
      <div className="log-header">
        {/* Level filters */}
        <div className="log-filters">
          {ALL_LEVELS.map((level) => (
            <FilterButton
              key={level}
              level={level}
              count={levelCounts[level]}
              isEnabled={state.enabledLogLevels.includes(level)}
              onToggle={() => action('toggleLogLevel', { level })}
            />
          ))}
        </div>

        {/* Search input */}
        <div className="log-search-box">
          <svg className="search-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="11" cy="11" r="8" />
            <path d="M21 21l-4.35-4.35" />
          </svg>
          <input
            ref={searchInputRef}
            type="text"
            placeholder="Search logs..."
            value={state.logSearchQuery}
            onChange={(e) => action('setLogSearchQuery', { query: e.target.value })}
            className="search-input"
          />
          {state.logSearchQuery && (
            <>
              <span className="search-count">
                {displayedEntries.length}/{state.logTotalCount ?? state.logEntries.length}
              </span>
              <button
                className="search-clear"
                onClick={(e) => {
                  e.stopPropagation();
                  action('setLogSearchQuery', { query: '' });
                }}
                title="Clear search"
              >
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M18 6L6 18M6 6l12 12" />
                </svg>
              </button>
            </>
          )}
        </div>

        <div className="log-actions">
          {/* Timestamp mode toggle */}
          <button
            className={`action-btn ${state.logTimestampMode === 'delta' ? 'active' : ''}`}
            onClick={() => action('toggleLogTimestampMode')}
            title={state.logTimestampMode === 'absolute' ? 'Show relative time (Δt)' : 'Show absolute time'}
          >
            {state.logTimestampMode === 'absolute' ? (
              <Clock size={14} />
            ) : (
              <Timer size={14} />
            )}
          </button>

          {/* Auto-scroll / pin to bottom */}
          <button
            className={`action-btn ${state.logAutoScroll ? 'active' : ''}`}
            onClick={() => action('setLogAutoScroll', { enabled: !state.logAutoScroll })}
            title={state.logAutoScroll ? 'Following new logs (click to unpin)' : 'Click to follow new logs'}
          >
            <ArrowDownToLine size={14} />
          </button>
        </div>

        {/* Build selector - right side */}
        <BuildSelector
          selection={selection}
          onSelectionChange={handleSelectionChange}
          projects={projects}
          showSymbols={false}
          compact
        />
      </div>

      <div className="log-content" ref={logRef} onScroll={handleScroll}>
        {state.isLoadingLogs ? (
          <div className="log-loading">
            <div className="spinner" />
            Loading logs...
          </div>
        ) : displayedEntries.length === 0 ? (
          <div className="log-empty">
            <div className="log-empty-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
                <line x1="16" y1="13" x2="8" y2="13" />
                <line x1="16" y1="17" x2="8" y2="17" />
                <line x1="10" y1="9" x2="8" y2="9" />
              </svg>
            </div>
            <p className="log-empty-text">
              {state.logEntries.length === 0
                ? 'Select a build to view logs'
                : state.logSearchQuery
                  ? 'No entries match your search'
                  : 'No entries match the current filters'}
            </p>
          </div>
        ) : (
          displayedEntries.map((entry, idx) => (
            <LogEntryRow
              key={idx}
              entry={entry}
              timestampMode={state.logTimestampMode}
              prevTimestamp={idx > 0 ? displayedEntries[idx - 1].timestamp : undefined}
              isSearchMatch={searchMatches.has(idx)}
            />
          ))
        )}
      </div>
    </div>
  );
}
