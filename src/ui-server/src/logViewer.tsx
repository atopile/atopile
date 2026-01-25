import React from 'react';
import ReactDOM from 'react-dom/client';
import { LogViewer } from './components/LogViewer';
import './index.css';

// LogViewer has its own WebSocket connection to /ws/logs
// It doesn't need AppProvider which connects to /ws/state
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <LogViewer />
  </React.StrictMode>
);
