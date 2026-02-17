import React from 'react';
import ReactDOM from 'react-dom/client';
import { AppProvider } from './AppProvider';
import { ManufacturingDashboard } from './components/manufacturing/dashboard';
import { initializeTheme } from './hooks/useTheme';
import './index.css';

// Initialize theme before React renders (handles VS Code webview theming)
initializeTheme();

// Read projectRoot and target from URL query params (dev) or injected globals (prod)
function getProjectRoot(): string {
  if (typeof window !== 'undefined') {
    const params = new URLSearchParams(window.location.search);
    const fromParam = params.get('projectRoot');
    if (fromParam) return fromParam;

    const fromGlobal = (window as Window & { __ATOPILE_DASHBOARD_PROJECT__?: string }).__ATOPILE_DASHBOARD_PROJECT__;
    if (fromGlobal) return fromGlobal;
  }
  return '';
}

function getTargetName(): string {
  if (typeof window !== 'undefined') {
    const params = new URLSearchParams(window.location.search);
    const fromParam = params.get('target');
    if (fromParam) return fromParam;

    const fromGlobal = (window as Window & { __ATOPILE_DASHBOARD_TARGET__?: string }).__ATOPILE_DASHBOARD_TARGET__;
    if (fromGlobal) return fromGlobal;
  }
  return '';
}

const projectRoot = getProjectRoot();
const targetName = getTargetName();

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <AppProvider>
      <ManufacturingDashboard projectRoot={projectRoot} targetName={targetName} />
    </AppProvider>
  </React.StrictMode>
);
