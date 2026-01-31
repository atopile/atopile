import React from 'react';
import ReactDOM from 'react-dom/client';
import { LogViewer } from './components/LogViewer';
import { AppProvider } from './AppProvider';
import { initializeTheme } from './hooks/useTheme';
import './index.css';

// Initialize theme before React renders (handles VS Code webview theming)
initializeTheme();

// AppProvider connects to /ws/state so the LogViewer shares
// the same builds data and logViewerBuildId as the sidebar.
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <AppProvider>
      <LogViewer />
    </AppProvider>
  </React.StrictMode>
);
