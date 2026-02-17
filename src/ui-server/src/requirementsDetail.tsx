import React from 'react';
import ReactDOM from 'react-dom/client';
import { RequirementsDetailPage } from './components/RequirementsDetailPage';
import { initializeTheme } from './hooks/useTheme';
import './styles/index.css';

initializeTheme();

function getRequirementId(): string {
  if (typeof window !== 'undefined') {
    const params = new URLSearchParams(window.location.search);
    const fromParam = params.get('requirementId');
    if (fromParam) return fromParam;

    const fromGlobal = (window as Window & { __ATOPILE_REQUIREMENT_ID__?: string }).__ATOPILE_REQUIREMENT_ID__;
    if (fromGlobal) return fromGlobal;
  }
  return '';
}

const requirementId = getRequirementId();

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <RequirementsDetailPage requirementId={requirementId} />
  </React.StrictMode>
);
