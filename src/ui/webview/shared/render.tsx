import React from "react";
import ReactDOM from "react-dom/client";
import { connectWebview } from "./rpcClient";
import "./index.css";

declare global {
  interface Window {
    __ATOPILE_PANEL_ID__: string;
    __ATOPILE_LOGO_URL__: string;
  }
}

export const panelId = window.__ATOPILE_PANEL_ID__;
export const logoUrl = window.__ATOPILE_LOGO_URL__;

export function render(App: React.ComponentType) {
  connectWebview();
  ReactDOM.createRoot(document.getElementById("root")!).render(<App />);
}
