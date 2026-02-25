import React from "react";
import ReactDOM from "react-dom/client";
import "./index.css";

declare global {
  interface Window {
    __ATOPILE_HUB_URL__: string;
    __ATOPILE_PANEL_ID__: string;
    __ATOPILE_LOGO_URL__: string;
  }
}

export const hubUrl = window.__ATOPILE_HUB_URL__;
export const panelId = window.__ATOPILE_PANEL_ID__;
export const logoUrl = window.__ATOPILE_LOGO_URL__;

export interface AppProps {
  hubUrl: string;
  panelId: string;
  logoUrl: string;
}

export function render(App: React.ComponentType<AppProps>) {
  ReactDOM.createRoot(document.getElementById("root")!).render(
    <App hubUrl={hubUrl} panelId={panelId} logoUrl={logoUrl} />
  );
}
