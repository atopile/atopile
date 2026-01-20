/**
 * Hook for WebSocket connection management.
 */

import { useEffect } from 'react';
import { useStore } from '../store';
import { connect, disconnect, isConnected } from '../api/websocket';

/**
 * Hook to manage WebSocket connection lifecycle.
 * Call this once at the app root level.
 */
export function useConnection() {
  const storeIsConnected = useStore((state) => state.isConnected);

  useEffect(() => {
    // Connect on mount
    connect();

    // Disconnect on unmount
    return () => {
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
