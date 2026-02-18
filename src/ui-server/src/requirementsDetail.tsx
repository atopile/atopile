import React from 'react';
import ReactDOM from 'react-dom/client';
import { RequirementsDetailPage } from './components/RequirementsDetailPage';
import { initializeTheme } from './hooks/useTheme';
import { preloadPlotly } from './components/requirements/charts';
import type { RequirementData } from './components/requirements/types';
import './styles/index.css';

// Start loading Plotly immediately — runs in parallel with React mount
preloadPlotly();

initializeTheme();

type WindowGlobals = Window & {
  __ATOPILE_REQUIREMENT_ID__?: string;
  __ATOPILE_REQUIREMENT_DATA__?: RequirementData;
  __ATOPILE_BUILD_TIME__?: string;
  __ATOPILE_API_URL__?: string;
  __ATOPILE_PROJECT_ROOT__?: string;
  __ATOPILE_TARGET__?: string;
};

const w = window as WindowGlobals;

function getRequirementId(): string {
  const params = new URLSearchParams(window.location.search);
  const fromParam = params.get('requirementId');
  if (fromParam) return fromParam;
  return w.__ATOPILE_REQUIREMENT_ID__ ?? '';
}

const requirementId = getRequirementId();

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <RequirementsDetailPage
      requirementId={requirementId}
      injectedData={w.__ATOPILE_REQUIREMENT_DATA__ ?? null}
      injectedBuildTime={w.__ATOPILE_BUILD_TIME__ ?? ''}
    />
  </React.StrictMode>
);
