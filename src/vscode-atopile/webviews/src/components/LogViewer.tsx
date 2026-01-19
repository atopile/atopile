/**
 * Log viewer component for displaying structured JSON Lines logs.
 */

import { useEffect, useRef, useState, useMemo } from 'react';
import AnsiToHtml from 'ansi-to-html';
import { useBuildStore } from '../stores/buildStore';
import type { LogEntry, LogLevel } from '../types/build';
import './LogViewer.css';

// Get VS Code API
const vscode = acquireVsCodeApi();

const ALL_LEVELS: LogLevel[] = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'ALERT'];

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

function formatTimestamp(isoString: string): string {
  try {
    const date = new Date(isoString);
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

function LogEntryRow({ entry }: { entry: LogEntry }) {
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
    <div className={`log-entry ${isHighlight ? levelClass : ''}`}>
      <span className="log-timestamp">{formatTimestamp(entry.timestamp)}</span>
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
  const {
    logEntries,
    enabledLevels,
    isLoadingLogs,
    currentLogFile,
    setLogEntries,
    toggleLevel,
    setLoadingLogs,
    setCurrentLogFile,
    getFilteredLogEntries,
    getLevelCounts,
  } = useBuildStore();

  const logRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);

  // Handle messages from VS Code
  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      const message = event.data;

      switch (message.type) {
        case 'updateLogs':
          setLogEntries(message.data.entries || []);
          setLoadingLogs(message.data.isLoading ?? false);
          setCurrentLogFile(message.data.logFile || null);
          break;
      }
    };

    window.addEventListener('message', handleMessage);
    vscode.postMessage({ type: 'ready' });
    return () => window.removeEventListener('message', handleMessage);
  }, []);

  // Auto-scroll to bottom
  useEffect(() => {
    if (autoScroll && logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [logEntries, autoScroll]);

  const handleScroll = () => {
    if (!logRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = logRef.current;
    setAutoScroll(scrollHeight - scrollTop - clientHeight < 100);
  };

  const handleCopyLogPath = () => {
    vscode.postMessage({ type: 'copyLogPath' });
  };

  const handleToggleLevel = (level: LogLevel) => {
    toggleLevel(level);
    vscode.postMessage({ type: 'toggleLevel', level });
  };

  const filteredEntries = getFilteredLogEntries();
  const levelCounts = getLevelCounts();
  const logFilename = currentLogFile?.split('/').pop() || '';

  return (
    <div className="log-viewer">
      <div className="log-header">
        <div className="log-filters">
          {ALL_LEVELS.map((level) => (
            <FilterButton
              key={level}
              level={level}
              count={levelCounts[level]}
              isEnabled={enabledLevels.has(level)}
              onToggle={() => handleToggleLevel(level)}
            />
          ))}
        </div>

        <div className="log-actions">
          {currentLogFile && (
            <>
              <button className="log-file-btn" onClick={handleCopyLogPath} title={`Copy: ${currentLogFile}`}>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                </svg>
                {logFilename}
              </button>
              <div className="action-divider" />
            </>
          )}
          <button
            className={`scroll-btn ${autoScroll ? 'active' : ''}`}
            onClick={() => setAutoScroll(!autoScroll)}
            title={autoScroll ? 'Auto-scroll enabled' : 'Auto-scroll disabled'}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M19 14l-7 7m0 0l-7-7m7 7V3" />
            </svg>
          </button>
        </div>
      </div>

      <div className="log-content" ref={logRef} onScroll={handleScroll}>
        {isLoadingLogs ? (
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
              {logEntries.length === 0 ? 'Select a build stage to view logs' : 'No entries match the current filters'}
            </p>
          </div>
        ) : (
          filteredEntries.map((entry, idx) => <LogEntryRow key={idx} entry={entry} />)
        )}
      </div>
    </div>
  );
}
