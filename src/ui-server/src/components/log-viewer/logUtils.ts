/**
 * Shared utility functions for log viewers
 */

import AnsiToHtml from 'ansi-to-html';
import { SOURCE_COLORS, LogEntry, TreeNode, LogTreeGroup, TimeMode } from './logTypes';
import type { StructuredTraceback } from '../StackInspector';

// ANSI to HTML converter
export const ansiConverter = new AnsiToHtml({
  fg: '#e5e5e5',
  bg: 'transparent',
  newline: true,
  escapeXML: true,
});

// Hash string to consistent color index
export function hashStringToColor(str: string): string {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = ((hash << 5) - hash) + str.charCodeAt(i);
    hash = hash & hash; // Convert to 32-bit integer
  }
  return SOURCE_COLORS[Math.abs(hash) % SOURCE_COLORS.length];
}

// Highlight search matches in text
export function highlightText(text: string, search: string): string {
  if (!search.trim()) return text;
  const escaped = search.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const regex = new RegExp(`(${escaped})`, 'gi');
  return text.replace(regex, '<mark class="lv-highlight">$1</mark>');
}

// Detect separator lines: messages with >5 consecutive '-' or '=' characters
export function isSeparatorLine(message: string): { isSeparator: boolean; char: '-' | '=' | null; label: string | null } {
  const trimmed = message.trim();

  // Check if line contains 6+ consecutive dashes or equals
  const hasDashes = /-{6,}/.test(trimmed);
  const hasEquals = /={6,}/.test(trimmed);

  if (!hasDashes && !hasEquals) {
    return { isSeparator: false, char: null, label: null };
  }

  const char = hasEquals ? '=' : '-';
  const sepRegex = char === '=' ? /={6,}/g : /-{6,}/g;

  // Extract label by removing all separator sequences
  const label = trimmed.replace(sepRegex, '').trim() || null;

  return { isSeparator: true, char, label };
}

// Detect tree depth from leading dot characters (· or .)
export function parseTreeDepth(message: string): { depth: number; content: string } {
  // Match leading middle dots (·) or regular dots (.)
  const match = message.match(/^([·.]+)/);
  if (!match) {
    return { depth: 0, content: message };
  }
  const dots = match[1];
  const depth = dots.length;
  const content = message.slice(depth);
  return { depth, content };
}

// Format timestamp based on mode
export function formatTimestamp(ts: string, mode: TimeMode, firstTimestamp: number): string {
  if (mode === 'wall') {
    // hh:mm:ss format (no milliseconds)
    const timePart = ts.split('T')[1];
    if (!timePart) return ts;
    const hms = timePart.split('.')[0];
    return hms;
  } else {
    // Delta ms since first log
    const logTime = new Date(ts).getTime();
    const delta = logTime - firstTimestamp;
    if (delta < 1000) return `+${delta}ms`;
    if (delta < 60000) return `+${(delta / 1000).toFixed(1)}s`;
    return `+${(delta / 60000).toFixed(1)}m`;
  }
}

// Format source location
export function formatSource(file: string | null | undefined, line: number | null | undefined): string | null {
  if (!file) return null;
  // Get just the filename from the path
  const filename = file.split('/').pop() || file;
  return line ? `${filename}:${line}` : filename;
}

/**
 * Try to parse python_traceback as structured JSON.
 * Returns null if not valid structured traceback.
 */
export function tryParseStructuredTraceback(pythonTraceback: string | null | undefined): StructuredTraceback | null {
  if (!pythonTraceback) return null;

  try {
    const parsed = JSON.parse(pythonTraceback);
    // Validate it has the expected structure
    if (
      typeof parsed === 'object' &&
      parsed !== null &&
      typeof parsed.exc_type === 'string' &&
      typeof parsed.exc_message === 'string' &&
      Array.isArray(parsed.frames)
    ) {
      return parsed as StructuredTraceback;
    }
  } catch {
    // Not JSON, it's plain text traceback
  }

  return null;
}

// Build hierarchical tree from flat list of entries with depths
export function buildTreeHierarchy(entries: Array<{ entry: LogEntry; depth: number; content: string }>): TreeNode {
  if (entries.length === 0) {
    throw new Error('Cannot build tree from empty entries');
  }

  const root: TreeNode = {
    entry: entries[0].entry,
    depth: entries[0].depth,
    content: entries[0].content,
    children: []
  };

  // Stack to track parent nodes at each depth
  const stack: TreeNode[] = [root];

  for (let i = 1; i < entries.length; i++) {
    const { entry, depth, content } = entries[i];
    const node: TreeNode = { entry, depth, content, children: [] };

    // Pop stack until we find the parent (node with depth < current)
    while (stack.length > 1 && stack[stack.length - 1].depth >= depth) {
      stack.pop();
    }

    // Add as child of current top of stack
    stack[stack.length - 1].children.push(node);

    // Push this node to stack (it might be parent of next entries)
    stack.push(node);
  }

  return root;
}

// Group logs into tree structures
export function groupLogsIntoTrees(logs: LogEntry[]): LogTreeGroup[] {
  const groups: LogTreeGroup[] = [];
  let currentEntries: Array<{ entry: LogEntry; depth: number; content: string }> = [];

  for (const entry of logs) {
    const { depth, content } = parseTreeDepth(entry.message);

    if (depth === 0) {
      // Depth 0 = potential root or standalone
      // First, close any existing tree
      if (currentEntries.length > 0) {
        const root = buildTreeHierarchy(currentEntries);
        groups.push({
          type: currentEntries.length > 1 ? 'tree' : 'standalone',
          root
        });
        currentEntries = [];
      }
      // Start a new potential tree
      currentEntries.push({ entry, depth: 0, content: entry.message });
    } else {
      // Depth > 0 = child of current tree
      if (currentEntries.length > 0) {
        currentEntries.push({ entry, depth, content });
      } else {
        // Orphan child (no root) - treat as standalone
        const orphanNode: TreeNode = { entry, depth, content, children: [] };
        groups.push({ type: 'standalone', root: orphanNode });
      }
    }
  }

  // Don't forget the last group
  if (currentEntries.length > 0) {
    const root = buildTreeHierarchy(currentEntries);
    groups.push({
      type: currentEntries.length > 1 ? 'tree' : 'standalone',
      root
    });
  }

  return groups;
}

// Filter logs by search and source filter
export function filterLogs(
  logs: LogEntry[],
  search: string,
  sourceFilter: string
): LogEntry[] {
  return logs.filter(log => {
    // Message search
    if (search.trim() && !log.message.toLowerCase().includes(search.toLowerCase())) {
      return false;
    }
    // Source/Logger filter - searches both regardless of display mode
    if (sourceFilter.trim()) {
      const sourceStr = log.source_file ? `${log.source_file}:${log.source_line || ''}` : '';
      const loggerStr = log.logger_name || '';
      const combined = `${sourceStr} ${loggerStr}`.toLowerCase();
      if (!combined.includes(sourceFilter.toLowerCase())) {
        return false;
      }
    }
    return true;
  });
}

// Get stored display setting with default
export function getStoredSetting<T>(key: string, defaultValue: T, validator?: (v: unknown) => boolean): T {
  const stored = localStorage.getItem(key);
  if (stored !== null) {
    if (typeof defaultValue === 'boolean') {
      return (stored === 'true') as unknown as T;
    }
    if (validator && !validator(stored)) {
      return defaultValue;
    }
    return stored as unknown as T;
  }
  return defaultValue;
}
