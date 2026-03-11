/**
 * Utility functions for the log viewer.
 * Ported from mainline, uses shared search utilities.
 */

import type { CSSProperties } from 'react';
import type {
  TreeNode,
  LogTreeGroup,
  TimeMode,
  SourceMode,
} from '../../shared/types';
import type { UiLogEntry } from '../../shared/generated-types';
import type { SearchOptions } from '../shared/utils/searchUtils';
import { createSearchMatcher, highlightMatches } from '../shared/utils/searchUtils';
import { formatSource } from '../shared/utils';

// Re-export shared utilities for convenience
export { ansiConverter, hashStringToColor, formatTimestamp } from '../shared/utils';
import { ansiConverter, hashStringToColor, formatTimestamp } from '../shared/utils';

// --- Core utilities ---

export function isSeparatorLine(message: string): { isSeparator: boolean; char: '-' | '=' | null; label: string | null } {
  const trimmed = message.trim();
  const hasDashes = /-{6,}/.test(trimmed);
  const hasEquals = /={6,}/.test(trimmed);

  if (!hasDashes && !hasEquals) {
    return { isSeparator: false, char: null, label: null };
  }

  const char = hasEquals ? '=' : '-';
  const sepRegex = char === '=' ? /={6,}/g : /-{6,}/g;
  const label = trimmed.replace(sepRegex, '').trim() || null;
  return { isSeparator: true, char, label };
}

export function parseTreeDepth(message: string): { depth: number; content: string } {
  const match = message.match(/^([·.]+)/);
  if (!match) return { depth: 0, content: message };
  const depth = match[1].length;
  return { depth, content: message.slice(depth) };
}

// --- Tree building ---

export function buildTreeHierarchy(entries: Array<{ entry: UiLogEntry; depth: number; content: string }>): TreeNode {
  if (entries.length === 0) throw new Error('Cannot build tree from empty entries');

  const root: TreeNode = {
    entry: entries[0].entry,
    depth: entries[0].depth,
    content: entries[0].content,
    children: [],
  };

  const stack: TreeNode[] = [root];
  for (let i = 1; i < entries.length; i++) {
    const { entry, depth, content } = entries[i];
    const node: TreeNode = { entry, depth, content, children: [] };

    while (stack.length > 1 && stack[stack.length - 1].depth >= depth) {
      stack.pop();
    }
    stack[stack.length - 1].children.push(node);
    stack.push(node);
  }

  return root;
}

export function groupLogsIntoTrees(logs: UiLogEntry[]): LogTreeGroup[] {
  const groups: LogTreeGroup[] = [];
  let currentEntries: Array<{ entry: UiLogEntry; depth: number; content: string }> = [];

  for (const entry of logs) {
    const { depth, content } = parseTreeDepth(entry.message);

    if (depth === 0) {
      if (currentEntries.length > 0) {
        const root = buildTreeHierarchy(currentEntries);
        groups.push({ type: currentEntries.length > 1 ? 'tree' : 'standalone', root });
        currentEntries = [];
      }
      currentEntries.push({ entry, depth: 0, content: entry.message });
    } else {
      if (currentEntries.length > 0) {
        currentEntries.push({ entry, depth, content });
      } else {
        const orphanNode: TreeNode = { entry, depth, content, children: [] };
        groups.push({ type: 'standalone', root: orphanNode });
      }
    }
  }

  if (currentEntries.length > 0) {
    const root = buildTreeHierarchy(currentEntries);
    groups.push({ type: currentEntries.length > 1 ? 'tree' : 'standalone', root });
  }

  return groups;
}

// --- Filtering ---

