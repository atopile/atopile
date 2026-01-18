import { useMemo, useEffect } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Layout } from '@/components';
import { Dashboard, Pipelines } from '@/pages';
import { UILogic } from '@/logic';
import { LogicProvider } from '@/hooks';

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
    return new UILogic(getApiBaseUrl(), getWsBaseUrl());
  }, []);

  // Connect to global events WebSocket on mount
  useEffect(() => {
    logic.connectGlobalEvents();
    return () => {
      logic.cleanup();
    };
  }, [logic]);

  return (
    <LogicProvider logic={logic}>
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/pipelines" element={<Pipelines />} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </LogicProvider>
  );
}

export default App;
