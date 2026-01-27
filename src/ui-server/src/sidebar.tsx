import React from 'react';
import ReactDOM from 'react-dom/client';
import type { Root } from 'react-dom/client';
import { Sidebar } from './components/Sidebar';
import { AppProvider } from './AppProvider';
import { initializeTheme } from './hooks/useTheme';
import './index.css';

// Initialize theme before React renders to prevent flash
initializeTheme();

const rootElement = document.getElementById('root');
if (rootElement) {
  const existingRoot = (window as Window & { __ATOPILE_ROOT_SIDEBAR__?: Root })
    .__ATOPILE_ROOT_SIDEBAR__;
  const root = existingRoot ?? ReactDOM.createRoot(rootElement);
  (window as Window & { __ATOPILE_ROOT_SIDEBAR__?: Root }).__ATOPILE_ROOT_SIDEBAR__ = root;
  root.render(
  <React.StrictMode>
    <AppProvider>
      <Sidebar />
    </AppProvider>
  </React.StrictMode>
);
}
