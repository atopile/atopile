// @ts-nocheck
import 'globalthis/polyfill';

window.global = window;
import React from 'react';
import ReactDOM from 'react-dom/client';

import App from './SchematicApp';

import './index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
