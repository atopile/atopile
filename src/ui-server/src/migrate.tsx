import React from 'react';
import ReactDOM from 'react-dom/client';
import { AppProvider } from './AppProvider';
import { MigratePage } from './components/MigratePage';
import { initializeTheme } from './hooks/useTheme';
import './index.css';

// Initialize theme before React renders (handles VS Code webview theming)
initializeTheme();

// Read projectRoot from URL query param (dev) or injected global (prod)
function getProjectRoot(): string {
  if (typeof window !== 'undefined') {
    // Dev mode: passed as query param on the iframe src
    const params = new URLSearchParams(window.location.search);
    const fromParam = params.get('projectRoot');
    if (fromParam) return fromParam;

    // Prod mode: injected by the extension in a <script> tag
    const fromGlobal = (window as Window & { __ATOPILE_MIGRATE_PROJECT__?: string }).__ATOPILE_MIGRATE_PROJECT__;
    if (fromGlobal) return fromGlobal;
  }
  return '';
}

const projectRoot = getProjectRoot();

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <AppProvider>
      <MigratePage projectRoot={projectRoot} />
    </AppProvider>
  </React.StrictMode>
);
