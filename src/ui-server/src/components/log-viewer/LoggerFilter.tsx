/**
 * Logger Filter Component - Dropdown with checkboxes for top-level logger namespaces
 *
 * Extracts unique top-level logger names (e.g., "faebryk" from "faebryk.core.solver.solver")
 * and provides checkbox toggles to filter logs by these namespaces.
 */

import { useRef, useEffect, useState, useMemo, useCallback } from 'react';
import { LogEntry } from './logTypes';

// Local storage key for persisted logger filter
const STORAGE_KEY = 'lv-loggerFilter';

// Chevron icon component
function ChevronDown({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      width="10"
      height="10"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <polyline points="6 9 12 15 18 9" />
    </svg>
  );
}

/**
 * Extract the top-level logger namespace from a full logger name.
 * e.g., "faebryk.core.solver.solver" -> "faebryk"
 *       "atopile.logging" -> "atopile"
 *       "httpcore.connection" -> "httpcore"
 */
export function getTopLevelLogger(loggerName: string | undefined | null): string | null {
  if (!loggerName) return null;
  const parts = loggerName.split('.');
  return parts[0] || null;
}

/**
 * Get unique top-level logger names from a list of log entries.
 * Returns them sorted alphabetically.
 */
export function getUniqueTopLevelLoggers(logs: LogEntry[]): string[] {
  const topLevelLoggers = new Set<string>();
  for (const log of logs) {
    const topLevel = getTopLevelLogger(log.logger_name);
    if (topLevel) {
      topLevelLoggers.add(topLevel);
    }
  }
  return Array.from(topLevelLoggers).sort();
}

/**
 * Load enabled loggers from localStorage.
 * Returns null if nothing stored (meaning all enabled by default).
 */
export function loadEnabledLoggers(): Set<string> | null {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      if (Array.isArray(parsed)) {
        return new Set(parsed);
      }
    }
  } catch { /* ignore */ }
  return null;
}

/**
 * Save enabled loggers to localStorage.
 * If null, removes the key (all enabled).
 */
export function saveEnabledLoggers(enabled: Set<string> | null): void {
  if (enabled === null) {
    localStorage.removeItem(STORAGE_KEY);
  } else {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(Array.from(enabled)));
  }
}

/**
 * Filter logs by enabled top-level loggers.
 * If enabledLoggers is null, all logs pass through (no filtering).
 */
export function filterByLoggers(logs: LogEntry[], enabledLoggers: Set<string> | null): LogEntry[] {
  if (enabledLoggers === null) {
    return logs;
  }
  return logs.filter(log => {
    const topLevel = getTopLevelLogger(log.logger_name);
    // If no logger name, include by default
    if (!topLevel) return true;
    return enabledLoggers.has(topLevel);
  });
}

export interface LoggerFilterProps {
  logs: LogEntry[];
  enabledLoggers: Set<string> | null;
  onEnabledLoggersChange: (enabled: Set<string> | null) => void;
}

export function LoggerFilter({
  logs,
  enabledLoggers,
  onEnabledLoggersChange,
}: LoggerFilterProps) {
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Get all unique top-level loggers from the current logs
  const availableLoggers = useMemo(() => getUniqueTopLevelLoggers(logs), [logs]);

  // Determine which loggers are currently enabled
  // If enabledLoggers is null, all available loggers are enabled
  const currentEnabled = useMemo(() => {
    if (enabledLoggers === null) {
      return new Set(availableLoggers);
    }
    return enabledLoggers;
  }, [enabledLoggers, availableLoggers]);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setDropdownOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Toggle a specific logger
  const toggleLogger = useCallback((logger: string) => {
    const newEnabled = new Set(currentEnabled);
    if (newEnabled.has(logger)) {
      newEnabled.delete(logger);
    } else {
      newEnabled.add(logger);
    }

    // If all available loggers are now enabled, set to null (no filtering)
    if (newEnabled.size === availableLoggers.length &&
        availableLoggers.every(l => newEnabled.has(l))) {
      onEnabledLoggersChange(null);
      saveEnabledLoggers(null);
    } else {
      onEnabledLoggersChange(newEnabled);
      saveEnabledLoggers(newEnabled);
    }
  }, [currentEnabled, availableLoggers, onEnabledLoggersChange]);

  // Select all loggers
  const selectAll = useCallback(() => {
    onEnabledLoggersChange(null);
    saveEnabledLoggers(null);
  }, [onEnabledLoggersChange]);

  // Deselect all loggers
  const deselectAll = useCallback(() => {
    const newEnabled = new Set<string>();
    onEnabledLoggersChange(newEnabled);
    saveEnabledLoggers(newEnabled);
  }, [onEnabledLoggersChange]);

  // Count enabled vs total
  const enabledCount = currentEnabled.size;
  const totalCount = availableLoggers.length;

  // Don't render if no loggers available
  if (availableLoggers.length === 0) {
    return null;
  }

  return (
    <div className="lv-dropdown" ref={dropdownRef}>
      <button
        className={`selector-trigger ${dropdownOpen ? 'open' : ''}`}
        onClick={() => setDropdownOpen(!dropdownOpen)}
        title="Filter by logger namespace"
      >
        <span className="selector-label">
          Loggers ({enabledCount}/{totalCount})
        </span>
        <ChevronDown className={`selector-chevron ${dropdownOpen ? 'rotated' : ''}`} />
      </button>
      {dropdownOpen && (
        <div className="selector-dropdown lv-logger-dropdown">
          <div className="lv-logger-actions">
            <button
              className="lv-logger-action-btn"
              onClick={selectAll}
              disabled={enabledLoggers === null}
            >
              All
            </button>
            <button
              className="lv-logger-action-btn"
              onClick={deselectAll}
              disabled={enabledCount === 0}
            >
              None
            </button>
          </div>
          <div className="lv-logger-list">
            {availableLoggers.map(logger => (
              <label key={logger} className="dropdown-item">
                <input
                  type="checkbox"
                  checked={currentEnabled.has(logger)}
                  onChange={() => toggleLogger(logger)}
                />
                <span className="lv-logger-name">{logger}</span>
              </label>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
