import React from "react";
import ReactDOM from "react-dom/client";
import { connectWebview } from "./webviewWebSocketClient";
import "./index.css";

declare global {
  interface Window {
    __ATOPILE_HUB_PORT__: number;
    __ATOPILE_PANEL_ID__: string;
    __ATOPILE_LOGO_URL__: string;
  }
}

export const hubPort = window.__ATOPILE_HUB_PORT__;
export const panelId = window.__ATOPILE_PANEL_ID__;
export const logoUrl = window.__ATOPILE_LOGO_URL__;

export function render(App: React.ComponentType) {
  connectWebview(`ws://localhost:${hubPort}/atopile-ui`);
  ReactDOM.createRoot(document.getElementById("root")!).render(<App />);
}
