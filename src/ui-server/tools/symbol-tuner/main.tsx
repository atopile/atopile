import React from 'react';
import ReactDOM from 'react-dom/client';
import { SymbolTunerApp } from './SymbolTunerApp';
import './symbol-tuner.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <SymbolTunerApp />
  </React.StrictMode>,
);

