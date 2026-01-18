/**
 * Build state store using Zustand.
 *
 * Manages build summary data, polling, and selection state.
 */

import { create } from 'zustand';
import type { BuildSummary, Build, BuildStage, LogEntry, LogLevel } from '../types/build';

// Set of enabled log levels (DEBUG off by default)
type EnabledLevels = Set<LogLevel>;

// API base URL - set by VS Code webview or defaults to current origin
declare global {
  interface Window {
    __ATO_API_URL__?: string;
  }
}

function getApiBaseUrl(): string {
  // Check for URL set by VS Code webview
  if (window.__ATO_API_URL__) {
    return window.__ATO_API_URL__;
  }
  // Default to current origin (for standalone/dev use)
  return '';
}

interface BuildState {
  // Data
  summary: BuildSummary | null;
  isLoading: boolean;
  loadError: string | null;
  lastUpdated: Date | null;

  // Selection
  selectedBuild: string | null;
  selectedStage: string | null;

  // Log content (all entries, frontend filters by level)
  logEntries: LogEntry[] | null;
  logLoading: boolean;
  logError: string | null;

  // Level filters (individually selectable)
  enabledLevels: EnabledLevels;

  // Polling
  isPolling: boolean;
  pollInterval: number;

  // Actions
  fetchSummary: () => Promise<void>;
  selectBuild: (buildName: string | null) => void;
  selectStage: (stageName: string | null) => void;
  fetchLog: (buildName: string, stage: BuildStage) => Promise<void>;
  toggleLevel: (level: LogLevel) => void;
  startPolling: (interval?: number) => void;
  stopPolling: () => void;

  // Helpers
  getSelectedBuild: () => Build | null;
  getSelectedStage: () => BuildStage | null;
  getFilteredLogEntries: () => LogEntry[];
}

let pollTimer: ReturnType<typeof setInterval> | null = null;

// Default: all levels enabled except DEBUG
const DEFAULT_ENABLED_LEVELS: EnabledLevels = new Set(['INFO', 'WARNING', 'ERROR', 'ALERT']);

export const useBuildStore = create<BuildState>((set, get) => ({
  summary: null,
  isLoading: false,
  loadError: null,
  lastUpdated: null,

  selectedBuild: null,
  selectedStage: null,

  logEntries: null,
  logLoading: false,
  logError: null,

  enabledLevels: new Set(DEFAULT_ENABLED_LEVELS),

  isPolling: false,
  pollInterval: 500,

  fetchSummary: async () => {
    set({ isLoading: true, loadError: null });

    try {
      const response = await fetch(`${getApiBaseUrl()}/api/summary`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data: BuildSummary = await response.json();

      // Auto-select first build if none selected
      const { selectedBuild } = get();
      if (!selectedBuild && data.builds.length > 0) {
        set({
          summary: data,
          isLoading: false,
          lastUpdated: new Date(),
          selectedBuild: data.builds[0].display_name,
        });
      } else {
        set({
          summary: data,
          isLoading: false,
          lastUpdated: new Date(),
        });
      }
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Unknown error';
      set({
        isLoading: false,
        loadError: `Failed to load summary: ${message}`,
      });
    }
  },

  selectBuild: (buildName: string | null) => {
    set({ selectedBuild: buildName, selectedStage: null, logEntries: null });
  },

  selectStage: (stageName: string | null) => {
    set({ selectedStage: stageName, logEntries: null });
  },

  fetchLog: async (buildName: string, stage: BuildStage) => {
    set({ logLoading: true, logError: null });

    try {
      // Get the log file path from the stage
      const logFile = stage.log_file;
      if (!logFile) {
        throw new Error('No log file available for this stage');
      }

      // Extract just the filename from the full path
      const filename = logFile.split('/').pop() || logFile;

      const response = await fetch(`${getApiBaseUrl()}/api/logs/${encodeURIComponent(buildName)}/${encodeURIComponent(filename)}`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const content = await response.text();

      // Parse JSON Lines format
      const entries: LogEntry[] = content
        .split('\n')
        .filter((line) => line.trim())
        .map((line) => {
          try {
            return JSON.parse(line) as LogEntry;
          } catch {
            // If parsing fails, create a fallback entry
            return {
              timestamp: new Date().toISOString(),
              level: 'INFO' as const,
              logger: 'unknown',
              message: line,
            };
          }
        });

      set({
        logEntries: entries,
        logLoading: false,
      });
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Unknown error';
      set({
        logLoading: false,
        logError: message,
      });
    }
  },

  toggleLevel: (level: LogLevel) => {
    const { enabledLevels } = get();
    const newLevels = new Set(enabledLevels);
    if (newLevels.has(level)) {
      newLevels.delete(level);
    } else {
      newLevels.add(level);
    }
    set({ enabledLevels: newLevels });
  },

  startPolling: (interval?: number) => {
    const { fetchSummary, pollInterval } = get();

    // Clear existing timer
    if (pollTimer) {
      clearInterval(pollTimer);
    }

    const actualInterval = interval ?? pollInterval;
    set({ isPolling: true, pollInterval: actualInterval });

    // Initial fetch
    fetchSummary();

    // Start polling
    pollTimer = setInterval(() => {
      fetchSummary();
    }, actualInterval);
  },

  stopPolling: () => {
    if (pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
    set({ isPolling: false });
  },

  getSelectedBuild: () => {
    const { summary, selectedBuild } = get();
    if (!summary || !selectedBuild) return null;
    return summary.builds.find(b => b.display_name === selectedBuild) ?? null;
  },

  getSelectedStage: () => {
    const { selectedStage } = get();
    const build = get().getSelectedBuild();
    if (!build || !selectedStage || !build.stages) return null;
    return build.stages.find(s => s.name === selectedStage) ?? null;
  },

  getFilteredLogEntries: () => {
    const { logEntries, enabledLevels } = get();
    if (!logEntries) return [];
    return logEntries.filter(entry => enabledLevels.has(entry.level));
  },
}));
