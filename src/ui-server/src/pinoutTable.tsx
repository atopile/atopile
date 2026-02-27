import React from 'react';
import ReactDOM from 'react-dom/client';
import type { Root } from 'react-dom/client';
import { PinoutPanel } from './components/PinoutPanel';
import { AppProvider } from './AppProvider';
import './index.css';

const rootElement = document.getElementById('root');
if (rootElement) {
  const existingRoot = (window as Window & { __ATOPILE_ROOT_PINOUT__?: Root })
    .__ATOPILE_ROOT_PINOUT__;
  const root = existingRoot ?? ReactDOM.createRoot(rootElement);
  (window as Window & { __ATOPILE_ROOT_PINOUT__?: Root }).__ATOPILE_ROOT_PINOUT__ = root;
  root.render(
    <React.StrictMode>
      <AppProvider>
        <PinoutPanel />
      </AppProvider>
    </React.StrictMode>
  );
}
