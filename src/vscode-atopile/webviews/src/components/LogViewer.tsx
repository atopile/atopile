/**
 * Log viewer component - STATELESS.
 * Receives AppState from extension, sends actions back.
 */

import { useEffect, useState, useMemo, useRef, useCallback } from 'react';
import AnsiToHtml from 'ansi-to-html';
import type { AppState, LogLevel, LogEntry } from '../types/build';
import './LogViewer.css';

const vscode = acquireVsCodeApi();

const ALL_LEVELS: LogLevel[] = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'ALERT'];

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
  const levelClass = level.toLowerCase();

  return (
    <button
      className={`filter-btn ${levelClass} ${isEnabled ? 'active' : ''}`}
      onClick={onToggle}
    >
      {level}
      {count > 0 && <span className="count">{count}</span>}
    </button>
  );
}

function StageFilterDropdown({
  availableStages,
  enabledStages,
}: {
  availableStages: string[];
  enabledStages: string[];
}) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [isOpen]);

  // Simple logic:
  // - enabledStages empty = show all (no filter active, all checkboxes unchecked)
  // - enabledStages has items = filter to only those stages (those checkboxes checked)
  const isFiltered = enabledStages.length > 0;
  const isStageChecked = (stage: string) => enabledStages.includes(stage);

  const hasStages = availableStages.length > 0;

  return (
    <div className="stage-filter-dropdown" ref={dropdownRef}>
      <button
        className={`stage-filter-btn ${isFiltered ? 'filtered' : ''} ${isOpen ? 'open' : ''}`}
        onClick={() => hasStages && setIsOpen(!isOpen)}
        disabled={!hasStages}
        title={hasStages ? 'Filter by build stage' : 'No stages available'}
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" />
        </svg>
        Stages
        {hasStages && isFiltered && (
          <span className="stage-count">
            {enabledStages.length}/{availableStages.length}
          </span>
        )}
        <svg className={`chevron ${isOpen ? 'open' : ''}`} width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>

      {isOpen && (
        <div className="stage-dropdown-panel">
          {isFiltered && (
            <div className="stage-dropdown-actions">
              <button
                className="stage-action-btn clear-btn"
                onClick={() => {
                  action('clearStageFilters');
                }}
              >
                Clear Filters
              </button>
            </div>
          )}
          <div className="stage-dropdown-list">
            {availableStages.map((stage) => (
              <label key={stage} className="stage-checkbox-item">
                <input
                  type="checkbox"
                  checked={isStageChecked(stage)}
                  onChange={() => action('toggleStage', { stage })}
                />
                <span className="stage-name" title={stage}>{stage}</span>
              </label>
            ))}
          </div>
        </div>
      )}
    </div>
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
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set());
  const levelClass = entry.level.toLowerCase();

  const toggleSection = (section: string) => {
    setExpandedSections((prev) => {
      const next = new Set(prev);
      if (next.has(section)) {
        next.delete(section);
      } else {
        next.add(section);
      }
      return next;
    });
  };

  const isHighlight = entry.level === 'WARNING' || entry.level === 'ERROR' || entry.level === 'ALERT';

  return (
    <div className={`log-entry ${isHighlight ? levelClass : ''} ${isSearchMatch ? 'search-match' : ''}`}>
      <span className="log-timestamp">{formatTimestamp(entry.timestamp, timestampMode, prevTimestamp)}</span>
      <span className={`log-level ${levelClass}`}>{entry.level}</span>
      <div className="log-body">
        <span className="log-message"><AnsiText text={entry.message} /></span>

        {(entry.ato_traceback || entry.exc_info) && (
          <div className="traceback-toggles">
            {entry.ato_traceback && (
              <button
                className="traceback-toggle ato"
                onClick={() => toggleSection('ato')}
              >
                <span className={`chevron ${expandedSections.has('ato') ? 'expanded' : ''}`}>▶</span>
                ato traceback
              </button>
            )}
            {entry.exc_info && (
              <button
                className="traceback-toggle"
                onClick={() => toggleSection('py')}
              >
                <span className={`chevron ${expandedSections.has('py') ? 'expanded' : ''}`}>▶</span>
                python traceback
              </button>
            )}
          </div>
        )}

        {expandedSections.has('ato') && entry.ato_traceback && (
          <pre className="traceback-content ato"><AnsiText text={entry.ato_traceback} /></pre>
        )}

        {expandedSections.has('py') && entry.exc_info && (
          <pre className="traceback-content python"><AnsiText text={entry.exc_info} /></pre>
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
        setState(msg.data);
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

  // Client-side filtering by level, stage, and search query
  const filteredEntries = useMemo(() => {
    if (!state) return [];

    return state.logEntries.filter(entry => {
      // Level filter
      if (!state.enabledLogLevels.includes(entry.level)) {
        return false;
      }

      // Stage filter: empty = show all, non-empty = filter to selected stages
      if (state.enabledStages.length > 0) {
        if (!entry.stage || !state.enabledStages.includes(entry.stage)) {
          return false;
        }
      }

      // Search query filter
      const query = state.logSearchQuery.toLowerCase().trim();
      if (query) {
        const matchesQuery =
          entry.message.toLowerCase().includes(query) ||
          entry.logger.toLowerCase().includes(query) ||
          entry.stage?.toLowerCase().includes(query);
        if (!matchesQuery) {
          return false;
        }
      }

      return true;
    });
  }, [state?.logEntries, state?.enabledLogLevels, state?.enabledStages, state?.logSearchQuery]);

  // Search matches for highlighting (all filtered entries match when search is active)
  const searchMatches = useMemo(() => {
    if (!state?.logSearchQuery.trim()) return new Set<number>();
    const matches = new Set<number>();
    filteredEntries.forEach((_, idx) => matches.add(idx));
    return matches;
  }, [filteredEntries, state?.logSearchQuery]);

  // Level counts from all logs (unfiltered)
  // Shows total logs of each type for the filter button badges
  const levelCounts = useMemo(() => {
    if (!state) return { DEBUG: 0, INFO: 0, WARNING: 0, ERROR: 0, ALERT: 0 };
    return {
      DEBUG: state.logEntries.filter(e => e.level === 'DEBUG').length,
      INFO: state.logEntries.filter(e => e.level === 'INFO').length,
      WARNING: state.logEntries.filter(e => e.level === 'WARNING').length,
      ERROR: state.logEntries.filter(e => e.level === 'ERROR').length,
      ALERT: state.logEntries.filter(e => e.level === 'ALERT').length,
    };
  }, [state?.logEntries]);

  if (!state) {
    return <div className="log-viewer loading">Loading...</div>;
  }

  return (
    <div className="log-viewer">
      <div className="log-header">
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
          <div className="filter-divider" />
          <StageFilterDropdown
            availableStages={state.availableStages}
            enabledStages={state.enabledStages}
          />
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
                {filteredEntries.length}/{state.logEntries.length}
              </span>
              <button
                className="search-clear"
                onClick={() => action('setLogSearchQuery', { query: '' })}
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
            title={state.logTimestampMode === 'absolute' ? 'Switch to delta timestamps' : 'Switch to absolute timestamps'}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              {state.logTimestampMode === 'absolute' ? (
                <>
                  <circle cx="12" cy="12" r="10" />
                  <polyline points="12 6 12 12 16 14" />
                </>
              ) : (
                <>
                  <path d="M5 12h14" />
                  <path d="M12 5v14" />
                </>
              )}
            </svg>
          </button>

          <div className="action-divider" />

          <button
            className={`scroll-btn ${state.logAutoScroll ? 'active' : ''}`}
            onClick={() => action('setLogAutoScroll', { enabled: !state.logAutoScroll })}
            title={state.logAutoScroll ? 'Auto-scroll enabled' : 'Auto-scroll disabled'}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M19 14l-7 7m0 0l-7-7m7 7V3" />
            </svg>
          </button>
        </div>
      </div>

      {/* Build info bar */}
      {state.currentBuildInfo && (
        <div className="log-build-info">
          <span className="build-info-item build-target" title={`Target: ${state.currentBuildInfo.target}`}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <circle cx="12" cy="12" r="6" />
              <circle cx="12" cy="12" r="2" />
            </svg>
            {state.currentBuildInfo.target}
          </span>
          <span className="build-info-sep">·</span>
          <span className="build-info-item" title={state.currentBuildInfo.projectPath}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
            </svg>
            {state.currentBuildInfo.projectPath.split('/').pop() || state.currentBuildInfo.projectPath}
          </span>
          <span className="build-info-sep">·</span>
          <span className="build-info-item" title="Build timestamp">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
            {state.currentBuildInfo.timestamp.replace('_', ' ')}
          </span>
          <span className="build-info-sep">·</span>
          <span className="build-info-item build-id" title={`Build ID: ${state.currentBuildInfo.buildId}`}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
              <line x1="9" y1="9" x2="15" y2="9" />
              <line x1="9" y1="15" x2="15" y2="15" />
            </svg>
            {state.currentBuildInfo.buildId.substring(0, 8)}
          </span>
        </div>
      )}

      <div className="log-content" ref={logRef} onScroll={handleScroll}>
        {state.isLoadingLogs ? (
          <div className="log-loading">
            <div className="spinner" />
            Loading logs...
          </div>
        ) : filteredEntries.length === 0 ? (
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
          filteredEntries.map((entry, idx) => (
            <LogEntryRow
              key={idx}
              entry={entry}
              timestampMode={state.logTimestampMode}
              prevTimestamp={idx > 0 ? filteredEntries[idx - 1].timestamp : undefined}
              isSearchMatch={searchMatches.has(idx)}
            />
          ))
        )}
      </div>
    </div>
  );
}
