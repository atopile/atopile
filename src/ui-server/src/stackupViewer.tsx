import React from 'react';
import ReactDOM from 'react-dom/client';
import { StackupViewer } from './components/StackupViewer/StackupViewer';
import { initializeTheme } from './hooks/useTheme';
import './index.css';

initializeTheme();

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <StackupViewer />
  </React.StrictMode>
);
