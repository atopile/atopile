/**
 * App Provider - Wraps the application with necessary providers and setup.
 *
 * This component:
 * - Establishes WebSocket connection to the Python backend
 * - Provides the Zustand store to the component tree
 * - Handles connection state display
 */

import React, { useEffect, ReactNode } from 'react';
import { useConnection } from './hooks/useConnection';
import { useStore } from './store';

interface AppProviderProps {
  children: ReactNode;
}

/**
 * Connection status banner for development.
 */
function ConnectionBanner() {
  const isConnected = useStore((state) => state.isConnected);

  if (isConnected) return null;

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        background: '#dc3545',
        color: 'white',
        padding: '4px 8px',
        fontSize: '12px',
        textAlign: 'center',
        zIndex: 9999,
      }}
    >
      Disconnected from backend - reconnecting...
    </div>
  );
}

/**
 * AppProvider wraps the application with necessary setup.
 */
export function AppProvider({ children }: AppProviderProps) {
  // Initialize WebSocket connection
  useConnection();

  return (
    <>
      <ConnectionBanner />
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
