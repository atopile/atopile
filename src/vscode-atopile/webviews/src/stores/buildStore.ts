/**
 * Build state store using Zustand.
 * Receives data from VS Code extension via postMessage.
 */

import { create } from 'zustand';
import type { Build, BuildStage, LogEntry, LogLevel } from '../types/build';

interface ActionButton {
  id: string;
  label: string;
  icon: string;
  tooltip: string;
}

interface BuildState {
  // Sidebar data
  builds: Build[];
  actionButtons: ActionButton[];
  selectedBuildName: string | null;
  selectedStageName: string | null;
  isConnected: boolean;

  // Log viewer data
  logEntries: LogEntry[];
  enabledLevels: Set<LogLevel>;
  isLoadingLogs: boolean;
  currentLogFile: string | null;

  // Actions
  setBuilds: (builds: Build[]) => void;
  setActionButtons: (buttons: ActionButton[]) => void;
  setSelectedBuild: (name: string | null) => void;
  setSelectedStage: (name: string | null) => void;
  setConnected: (connected: boolean) => void;
  setLogEntries: (entries: LogEntry[]) => void;
  toggleLevel: (level: LogLevel) => void;
  setLoadingLogs: (loading: boolean) => void;
  setCurrentLogFile: (file: string | null) => void;

  // Helpers
  getSelectedBuild: () => Build | null;
  getSelectedStage: () => BuildStage | null;
  getFilteredLogEntries: () => LogEntry[];
  getLevelCounts: () => Record<LogLevel, number>;
}

const DEFAULT_ENABLED_LEVELS: Set<LogLevel> = new Set(['INFO', 'WARNING', 'ERROR', 'ALERT']);

export const useBuildStore = create<BuildState>((set, get) => ({
  builds: [],
  actionButtons: [],
  selectedBuildName: null,
  selectedStageName: null,
  isConnected: false,

  logEntries: [],
  enabledLevels: new Set(DEFAULT_ENABLED_LEVELS),
  isLoadingLogs: false,
  currentLogFile: null,

  setBuilds: (builds) => set({ builds }),
  setActionButtons: (actionButtons) => set({ actionButtons }),
  setSelectedBuild: (selectedBuildName) => set({ selectedBuildName, selectedStageName: null }),
  setSelectedStage: (selectedStageName) => set({ selectedStageName }),
  setConnected: (isConnected) => set({ isConnected }),
  setLogEntries: (logEntries) => set({ logEntries }),
  setLoadingLogs: (isLoadingLogs) => set({ isLoadingLogs }),
  setCurrentLogFile: (currentLogFile) => set({ currentLogFile }),

  toggleLevel: (level) => {
    const { enabledLevels } = get();
    const newLevels = new Set(enabledLevels);
    if (newLevels.has(level)) {
      newLevels.delete(level);
    } else {
      newLevels.add(level);
    }
    set({ enabledLevels: newLevels });
  },

  getSelectedBuild: () => {
    const { builds, selectedBuildName } = get();
    if (!selectedBuildName) return null;
    return builds.find(b => b.display_name === selectedBuildName) ?? null;
  },

  getSelectedStage: () => {
    const { selectedStageName } = get();
    const build = get().getSelectedBuild();
    if (!build || !selectedStageName || !build.stages) return null;
    return build.stages.find(s => s.name === selectedStageName) ?? null;
  },

  getFilteredLogEntries: () => {
    const { logEntries, enabledLevels } = get();
    return logEntries.filter(entry => enabledLevels.has(entry.level));
  },

  getLevelCounts: () => {
    const { logEntries } = get();
    return {
      DEBUG: logEntries.filter(e => e.level === 'DEBUG').length,
      INFO: logEntries.filter(e => e.level === 'INFO').length,
      WARNING: logEntries.filter(e => e.level === 'WARNING').length,
      ERROR: logEntries.filter(e => e.level === 'ERROR').length,
      ALERT: logEntries.filter(e => e.level === 'ALERT').length,
    };
  },
}));
