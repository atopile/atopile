import { useMemo, useEffect } from 'react';
import { Layout } from '@/components';
import { UILogic } from '@/logic';
import { LogicProvider } from '@/hooks';

// Version marker - if you see this in console, you have the latest code
console.log('%c[App] Code version: 2026-01-20T08:30 - Unified sidebar', 'background: blue; color: white; font-size: 16px;');

// Determine API and WebSocket URLs based on environment
function getApiBaseUrl(): string {
  if (import.meta.env.DEV) {
    return '/api';
  }
  return import.meta.env.VITE_API_URL || 'http://localhost:8765';
}

function getWsBaseUrl(): string {
  if (import.meta.env.DEV) {
    return `ws://${window.location.hostname}:8765`;
  }
  return import.meta.env.VITE_WS_URL || `ws://${window.location.host}`;
}

function App() {
  // Create the logic instance once
  const logic = useMemo(() => {
    const apiUrl = getApiBaseUrl();
    const wsUrl = getWsBaseUrl();
    console.log('[App] Creating UILogic with API:', apiUrl, 'WS:', wsUrl);
    return new UILogic(apiUrl, wsUrl);
  }, []);

  // Connect to global events WebSocket on mount
  useEffect(() => {
    console.log('[App] Connecting to global events WebSocket...');
    logic.connectGlobalEvents();
    console.log('[App] Global events connection initiated');
    return () => {
      console.log('[App] Cleaning up logic instance');
      logic.cleanup();
    };
  }, [logic]);

  return (
    <LogicProvider logic={logic}>
      <Layout />
    </LogicProvider>
  );
}

export default App;
