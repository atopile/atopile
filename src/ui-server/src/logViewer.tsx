import React from 'react';
import ReactDOM from 'react-dom/client';
import type { Root } from 'react-dom/client';
import { LogViewer } from './components/LogViewer';
import './index.css';

// LogViewer has its own WebSocket connection to /ws/logs
// It doesn't need AppProvider which connects to /ws/state
const rootElement = document.getElementById('root');
if (rootElement) {
  const existingRoot = (window as Window & { __ATOPILE_ROOT_LOGVIEWER__?: Root })
    .__ATOPILE_ROOT_LOGVIEWER__;
  const root = existingRoot ?? ReactDOM.createRoot(rootElement);
  (window as Window & { __ATOPILE_ROOT_LOGVIEWER__?: Root }).__ATOPILE_ROOT_LOGVIEWER__ = root;
  root.render(
    <React.StrictMode>
      <LogViewer />
    </React.StrictMode>
  );
}
