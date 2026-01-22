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
