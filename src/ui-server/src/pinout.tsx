/**
 * Pinout Viewer Entry Point
 *
 * Standalone page that renders IC pinout diagrams.
 * Data is injected via window.__PINOUT_CONFIG__ from the extension webview.
 */

import React, { useState, useEffect } from 'react';
import ReactDOM from 'react-dom/client';
import { PinoutViewer } from './components/PinoutViewer';
import { initializeTheme } from './hooks/useTheme';
import './index.css';

// Initialize theme before React renders
initializeTheme();

interface PinoutConfig {
  dataUrl: string;
}

declare global {
  interface Window {
    __PINOUT_CONFIG__?: PinoutConfig;
  }
}

function PinoutApp() {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const config = window.__PINOUT_CONFIG__;
    let dataUrl = config?.dataUrl;

    // Dev mode: load from URL query param or default test file
    if (!dataUrl) {
      const params = new URLSearchParams(window.location.search);
      dataUrl = params.get('dataUrl') || undefined;
    }

    if (!dataUrl) {
      setError('No pinout data URL. In dev mode, use ?dataUrl=path/to/pinout.json');
      return;
    }

    fetch(dataUrl)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((json) => {
        if (!json.components || json.components.length === 0) {
          setError('No components with 5+ pins found. Build your project first.');
        } else {
          setData(json);
        }
      })
      .catch((err) => setError(`Failed to load pinout data: ${err.message}`));
  }, []);

  if (error) {
    return (
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        height: '100vh', color: 'var(--vscode-descriptionForeground, #888)',
        fontFamily: 'var(--vscode-font-family, system-ui)',
        fontSize: 13, padding: 24, textAlign: 'center',
      }}>
        {error}
      </div>
    );
  }

  if (!data) {
    return (
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        height: '100vh', color: 'var(--vscode-descriptionForeground, #888)',
        fontFamily: 'var(--vscode-font-family, system-ui)', fontSize: 13,
      }}>
        Loading...
      </div>
    );
  }

  return <PinoutViewer data={data} />;
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <PinoutApp />
  </React.StrictMode>
);
