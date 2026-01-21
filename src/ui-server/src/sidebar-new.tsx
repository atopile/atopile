/**
 * Sidebar entry point - NEW ARCHITECTURE
 *
 * This entry point uses:
 * - Zustand store for state management
 * - Direct WebSocket connection to Python backend
 * - No VS Code postMessage - UI owns its state
 *
 * The existing components (Sidebar, ProjectsPanel, etc.) will continue to work
 * as we migrate them to use the new hooks instead of props.
 */

import React from 'react';
import ReactDOM from 'react-dom/client';
import { AppProvider } from './AppProvider';
import { SidebarNew } from './components/SidebarNew';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <AppProvider>
      <SidebarNew />
    </AppProvider>
  </React.StrictMode>
);
