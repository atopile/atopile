import React from 'react';
import ReactDOM from 'react-dom/client';
import { Sidebar } from './components/Sidebar';
import { AppProvider } from './AppProvider';
import { initializeTheme } from './hooks/useTheme';
import './index.css';

// Initialize theme before React renders to prevent flash
initializeTheme();

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <AppProvider>
      <Sidebar />
    </AppProvider>
  </React.StrictMode>
);
