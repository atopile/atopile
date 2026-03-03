import React from 'react';
import ReactDOM from 'react-dom/client';
import type { Root } from 'react-dom/client';
import { InteractiveBomApp } from './components/interactive-bom/InteractiveBomApp';
import { initializeTheme } from './hooks/useTheme';
import './styles.css';

initializeTheme();

const rootElement = document.getElementById('root');
if (rootElement) {
  const existingRoot = (window as Window & { __ATOPILE_ROOT_IBOM__?: Root })
    .__ATOPILE_ROOT_IBOM__;
  const root = existingRoot ?? ReactDOM.createRoot(rootElement);
  (window as Window & { __ATOPILE_ROOT_IBOM__?: Root }).__ATOPILE_ROOT_IBOM__ = root;
  root.render(
    <React.StrictMode>
      <InteractiveBomApp />
    </React.StrictMode>
  );
}
