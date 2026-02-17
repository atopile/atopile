/**
 * Schematic Viewer Entry Point
 *
 * Standalone page that renders hierarchical schematic diagrams.
 * Data is injected via window.__SCHEMATIC_VIEWER_CONFIG__ from the extension webview.
 */

import React from 'react';
import ReactDOM from 'react-dom/client';
import SchematicApp from './schematic-viewer/App';
import { initializeTheme } from './hooks/useTheme';
import './index.css';
import './schematic-viewer/page.css';

// Initialize theme before React renders
initializeTheme();

declare global {
  interface Window {
    __SCHEMATIC_VIEWER_CONFIG__?: {
      dataUrl: string;
    };
  }
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <SchematicApp />
  </React.StrictMode>
);
