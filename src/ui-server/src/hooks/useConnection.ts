/**
 * Hook for WebSocket connection management.
 */

import { useEffect } from 'react';
import { useStore } from '../store';
import { connect, disconnect, isConnected, sendAction } from '../api/websocket';
import { onExtensionMessage, postMessage, requestSelectionState } from '../api/vscodeApi';

// Track pending glb-only builds to report success/failure to extension
let pendingGlbBuildIds: Set<string> = new Set();

/**
 * Hook to manage WebSocket connection lifecycle.
 * Call this once at the app root level.
 */
export function useConnection() {
  const storeIsConnected = useStore((state) => state.isConnected);

  useEffect(() => {
    // Connect on mount
    connect();

    // Listen for action results to track glb-only build IDs
    const handleActionResult = (event: Event) => {
      const customEvent = event as CustomEvent;
      const message = customEvent.detail;
      if (message?.action === 'build') {
        // Check if this is a response to a glb-only build
        const includeTargets = message?.payload?.includeTargets;
        const isGlbOnly = Array.isArray(includeTargets) && includeTargets.includes('glb-only');

        if (isGlbOnly) {
          if (message?.result?.success) {
            // Build was queued successfully - track the build ID
            const buildId = message?.result?.build_id ?? message?.result?.buildId;
            const buildIds = message?.result?.build_ids ?? message?.result?.buildIds;
            const ids: string[] = [];
            if (typeof buildId === 'string') ids.push(buildId);
            if (Array.isArray(buildIds)) {
              for (const id of buildIds) {
                if (typeof id === 'string') ids.push(id);
              }
            }
            for (const id of ids) {
              pendingGlbBuildIds.add(id);
            }
          } else {
            // Build failed to start - report failure immediately
            const error = message?.result?.error ?? message?.error ?? 'Failed to start build';
            postMessage({
              type: 'threeDModelBuildResult',
              success: false,
              error: typeof error === 'string' ? error : 'Failed to start build',
            });
          }
        }
      }
    };
    window.addEventListener('atopile:action_result', handleActionResult);

    // Subscribe to build state changes to detect glb-only build failures
    // NOTE: We only report failures here. Success is detected by the file watcher
    // in the extension, which avoids race conditions with build history updates.
    const unsubscribeBuilds = useStore.subscribe(
      (state) => state.builds,
      (builds) => {
        // Check if any pending glb-only build has failed or been cancelled
        for (const buildId of [...pendingGlbBuildIds]) {
          const build = builds.find((b) => b.buildId === buildId);

          if (build) {
            // Build is still in active builds
            if (build.status === 'failed' || build.status === 'cancelled') {
              pendingGlbBuildIds.delete(buildId);
              postMessage({
                type: 'threeDModelBuildResult',
                success: false,
                error: build.error || (build.status === 'cancelled' ? 'Build was cancelled' : 'Build failed'),
              });
            } else if (build.status === 'success' || build.status === 'warning') {
              // Build succeeded - notify extension to check for file and update status
              pendingGlbBuildIds.delete(buildId);
              postMessage({
                type: 'threeDModelBuildResult',
                success: true,
              });
            }
          } else {
            // Build is no longer in active builds - check if it completed successfully
            // by looking at history, but only for definitive terminal states
            const historyBuilds = useStore.getState().buildHistory;
            const historyBuild = historyBuilds.find((b) => b.buildId === buildId);
            if (historyBuild) {
              // Only report if we have a definitive terminal state
              if (historyBuild.status === 'success' || historyBuild.status === 'warning') {
                pendingGlbBuildIds.delete(buildId);
                postMessage({
                  type: 'threeDModelBuildResult',
                  success: true,
                });
              } else if (historyBuild.status === 'failed' || historyBuild.status === 'cancelled') {
                const errorMsg = historyBuild.error || (historyBuild.status === 'cancelled' ? 'Build was cancelled' : 'Build failed');
                // Skip "interrupted" errors from history - these are stale and shouldn't affect current builds
                if (errorMsg.includes('interrupted')) {
                  pendingGlbBuildIds.delete(buildId);
                } else {
                  pendingGlbBuildIds.delete(buildId);
                  postMessage({
                    type: 'threeDModelBuildResult',
                    success: false,
                    error: errorMsg,
                  });
                }
              }
              // If status is still 'building' or 'queued' in history, ignore it
              // as it might be stale data (the "interrupted" issue)
            }
          }
        }
      }
    );

    // Handle messages from extension (build requests, etc.)
    const unsubscribe = onExtensionMessage((message) => {
      switch (message.type) {
        case 'triggerBuild':
          // If this is a new glb-only build, clear any previous pending builds
          // to avoid stale tracking
          if (Array.isArray(message.includeTargets) && message.includeTargets.includes('glb-only')) {
            pendingGlbBuildIds.clear();
          }
          // Forward build request to backend via WebSocket
          sendAction('build', {
            projectRoot: message.projectRoot,
            targets: message.targets,
            requestId: message.requestId,
            includeTargets: message.includeTargets,
            frozen: message.frozen,
            excludeTargets: message.excludeTargets,
          });
          break;
        case 'atopileInstalling':
          // Extension is switching to a new atopile version
          useStore.getState().setAtopileConfig({
            isInstalling: true,
            installProgress: {
              message: message.message || 'Switching atopile version...',
            },
            error: null,
          });
          break;
        case 'atopileInstallError':
          // Extension failed to switch atopile version
          useStore.getState().setAtopileConfig({
            isInstalling: false,
            installProgress: null,
            error: message.error || 'Failed to switch atopile version',
          });
          break;
        case 'activeFile': {
          const filePath = message.filePath ?? null;
          const store = useStore.getState();
          store.setActiveEditorFile(filePath);
          if (filePath && filePath.toLowerCase().endsWith('.ato')) {
            store.setLastAtoFile(filePath);
          }
          break;
        }
        case 'selectionState': {
          const projectRoot = message.projectRoot ?? null;
          const targetNames = message.targetNames ?? [];
          const current = useStore.getState();
          if (
            current.selectedProjectRoot === projectRoot &&
            current.selectedTargetNames.length === targetNames.length &&
            current.selectedTargetNames.every((value, index) => value === targetNames[index])
          ) {
            break;
          }
          const selectedProjectName = projectRoot
            ? (current.projects.find((project) => project.root === projectRoot)?.name ?? null)
            : null;
          useStore.setState({
            selectedProjectRoot: projectRoot,
            selectedTargetNames: [...targetNames],
            selectedProjectName,
          });
          break;
        }
      }
    });

    // Ask the extension for the current selection so the store is populated
    // before projects finish loading (avoids null→auto-select→correction cycle).
    requestSelectionState();

    // Disconnect on unmount
    return () => {
      unsubscribe();
      unsubscribeBuilds();
      window.removeEventListener('atopile:action_result', handleActionResult);
      pendingGlbBuildIds.clear();
      disconnect();
    };
  }, []);

  return {
    isConnected: storeIsConnected,
    connect,
    disconnect,
    checkConnection: isConnected,
  };
}
