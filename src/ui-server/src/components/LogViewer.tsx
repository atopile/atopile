/**
 * Log viewer component - store driven.
 * Uses UI store synced from the backend via WebSocket.
 */

import { useEffect, useMemo, useRef, useCallback } from 'react';
import AnsiToHtml from 'ansi-to-html';
import { ArrowDownToLine, Clock, Timer } from 'lucide-react';
import { BuildSelector, type Selection, type Project, type BuildTarget } from './BuildSelector';
import type { LogLevel, LogEntry, Build } from '../types/build';
import { useBuilds, useLogs } from '../hooks';
import './LogViewer.css';

const ALL_LEVELS: LogLevel[] = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'ALERT'];

// Convert builds to BuildSelector Project format
function buildsToProjects(builds: Build[] | undefined | null): Project[] {
  if (!builds || !Array.isArray(builds)) return [];
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
    const projectName = build.projectName || 'Unknown';

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
      id: build.displayName,
      name: build.name,
      entry: build.displayName,
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

  const build = builds.find(b => b.displayName === selectedBuildName);
  if (!build) {
    return { type: 'none' };
  }

  const projectName = build.projectName || 'Unknown';
  return {
    type: 'build',
    projectId: projectName,
    buildId: build.displayName,
    label: build.displayName,
  };
}

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
  const hasTracebacks = !!(entry.atoTraceback || entry.excInfo);
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
                {entry.atoTraceback && (
                  <div className="traceback-section">
                    <div className="traceback-label ato">ato traceback</div>
                    <pre className="traceback-content ato"><AnsiText text={entry.atoTraceback} /></pre>
                  </div>
                )}
                {entry.excInfo && (
                  <div className="traceback-section">
                    <div className="traceback-label">python traceback</div>
                    <pre className="traceback-content python"><AnsiText text={entry.excInfo} /></pre>
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
  const {
    logEntries,
    filteredLogs,
    enabledLogLevels,
    logSearchQuery,
    logTimestampMode,
    logAutoScroll,
    isLoadingLogs,
    logCounts,
    logTotalCount,
    toggleLogLevel,
    setSearchQuery,
    toggleTimestampMode,
    setAutoScroll,
  } = useLogs();
  const { builds, selectedBuildName, selectBuild } = useBuilds();
  const logRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll when logAutoScroll is enabled
  useEffect(() => {
    if (logAutoScroll && logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [logEntries, logAutoScroll]);

  // Handle keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'f') {
        e.preventDefault();
        searchInputRef.current?.focus();
      }
      if (e.key === 'Escape' && logSearchQuery) {
        setSearchQuery('');
        searchInputRef.current?.blur();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [logSearchQuery, setSearchQuery]);

  // Handle scroll - detect when user scrolls away from bottom
  const handleScroll = useCallback(() => {
    if (!logRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = logRef.current;
    const atBottom = scrollHeight - scrollTop - clientHeight < 100;
    if (logAutoScroll !== atBottom) {
      setAutoScroll(atBottom);
    }
  }, [logAutoScroll, setAutoScroll]);

  // Server-side filtered logs - no client-side filtering needed
  // The server already applies level, stage, and search filters
  const displayedEntries = useMemo(
    () => (filteredLogs.length > 0 ? filteredLogs : logEntries),
    [filteredLogs, logEntries]
  );

  // Level counts - use server-provided counts if available, otherwise calculate
  const levelCounts = useMemo(() => {
    if (logCounts) {
      return logCounts;
    }
    const entries = logEntries || [];
    return {
      DEBUG: entries.filter(e => e.level === 'DEBUG').length,
      INFO: entries.filter(e => e.level === 'INFO').length,
      WARNING: entries.filter(e => e.level === 'WARNING').length,
      ERROR: entries.filter(e => e.level === 'ERROR').length,
      ALERT: entries.filter(e => e.level === 'ALERT').length,
    };
  }, [logCounts, logEntries]);

  // Search matches for highlighting (still needed for UI highlighting)
  const searchMatches = useMemo(() => {
    if (!logSearchQuery.trim()) return new Set<number>();
    const query = logSearchQuery.toLowerCase();
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
  }, [displayedEntries, logSearchQuery]);

  // Convert state to BuildSelector format (must be before early return to maintain hook order)
  const projects = useMemo(
    () => buildsToProjects(builds),
    [builds]
  );
  const selection = useMemo(
    () => buildNameToSelection(selectedBuildName, builds),
    [selectedBuildName, builds]
  );

  const handleSelectionChange = useCallback((newSelection: Selection) => {
    if (newSelection.type === 'none') {
      // "All" selected - pass null to show logs from all builds
      selectBuild(null);
    } else if (newSelection.buildId) {
      // Specific build selected
      selectBuild(newSelection.buildId);
    } else if (newSelection.projectId) {
      // Project selected (not a specific build) - clear build selection
      selectBuild(null);
    }
  }, [selectBuild]);

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
              isEnabled={enabledLogLevels.includes(level)}
              onToggle={() => toggleLogLevel(level)}
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
            value={logSearchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="search-input"
          />
          {logSearchQuery && (
            <>
              <span className="search-count">
                {displayedEntries.length}/{logTotalCount ?? logEntries.length}
              </span>
              <button
                className="search-clear"
                onClick={(e) => {
                  e.stopPropagation();
                  setSearchQuery('');
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
            className={`action-btn ${logTimestampMode === 'delta' ? 'active' : ''}`}
            onClick={() => toggleTimestampMode()}
            title={logTimestampMode === 'absolute' ? 'Show relative time (Δt)' : 'Show absolute time'}
          >
            {logTimestampMode === 'absolute' ? (
              <Clock size={14} />
            ) : (
              <Timer size={14} />
            )}
          </button>

          {/* Auto-scroll / pin to bottom */}
          <button
            className={`action-btn ${logAutoScroll ? 'active' : ''}`}
            onClick={() => setAutoScroll(!logAutoScroll)}
            title={logAutoScroll ? 'Following new logs (click to unpin)' : 'Click to follow new logs'}
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
        {isLoadingLogs ? (
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
              {logEntries.length === 0
                ? 'Select a build to view logs'
                : logSearchQuery
                  ? 'No entries match your search'
                  : 'No entries match the current filters'}
            </p>
          </div>
        ) : (
          displayedEntries.map((entry, idx) => (
            <LogEntryRow
              key={idx}
              entry={entry}
              timestampMode={logTimestampMode}
              prevTimestamp={idx > 0 ? displayedEntries[idx - 1].timestamp : undefined}
              isSearchMatch={searchMatches.has(idx)}
            />
          ))
        )}
      </div>
    </div>
  );
}