export function filterLogs(
  logs: UiLogEntry[],
  search: string,
  sourceFilter: string,
  searchOptions: SearchOptions = { isRegex: false },
  sourceOptions: SearchOptions = { isRegex: false },
): UiLogEntry[] {
  const messageMatcher = createSearchMatcher(search, searchOptions);
  const sourceMatcher = createSearchMatcher(sourceFilter, sourceOptions);

  return logs.filter(log => {
    if (search.trim() && !messageMatcher(log.message).matches) return false;
    if (sourceFilter.trim()) {
      const sourceStr = log.sourceFile ? `${log.sourceFile}:${log.sourceLine || ''}` : '';
      const loggerStr = log.loggerName || '';
      if (!sourceMatcher(`${sourceStr} ${loggerStr}`).matches) return false;
    }
    return true;
  });
}

// --- Logger filter helpers ---

export function getTopLevelLogger(loggerName: string | undefined | null): string | null {
  if (!loggerName) return null;
  return loggerName.split('.')[0] || null;
}

export function getUniqueTopLevelLoggers(logs: UiLogEntry[]): string[] {
  const set = new Set<string>();
  for (const log of logs) {
    const top = getTopLevelLogger(log.loggerName);
    if (top) set.add(top);
  }
  return Array.from(set).sort();
}

export function loadEnabledLoggers(): Set<string> | null {
  try {
    const stored = localStorage.getItem('lv-loggerFilter');
    if (stored) {
      const parsed = JSON.parse(stored);
      if (Array.isArray(parsed)) return new Set(parsed);
    }
  } catch { /* ignore */ }
  return null;
}

export function saveEnabledLoggers(enabled: Set<string> | null): void {
  if (enabled === null) {
    localStorage.removeItem('lv-loggerFilter');
  } else {
    localStorage.setItem('lv-loggerFilter', JSON.stringify(Array.from(enabled)));
  }
}

export function filterByLoggers(logs: UiLogEntry[], enabledLoggers: Set<string> | null): UiLogEntry[] {
  if (enabledLoggers === null) return logs;
  return logs.filter(log => {
    const topLevel = getTopLevelLogger(log.loggerName);
    if (!topLevel) return true;
    return enabledLoggers.has(topLevel);
  });
}

// --- Display transform ---

export function computeRowDisplay(
  entry: UiLogEntry, content: string, search: string, searchOptions: SearchOptions,
  timeMode: TimeMode, sourceMode: SourceMode, firstTimestamp: number,
) {
  const ts = formatTimestamp(entry.timestamp, timeMode, firstTimestamp);
  const html = highlightMatches(ansiConverter.toHtml(content), search, searchOptions);
  const sourceColor = sourceMode === 'source'
    ? (entry.sourceFile ? hashStringToColor(entry.sourceFile) : undefined)
    : (entry.loggerName ? hashStringToColor(entry.loggerName) : undefined);
  const sourceStyle: CSSProperties | undefined = sourceColor
    ? ({ '--lv-source-accent': sourceColor } as CSSProperties) : undefined;
  const loggerShort = entry.loggerName?.split('.').pop() || '';
  const sourceDisplayValue = sourceMode === 'source'
    ? (formatSource(entry.sourceFile, entry.sourceLine) || '\u2014')
    : (loggerShort || '\u2014');
  const sourceTooltip = sourceMode === 'source' ? (entry.sourceFile || '') : (entry.loggerName || '');
  return { ts, html, sourceStyle, sourceDisplayValue, sourceTooltip };
}

// --- localStorage settings ---

export const LOG_SETTINGS_DEFAULTS: Record<string, string> = {
  'lv-levelFull': 'true',
  'lv-timeMode': 'delta',
  'lv-sourceMode': 'source',
  'lv-logLevels': JSON.stringify(['INFO', 'WARNING', 'ERROR', 'ALERT']),
};

export function initLogSettings(): void {
  for (const [key, value] of Object.entries(LOG_SETTINGS_DEFAULTS)) {
    if (localStorage.getItem(key) === null) {
      localStorage.setItem(key, value);
    }
  }
}

// --- Tree helpers ---

export function countDescendants(node: TreeNode): number {
  return node.children.length + node.children.reduce((sum, c) => sum + countDescendants(c), 0);
}
