import React from 'react';
import ReactDOM from 'react-dom/client';
import { Sidebar } from './components/Sidebar';
import { AppProvider } from './AppProvider';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <AppProvider>
      <Sidebar />
    </AppProvider>
  </React.StrictMode>
);
