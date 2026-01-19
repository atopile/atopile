import React from 'react';
import ReactDOM from 'react-dom/client';
import { LogViewer } from './components/LogViewer';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <LogViewer />
  </React.StrictMode>
);
