import React from 'react';
import ReactDOM from 'react-dom/client';
import { AppProvider } from './AppProvider';
import { LogViewer } from './components/LogViewer';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <AppProvider>
      <LogViewer />
    </AppProvider>
  </React.StrictMode>
);
