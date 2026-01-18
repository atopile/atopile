/**
 * Build state store using Zustand.
 *
 * Manages build summary data, polling, and selection state.
 */

import { create } from 'zustand';
import type { BuildSummary, Build, BuildStage } from '../types/build';

interface BuildState {
  // Data
  summary: BuildSummary | null;
  isLoading: boolean;
  loadError: string | null;
  lastUpdated: Date | null;

  // Selection
  selectedBuild: string | null;
  selectedStage: string | null;

  // Log content
  logContent: string | null;
  logLoading: boolean;
  logError: string | null;

  // Polling
  isPolling: boolean;
  pollInterval: number;

  // Actions
  fetchSummary: () => Promise<void>;
  selectBuild: (buildName: string | null) => void;
  selectStage: (stageName: string | null) => void;
  fetchLog: (buildName: string, stage: BuildStage, logType: string) => Promise<void>;
  startPolling: (interval?: number) => void;
  stopPolling: () => void;

  // Helpers
  getSelectedBuild: () => Build | null;
  getSelectedStage: () => BuildStage | null;
}

let pollTimer: ReturnType<typeof setInterval> | null = null;

export const useBuildStore = create<BuildState>((set, get) => ({
  summary: null,
  isLoading: false,
  loadError: null,
  lastUpdated: null,

  selectedBuild: null,
  selectedStage: null,

  logContent: null,
  logLoading: false,
  logError: null,

  isPolling: false,
  pollInterval: 500,

  fetchSummary: async () => {
    set({ isLoading: true, loadError: null });

    try {
      const response = await fetch('/api/summary');
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
    set({ selectedBuild: buildName, selectedStage: null, logContent: null });
  },

  selectStage: (stageName: string | null) => {
    set({ selectedStage: stageName, logContent: null });
  },

  fetchLog: async (buildName: string, stage: BuildStage, logType: string) => {
    set({ logLoading: true, logError: null });

    try {
      // Get the log filename from the stage's log_files
      const logFile = stage.log_files[logType];
      if (!logFile) {
        throw new Error(`No ${logType} log available for this stage`);
      }

      // Extract just the filename from the full path
      const filename = logFile.split('/').pop() || logFile;

      const response = await fetch(`/api/logs/${encodeURIComponent(buildName)}/${encodeURIComponent(filename)}`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const content = await response.text();
      set({
        logContent: content,
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
}));
