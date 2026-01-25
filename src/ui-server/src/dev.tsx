/**
 * Dev mode entry point.
 * Renders Sidebar + LogViewer in a single page using the backend WS directly.
 */

import React from 'react';
import ReactDOM from 'react-dom/client';
import { AppProvider } from './AppProvider';
import { Sidebar } from './components/Sidebar';
import { LogViewer } from './components/LogViewer';
import { initializeTheme } from './hooks/useTheme';
import { WS_STATE_URL } from './api/config';
import './index.css';

// Initialize theme before React renders
initializeTheme();

function DevLayout() {
  return (
    <>
      <div className="dev-banner">Dev Mode - {WS_STATE_URL}</div>
      <div className="main-content">
        <div className="panel sidebar-panel">
          <Sidebar />
        </div>
        <div className="panel log-panel">
          <LogViewer />
        </div>
      </div>
    </>
  );
}

const root = document.getElementById('root');
if (root) {
  ReactDOM.createRoot(root).render(
    <React.StrictMode>
      <AppProvider>
        <DevLayout />
      </AppProvider>
    </React.StrictMode>
  );
}
