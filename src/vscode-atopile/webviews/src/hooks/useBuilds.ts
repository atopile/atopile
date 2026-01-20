/**
 * Hook for build-related state and actions.
 */

import { useCallback } from 'react';
import { useStore, useSelectedBuild } from '../store';
import { api } from '../api/client';
import { sendAction } from '../api/websocket';

export function useBuilds() {
  const builds = useStore((state) => state.builds);
  const queuedBuilds = useStore((state) => state.queuedBuilds);
  const selectedBuildName = useStore((state) => state.selectedBuildName);

  const selectedBuild = useSelectedBuild();

  const selectBuild = useCallback((buildName: string | null) => {
    // Optimistic update
    useStore.getState().selectBuild(buildName);
    // Notify backend
    sendAction('selectBuild', { buildName });
  }, []);

  const startBuild = useCallback(
    async (projectRoot: string, targetNames: string[]) => {
      try {
        const build = await api.builds.start(projectRoot, targetNames);
        // Backend will broadcast state update via WebSocket
        return build;
      } catch (error) {
        console.error('Failed to start build:', error);
        throw error;
      }
    },
    []
  );

  const cancelBuild = useCallback(async (buildId: string) => {
    try {
      await api.builds.cancel(buildId);
      // Backend will broadcast state update via WebSocket
    } catch (error) {
      console.error('Failed to cancel build:', error);
      throw error;
    }
  }, []);

  // Combined list for UI (active + completed)
  const allBuilds = [...queuedBuilds, ...builds];

  return {
    builds,
    queuedBuilds,
    allBuilds,
    selectedBuild,
    selectedBuildName,
    selectBuild,
    startBuild,
    cancelBuild,
  };
}
