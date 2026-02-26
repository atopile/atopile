import React from "react";
import ReactDOM from "react-dom/client";
import { connect } from "./webSocketProvider";
import "./index.css";

declare global {
  interface Window {
    __ATOPILE_HUB_URL__: string;
    __ATOPILE_PANEL_ID__: string;
    __ATOPILE_LOGO_URL__: string;
  }
}

const hubUrl = window.__ATOPILE_HUB_URL__;
export const panelId = window.__ATOPILE_PANEL_ID__;
export const logoUrl = window.__ATOPILE_LOGO_URL__;

export function render(App: React.ComponentType) {
  connect(hubUrl);
  ReactDOM.createRoot(document.getElementById("root")!).render(<App />);
}
