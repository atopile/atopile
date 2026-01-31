/**
 * Centralized backend URL configuration.
 */

// Extended Window type for atopile globals injected by VS Code extension
interface AtopileWindow extends Window {
  __ATOPILE_API_URL__?: string;
  __ATOPILE_WS_URL__?: string;
  __ATOPILE_WORKSPACE_FOLDERS__?: string[];
}

const win = (typeof window !== 'undefined' ? window : {}) as AtopileWindow;

/**
 * Derive WebSocket URL from HTTP URL.
 * e.g., http://127.0.0.1:12345 -> ws://127.0.0.1:12345
 */
function httpToWsUrl(httpUrl: string): string {
  try {
    const url = new URL(httpUrl);
    const wsProtocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
    const port = url.port ? `:${url.port}` : '';
    return `${wsProtocol}//${url.hostname}${port}`;
  } catch {
    // Fallback if URL parsing fails
    return httpUrl.replace(/^http/, 'ws');
  }
}

/**
 * Get the base backend API URL (HTTP).
 * e.g., http://127.0.0.1:12345
 */
export const API_URL = win.__ATOPILE_API_URL__ || import.meta.env.VITE_API_URL;
if (!API_URL) {
  throw new Error(
    'Backend API URL not configured. Use the extension webview or run `ato serve frontend` to set VITE_API_URL.'
  );
}

/**
 * Get the base WebSocket URL (without path).
 * e.g., ws://127.0.0.1:12345
 */
const WS_BASE_URL = win.__ATOPILE_WS_URL__
  ? new URL(win.__ATOPILE_WS_URL__).origin.replace(/^http/, 'ws')
  : (import.meta.env.VITE_WS_URL
      ? new URL(import.meta.env.VITE_WS_URL).origin.replace(/^http/, 'ws')
      : httpToWsUrl(API_URL));

/**
 * WebSocket URL for state updates (/ws/state).
 * Used by the main app state manager.
 */
export const WS_STATE_URL = `${WS_BASE_URL}/ws/state`;

/**
 * WebSocket URL for log streaming (/ws/logs).
 * Used by the LogViewer component.
 */
export const WS_LOGS_URL = `${WS_BASE_URL}/ws/logs`;

/**
 * Get workspace folders from injected globals or URL query params.
 */
export function getWorkspaceFolders(): string[] {
  if (typeof window === 'undefined') return [];

  // Check window variable first (production VS Code)
  if (win.__ATOPILE_WORKSPACE_FOLDERS__) {
    return win.__ATOPILE_WORKSPACE_FOLDERS__;
  }

  // Check URL query param (dev mode iframe)
  try {
    const params = new URLSearchParams(window.location.search);
    const workspaceParam = params.get('workspace');
    if (workspaceParam) {
      const folders = JSON.parse(decodeURIComponent(workspaceParam));
      if (Array.isArray(folders)) {
        return folders;
      }
    }
  } catch (e) {
    console.warn('[Config] Failed to parse workspace folders from URL:', e);
  }

  return [];
}
