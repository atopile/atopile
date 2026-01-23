/**
 * Hook for build-related state and actions.
 */

import { useCallback } from 'react';
import { useStore, useSelectedBuild } from '../store';
import { sendAction } from '../api/websocket';

export function useBuilds() {
  const builds = useStore((state) => state.builds);
  const queuedBuilds = useStore((state) => state.queuedBuilds);
  const selectedBuildName = useStore((state) => state.selectedBuildName);

  const selectedBuild = useSelectedBuild();

  const selectBuild = useCallback((buildName: string | null) => {
    useStore.getState().selectBuild(buildName);
  }, []);

  const startBuild = useCallback(
    async (projectRoot: string, targetNames: string[]) => {
      sendAction('build', { projectRoot, targets: targetNames });
    },
    []
  );

  const cancelBuild = useCallback(async (buildId: string) => {
    sendAction('cancelBuild', { buildId });
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
