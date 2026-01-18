/**
 * Log viewer component for displaying structured JSON Lines logs.
 * Features: individually toggleable level filters, expandable tracebacks, auto-scroll.
 */

import { useEffect, useRef, useState } from 'react';
import type { BuildStage, LogEntry, LogLevel } from '../types/build';
import { useBuildStore } from '../stores/buildStore';

interface LogViewerProps {
  buildName: string;
  stage: BuildStage;
}

// Color classes for each log level
const levelColors: Record<LogLevel, string> = {
  DEBUG: 'text-text-muted',
  INFO: 'text-text-primary',
  WARNING: 'text-warning',
  ERROR: 'text-error',
  ALERT: 'text-accent',
};

// Background colors for error/warning entries
const levelBgColors: Record<LogLevel, string> = {
  DEBUG: '',
  INFO: '',
  WARNING: 'bg-warning/10',
  ERROR: 'bg-error/10',
  ALERT: 'bg-accent/10',
};

// Level badge styles
const levelBadgeColors: Record<LogLevel, string> = {
  DEBUG: 'bg-text-muted/20 text-text-muted',
  INFO: 'bg-blue-500/20 text-blue-400',
  WARNING: 'bg-warning/20 text-warning',
  ERROR: 'bg-error/20 text-error',
  ALERT: 'bg-accent/20 text-accent',
};

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

interface ExpandableSection {
  label: string;
  content: string;
  color: string;
  borderColor: string;
}

function LogEntryRow({ entry }: { entry: LogEntry }) {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set());

  // Build list of expandable sections
  const sections: ExpandableSection[] = [];

  if (entry.ato_traceback) {
    sections.push({
      label: 'ato traceback',
      content: entry.ato_traceback,
      color: 'text-warning',
      borderColor: 'border-warning',
    });
  }

  if (entry.exc_info) {
    sections.push({
      label: 'python traceback',
      content: entry.exc_info,
      color: 'text-text-muted',
      borderColor: 'border-text-muted',
    });
  }

  const toggleSection = (label: string) => {
    setExpandedSections((prev) => {
      const next = new Set(prev);
      if (next.has(label)) {
        next.delete(label);
      } else {
        next.add(label);
      }
      return next;
    });
  };

  const hasSections = sections.length > 0;

  return (
    <div className={`${levelBgColors[entry.level]} border-b border-panel-border/30 last:border-0`}>
      {/* Main log line */}
      <div className="flex gap-2 py-1.5 px-3 items-start">
        {/* Timestamp */}
        <span className="text-text-muted shrink-0 font-mono text-xs mt-0.5">
          {formatTimestamp(entry.timestamp)}
        </span>

        {/* Level badge */}
        <span className={`shrink-0 px-1.5 py-0.5 rounded text-xs font-medium ${levelBadgeColors[entry.level]}`}>
          {entry.level}
        </span>

        {/* Message and expandable sections */}
        <div className="flex-1 min-w-0">
          <span className={`${levelColors[entry.level]} break-words`}>
            {entry.message}
          </span>

          {/* Expandable section toggles */}
          {hasSections && (
            <div className="flex gap-3 mt-1">
              {sections.map((section) => (
                <button
                  key={section.label}
                  onClick={() => toggleSection(section.label)}
                  className={`text-xs ${section.color} hover:underline flex items-center gap-1 opacity-70 hover:opacity-100`}
                >
                  <span className="text-[10px]">{expandedSections.has(section.label) ? '▼' : '▶'}</span>
                  <span>{section.label}</span>
                </button>
              ))}
            </div>
          )}

          {/* Expanded sections */}
          {sections.map(
            (section) =>
              expandedSections.has(section.label) && (
                <pre
                  key={section.label}
                  className={`mt-2 p-2 text-xs ${section.color} bg-panel-bg/50 border-l-2 ${section.borderColor} overflow-x-auto whitespace-pre-wrap rounded-r`}
                >
                  {section.content}
                </pre>
              )
          )}
        </div>
      </div>
    </div>
  );
}

const ALL_LEVELS: LogLevel[] = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'ALERT'];

