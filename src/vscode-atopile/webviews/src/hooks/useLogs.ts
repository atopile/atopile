/**
 * Hook for log-related state and actions.
 */

import { useCallback } from 'react';
import { useStore, useFilteredLogs } from '../store';
import { api } from '../api/client';
import { sendAction } from '../api/websocket';
import type { LogLevel } from '../types/build';

export function useLogs() {
  const logEntries = useStore((state) => state.logEntries);
  const enabledLogLevels = useStore((state) => state.enabledLogLevels);
  const logSearchQuery = useStore((state) => state.logSearchQuery);
  const logTimestampMode = useStore((state) => state.logTimestampMode);
  const logAutoScroll = useStore((state) => state.logAutoScroll);
  const isLoadingLogs = useStore((state) => state.isLoadingLogs);
  const logCounts = useStore((state) => state.logCounts);
  const logTotalCount = useStore((state) => state.logTotalCount);
  const logHasMore = useStore((state) => state.logHasMore);
  const selectedBuildName = useStore((state) => state.selectedBuildName);
  const selectedProjectName = useStore((state) => state.selectedProjectName);

  const filteredLogs = useFilteredLogs();

  const toggleLogLevel = useCallback((level: LogLevel) => {
    // Optimistic update
    useStore.getState().toggleLogLevel(level);
    // Notify backend
    sendAction('toggleLogLevel', { level });
  }, []);

  const setSearchQuery = useCallback((query: string) => {
    // Optimistic update
    useStore.getState().setLogSearchQuery(query);
    // Notify backend
    sendAction('setLogSearchQuery', { query });
  }, []);

  const toggleTimestampMode = useCallback(() => {
    // Optimistic update
    useStore.getState().toggleLogTimestampMode();
    // Notify backend
    sendAction('toggleLogTimestampMode');
  }, []);

  const setAutoScroll = useCallback((enabled: boolean) => {
    // Optimistic update
    useStore.getState().setLogAutoScroll(enabled);
    // Notify backend
    sendAction('setLogAutoScroll', { enabled });
  }, []);

  const fetchLogs = useCallback(async (options?: { buildName?: string; projectName?: string; levels?: string[]; search?: string; limit?: number }) => {
    try {
      const response = await api.logs.query(options);
      useStore.getState().setLogEntries(response.logs);
    } catch (error) {
      console.error('Failed to fetch logs:', error);
    }
  }, []);

  const fetchLogCounts = useCallback(async (buildName?: string, projectName?: string) => {
    try {
      const response = await api.logs.counts(buildName, projectName);
      // Update store with counts (handled via WebSocket typically)
      return response;
    } catch (error) {
      console.error('Failed to fetch log counts:', error);
    }
  }, []);

  return {
    logEntries,
    filteredLogs,
    enabledLogLevels,
    logSearchQuery,
    logTimestampMode,
    logAutoScroll,
    isLoadingLogs,
    logCounts,
    logTotalCount,
    logHasMore,
    selectedBuildName,
    selectedProjectName,
    toggleLogLevel,
    setSearchQuery,
    toggleTimestampMode,
    setAutoScroll,
    fetchLogs,
    fetchLogCounts,
  };
}
