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
import { Toaster } from 'sonner';
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

  // Handle workspace folders from VS Code extension
  useEffect(() => {
    function handleMessage(event: MessageEvent) {
      const data = event?.data as { type?: string; folders?: unknown };
      if (data?.type !== 'workspace-folders') return;
      if (!Array.isArray(data.folders)) return;
      // Update injected workspace folders for future reads
      (window as { __ATOPILE_WORKSPACE_FOLDERS__?: string[] }).__ATOPILE_WORKSPACE_FOLDERS__ =
        data.folders as string[];
      sendAction('setWorkspaceFolders', { folders: data.folders as string[] });
    }

    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, []);

  return (
    <>
      <Toaster
        position="bottom-left"
        closeButton
        toastOptions={{
          duration: 5000,
        }}
      />
      {children}
    </>
  );
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
