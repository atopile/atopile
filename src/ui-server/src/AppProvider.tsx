/**
 * App Provider - Wraps the application with necessary providers and setup.
 *
 * This component:
 * - Establishes WebSocket connection to the Python backend
 * - Provides the Zustand store to the component tree
 *
 * Note: Connection status is displayed by individual components (e.g., SidebarNew)
 * rather than a global banner, since some pages (e.g., LogViewer) have their own
 * WebSocket connections with separate status tracking.
 */

import React, { ReactNode, useEffect } from 'react';
import { useConnection } from './hooks/useConnection';
import { sendAction } from './api/websocket';
import { initUILogger } from './ui-logger';

interface AppProviderProps {
  children: ReactNode;
}

/**
 * AppProvider wraps the application with necessary setup.
 */
export function AppProvider({ children }: AppProviderProps) {
  // Initialize WebSocket connection
  useConnection();
  useEffect(() => {
    initUILogger();
  }, []);
  useEffect(() => {
    function handleMessage(event: MessageEvent) {
      const data = event?.data as { type?: string; root?: unknown };
      if (data?.type === 'workspace-root') {
        const root = typeof data.root === 'string' && data.root.length > 0 ? data.root : null;
        (window as { __ATOPILE_WORKSPACE_ROOT__?: string }).__ATOPILE_WORKSPACE_ROOT__ =
          root || undefined;
        const folders = root ? [root] : [];
        sendAction('setWorkspaceFolders', { folders });
        return;
      }
    }

    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, []);

  return <>{children}</>;
}

/**
 * Higher-order component to wrap a component with AppProvider.
 */
export function withAppProvider<P extends object>(
  Component: React.ComponentType<P>
): React.FC<P> {
  return function WrappedComponent(props: P) {
    return (
      <AppProvider>
        <Component {...props} />
      </AppProvider>
    );
  };
}
