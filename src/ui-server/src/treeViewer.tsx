/**
 * Tree Viewer Entry Point
 *
 * Standalone page that renders power tree and I2C tree diagrams.
 * Data is injected via window.__TREE_VIEWER_CONFIG__ from the extension webview.
 */

import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './tree-viewer/App';
import './tree-viewer/index.css';

declare global {
  interface Window {
    __TREE_VIEWER_CONFIG__?: {
      type: string;
      dataUrl: string;
    };
  }
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
