/**
 * Log viewer component for displaying structured JSON Lines logs.
 */

import { useEffect, useRef, useState } from 'react';
import type { BuildStage, LogEntry, LogLevel } from '../types/build';
import { useBuildStore } from '../stores/buildStore';

interface LogViewerProps {
  buildName: string;
  stage: BuildStage;
}

type LogType = 'info' | 'error' | 'debug';

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
      <div className="flex gap-2 py-1 px-2">
        {/* Timestamp */}
        <span className="text-text-muted shrink-0 w-20">
          {formatTimestamp(entry.timestamp)}
        </span>

        {/* Level badge */}
        <span className={`shrink-0 w-16 font-medium ${levelColors[entry.level]}`}>
          {entry.level}
        </span>

        {/* Message */}
        <span className={`flex-1 ${levelColors[entry.level]}`}>
          {entry.message}
        </span>
      </div>

      {/* Expandable section toggles */}
      {hasSections && (
        <div className="flex gap-3 px-2 pb-1 ml-36">
          {sections.map((section) => (
            <button
              key={section.label}
              onClick={() => toggleSection(section.label)}
              className={`text-xs ${section.color} hover:underline flex items-center gap-1`}
            >
              <span>{expandedSections.has(section.label) ? '▼' : '▶'}</span>
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
              className={`px-2 py-2 mx-2 mb-2 text-xs ${section.color} bg-panel-bg/50 border-l-2 ${section.borderColor} overflow-x-auto whitespace-pre-wrap`}
            >
              {section.content}
            </pre>
          )
      )}
    </div>
  );
}

export function LogViewer({ buildName, stage }: LogViewerProps) {
  const { logEntries, logLoading, logError, fetchLog } = useBuildStore();
  const [activeTab, setActiveTab] = useState<LogType>('info');
  const logRef = useRef<HTMLDivElement>(null);

  // Available log types for this stage
  const availableLogs: LogType[] = [];
  if (stage.log_files.info) availableLogs.push('info');
  if (stage.log_files.error) availableLogs.push('error');
  if (stage.log_files.debug) availableLogs.push('debug');

  // Set default tab based on available logs
  useEffect(() => {
    if (availableLogs.length > 0 && !availableLogs.includes(activeTab)) {
      setActiveTab(availableLogs[0]);
    }
  }, [stage.name]);

  // Fetch log when tab changes
  useEffect(() => {
    if (stage.log_files[activeTab]) {
      fetchLog(buildName, stage, activeTab);
    }
  }, [buildName, stage.name, activeTab, fetchLog]);

  // Auto-scroll to bottom
  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [logEntries]);

  if (availableLogs.length === 0) {
    return (
      <div className="bg-panel-bg border border-panel-border rounded p-4">
        <p className="text-text-muted text-sm">No logs available for this stage.</p>
      </div>
    );
  }

  const tabColors: Record<LogType, string> = {
    info: 'text-text-primary',
    error: 'text-error',
    debug: 'text-text-muted',
  };

  // Get current log file path
  const currentLogPath = stage.log_files[activeTab];

  // Copy log path to clipboard
  const copyLogPath = () => {
    if (currentLogPath) {
      navigator.clipboard.writeText(currentLogPath);
    }
  };

  return (
    <div className="bg-panel-bg border border-panel-border rounded overflow-hidden flex flex-col h-full">
      {/* Tabs */}
      <div className="flex border-b border-panel-border">
        {availableLogs.map((logType) => (
          <button
            key={logType}
            onClick={() => setActiveTab(logType)}
            className={`
              px-4 py-2 text-sm font-medium transition-colors
              ${activeTab === logType
                ? `${tabColors[logType]} border-b-2 border-accent bg-accent/10`
                : 'text-text-muted hover:text-text-primary'
              }
            `}
          >
            {logType.charAt(0).toUpperCase() + logType.slice(1)}
          </button>
        ))}
        <div className="flex-1" />
        <div className="flex items-center gap-2 px-4 py-2 text-xs text-text-muted">
          <span>{stage.name}</span>
          {currentLogPath && (
            <>
              <span className="text-panel-border">|</span>
              <button
                onClick={copyLogPath}
                className="hover:text-text-primary transition-colors flex items-center gap-1"
                title={`Click to copy: ${currentLogPath}`}
              >
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
                <span className="font-mono">{currentLogPath.split('/').pop()}</span>
              </button>
            </>
          )}
        </div>
      </div>

      {/* Log content */}
      <div ref={logRef} className="flex-1 overflow-auto min-h-0">
        {logLoading ? (
          <div className="p-4 text-text-muted text-sm">Loading...</div>
        ) : logError ? (
          <div className="p-4 text-error text-sm">{logError}</div>
        ) : logEntries && logEntries.length > 0 ? (
          <div className="text-xs font-mono">
            {logEntries.map((entry, idx) => (
              <LogEntryRow key={idx} entry={entry} />
            ))}
          </div>
        ) : (
          <div className="p-4 text-text-muted text-sm">No log entries</div>
        )}
      </div>
    </div>
  );
}
