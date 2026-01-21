/**
 * Hook for log-related state and actions.
 *
 * TODO: Implement using dedicated logs WebSocket.
 * Currently returns placeholder/empty values.
 */

import type { LogLevel, LogEntry } from '../types/build';

export function useLogs() {
  // Placeholder values - logs will be implemented via dedicated WebSocket
  return {
    logEntries: [] as LogEntry[],
    filteredLogs: [] as LogEntry[],
    enabledLogLevels: ['INFO', 'WARNING', 'ERROR', 'ALERT'] as LogLevel[],
    logSearchQuery: '',
    logTimestampMode: 'absolute' as 'absolute' | 'delta',
    logAutoScroll: true,
    isLoadingLogs: false,
    logCounts: {
      DEBUG: 0,
      INFO: 0,
      WARNING: 0,
      ERROR: 0,
      ALERT: 0,
    },
    logTotalCount: 0,
    logHasMore: false,
    selectedBuildName: null as string | null,
    selectedProjectName: null as string | null,
    toggleLogLevel: (_level: LogLevel) => {
      // TODO: Implement via logs WebSocket
    },
    setSearchQuery: (_query: string) => {
      // TODO: Implement via logs WebSocket
    },
    toggleTimestampMode: () => {
      // TODO: Implement via logs WebSocket
    },
    setAutoScroll: (_enabled: boolean) => {
      // TODO: Implement via logs WebSocket
    },
  };
}
