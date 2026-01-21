import React from 'react';
import ReactDOM from 'react-dom/client';
import { LogViewer } from './components/LogViewer';
import { AppProvider } from './AppProvider';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <AppProvider>
      <LogViewer />
    </AppProvider>
  </React.StrictMode>
);
