/**
 * Hook for WebSocket connection management.
 */

import { useEffect } from 'react';
import { useStore } from '../store';
import { connect, disconnect, isConnected, sendAction } from '../api/websocket';
import { initExtensionMessageListener, onExtensionMessage } from '../api/vscodeApi';

/**
 * Hook to manage WebSocket connection lifecycle.
 * Call this once at the app root level.
 */
export function useConnection() {
  const storeIsConnected = useStore((state) => state.isConnected);

  useEffect(() => {
    // Connect on mount
    connect();

    // Initialize listener for messages from VS Code extension
    initExtensionMessageListener();

    // Handle messages from extension (build requests, etc.)
    const unsubscribe = onExtensionMessage((message) => {
      switch (message.type) {
        case 'triggerBuild':
          // Forward build request to backend via WebSocket
          sendAction('build', {
            projectRoot: message.projectRoot,
            targets: message.targets,
            requestId: message.requestId,
          });
          break;
        case 'setAtopileInstalling':
          // Forward atopile installing status to backend
          sendAction('setAtopileInstalling', {
            installing: message.installing,
            error: message.error,
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
      }
    });

    // Disconnect on unmount
    return () => {
      unsubscribe();
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
