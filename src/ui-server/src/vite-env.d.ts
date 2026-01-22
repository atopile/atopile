/// <reference types="vite/client" />

// Global variables injected by VS Code extension
declare global {
  interface Window {
    __ATOPILE_API_URL__?: string;
    __ATOPILE_WS_URL__?: string;
    __ATOPILE_WORKSPACE_FOLDERS__?: string[];
  }
}

export {};
