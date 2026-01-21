/**
 * BuildQueuePanelConnected - Connected version using hooks.
 *
 * This component:
 * - Uses useBuilds hook to get state and actions
 * - Passes data to the presentational BuildQueuePanel
 * - No props required - gets everything from store
 */

import { useBuilds } from '../hooks';
import { BuildQueuePanel, QueuedBuild } from './BuildQueuePanel';

export function BuildQueuePanelConnected() {
  const { queuedBuilds, cancelBuild } = useBuilds();

  // Transform store builds to the format expected by BuildQueuePanel
  const transformedBuilds: QueuedBuild[] = queuedBuilds.map((build) => ({
    buildId: build.buildId || build.name,
    status: build.status === 'failed' ? 'failed' : build.status as QueuedBuild['status'],
    projectRoot: build.projectRoot || '',
    targets: build.targets || [],
    entry: build.entry,
    startedAt: build.startedAt || Date.now() / 1000,
    elapsedSeconds: build.elapsedSeconds,
    stages: build.stages?.map((s) => ({
      name: s.name,
      displayName: s.displayName,
      status: s.status,
      elapsedSeconds: s.elapsedSeconds,
    })),
    error: build.error,
  }));

  const handleCancelBuild = (buildId: string) => {
    cancelBuild(buildId).catch(console.error);
  };

  return (
    <BuildQueuePanel
      builds={transformedBuilds}
      onCancelBuild={handleCancelBuild}
    />
  );
}