export function LogViewer({ buildName, stage }: LogViewerProps) {
  const { logLoading, logError, fetchLog, enabledLevels, toggleLevel, getFilteredLogEntries } = useBuildStore();
  const logRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);

  // Fetch log when stage changes
  useEffect(() => {
    if (stage.log_file) {
      fetchLog(buildName, stage);
    }
  }, [buildName, stage.name, stage.log_file, fetchLog]);

  // Get filtered entries
  const filteredEntries = getFilteredLogEntries();

  // Auto-scroll to bottom when new entries arrive (if enabled)
  useEffect(() => {
    if (autoScroll && logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [filteredEntries, autoScroll]);

  // Detect manual scroll to disable auto-scroll
  const handleScroll = () => {
    if (!logRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = logRef.current;
    // If user scrolled up more than 100px from bottom, disable auto-scroll
    const isNearBottom = scrollHeight - scrollTop - clientHeight < 100;
    setAutoScroll(isNearBottom);
  };

  if (!stage.log_file) {
    return (
      <div className="bg-panel-bg border border-panel-border rounded p-4">
        <p className="text-text-muted text-sm">No logs available for this stage.</p>
      </div>
    );
  }

  // Get current log file path for display
  const logFilename = stage.log_file.split('/').pop() || stage.log_file;

  // Copy log path to clipboard
  const copyLogPath = () => {
    if (stage.log_file) {
      navigator.clipboard.writeText(stage.log_file);
    }
  };

  // Count entries by level for the filter badges
  const allEntries = useBuildStore.getState().logEntries || [];
  const levelCounts: Record<LogLevel, number> = {
    DEBUG: allEntries.filter(e => e.level === 'DEBUG').length,
    INFO: allEntries.filter(e => e.level === 'INFO').length,
    WARNING: allEntries.filter(e => e.level === 'WARNING').length,
    ERROR: allEntries.filter(e => e.level === 'ERROR').length,
    ALERT: allEntries.filter(e => e.level === 'ALERT').length,
  };

  // Toggle button colors based on level and enabled state
  const getToggleClasses = (level: LogLevel, isEnabled: boolean, count: number): string => {
    if (count === 0) {
      return 'bg-panel-border/30 text-text-muted/50 cursor-not-allowed';
    }

    const colorMap: Record<LogLevel, { on: string; off: string }> = {
      DEBUG: {
        on: 'bg-text-muted/30 text-text-primary border-text-muted/50',
        off: 'bg-transparent text-text-muted/50 border-text-muted/30 hover:border-text-muted/50',
      },
      INFO: {
        on: 'bg-blue-500/20 text-blue-300 border-blue-500/50',
        off: 'bg-transparent text-blue-400/50 border-blue-500/30 hover:border-blue-500/50',
      },
      WARNING: {
        on: 'bg-warning/20 text-warning border-warning/50',
        off: 'bg-transparent text-warning/50 border-warning/30 hover:border-warning/50',
      },
      ERROR: {
        on: 'bg-error/20 text-error border-error/50',
        off: 'bg-transparent text-error/50 border-error/30 hover:border-error/50',
      },
      ALERT: {
        on: 'bg-accent/20 text-accent border-accent/50',
        off: 'bg-transparent text-accent/50 border-accent/30 hover:border-accent/50',
      },
    };

    return isEnabled ? colorMap[level].on : colorMap[level].off;
  };

  return (
    <div className="bg-panel-bg border border-panel-border rounded overflow-hidden flex flex-col h-full">
      {/* Header with filter toggles and info */}
      <div className="flex items-center justify-between border-b border-panel-border px-3 py-2">
        {/* Level filter toggles */}
        <div className="flex gap-1">
          {ALL_LEVELS.map((level) => {
            const count = levelCounts[level];
            const isEnabled = enabledLevels.has(level);

            return (
              <button
                key={level}
                onClick={() => count > 0 && toggleLevel(level)}
                disabled={count === 0}
                className={`px-2 py-1 text-xs rounded border transition-colors flex items-center gap-1.5 ${getToggleClasses(level, isEnabled, count)}`}
                title={count === 0 ? `No ${level} entries` : `Toggle ${level} logs`}
              >
                <span>{level}</span>
                <span className="opacity-60">({count})</span>
              </button>
            );
          })}
        </div>

        {/* Stage info and copy button */}
        <div className="flex items-center gap-2 text-xs text-text-muted">
          <span>{stage.name}</span>
          <span className="text-panel-border">|</span>
          <button
            onClick={copyLogPath}
            className="hover:text-text-primary transition-colors flex items-center gap-1"
            title={`Click to copy: ${stage.log_file}`}
          >
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
            <span className="font-mono">{logFilename}</span>
          </button>

          {/* Auto-scroll indicator */}
          <span className="text-panel-border">|</span>
          <button
            onClick={() => setAutoScroll(!autoScroll)}
            className={`flex items-center gap-1 transition-colors ${autoScroll ? 'text-accent' : 'text-text-muted hover:text-text-primary'}`}
            title={autoScroll ? 'Auto-scroll enabled' : 'Auto-scroll disabled'}
          >
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
            </svg>
          </button>
        </div>
      </div>

      {/* Log content */}
      <div
        ref={logRef}
        className="flex-1 overflow-auto min-h-0"
        onScroll={handleScroll}
      >
        {logLoading ? (
          <div className="p-4 text-text-muted text-sm flex items-center gap-2">
            <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            Loading logs...
          </div>
        ) : logError ? (
          <div className="p-4 text-error text-sm">{logError}</div>
        ) : filteredEntries.length > 0 ? (
          <div className="text-sm font-mono">
            {filteredEntries.map((entry, idx) => (
              <LogEntryRow key={idx} entry={entry} />
            ))}
          </div>
        ) : (
          <div className="p-4 text-text-muted text-sm">
            {allEntries.length === 0 ? 'No log entries' : 'No entries match the current filters'}
          </div>
        )}
      </div>
    </div>
  );
}
