/**
 * WebSocket client for real-time state updates from the Python backend.
 *
 * The backend broadcasts full state on every change. This client connects
 * to the WebSocket endpoint and updates the Zustand store.
 */

import { useStore } from '../store';
import type { AppState } from '../types/build';

// Extended Window type for atopile globals injected by VS Code extension
interface AtopileWindow extends Window {
  __ATOPILE_API_URL__?: string;
  __ATOPILE_WS_URL__?: string;
  __ATOPILE_WORKSPACE_FOLDERS__?: string[];
}

const win = (typeof window !== 'undefined' ? window : {}) as AtopileWindow;

// WebSocket URL - configurable for development or injected by extension
const WS_URL =
  win.__ATOPILE_WS_URL__ ||
  import.meta.env.VITE_WS_URL ||
  'ws://localhost:8501/ws/state';

// Workspace folders - check multiple sources:
// 1. Injected by VS Code extension (production mode)
// 2. URL query param (dev mode with iframe)
// 3. Empty array (standalone browser)
const getWorkspaceFolders = (): string[] => {
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
    console.warn('[WS] Failed to parse workspace folders from URL:', e);
  }

  return [];
};

// Reconnection settings
const RECONNECT_DELAY_MS = 1000;
const MAX_RECONNECT_DELAY_MS = 10000; // Reduced from 30s for faster reconnection
const RECONNECT_BACKOFF_MULTIPLIER = 1.5;
const CONNECTION_TIMEOUT_MS = 5000; // Timeout for connection handshake

// Message types from backend
interface StateMessage {
  type: 'state';
  data: AppState;
}

interface ActionResultMessage {
  type: 'action_result';
  action: string;
  payload?: Record<string, unknown>;  // Original request payload for tracking
  result?: {
    success: boolean;
    error?: string;
    [key: string]: unknown;
  };
  // Legacy direct fields (for backwards compatibility)
  success?: boolean;
  error?: string;
}

type BackendMessage = StateMessage | ActionResultMessage;

// WebSocket connection state
let ws: WebSocket | null = null;
let reconnectAttempts = 0;
let reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
let connectionTimeout: ReturnType<typeof setTimeout> | null = null;
let isIntentionallyClosed = false;
let requestCounter = 0;
const pendingRequests = new Map<string, {
  resolve: (message: ActionResultMessage) => void;
  reject: (error: Error) => void;
  timeoutId: ReturnType<typeof setTimeout>;
}>();

/**
 * Clean up any pending timeouts and close the current WebSocket.
 */
function cleanup(): void {
  if (connectionTimeout) {
    clearTimeout(connectionTimeout);
    connectionTimeout = null;
  }
  if (pendingRequests.size > 0) {
    for (const [requestId, pending] of pendingRequests.entries()) {
      clearTimeout(pending.timeoutId);
      pending.reject(new Error('WebSocket disconnected'));
      pendingRequests.delete(requestId);
    }
  }
  if (ws) {
    // Remove handlers to prevent callbacks during cleanup
    ws.onopen = null;
    ws.onmessage = null;
    ws.onclose = null;
    ws.onerror = null;
    if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
      ws.close();
    }
    ws = null;
  }
}

/**
 * Connect to the backend WebSocket.
 * Automatically reconnects on disconnect.
 */
export function connect(): void {
  if (ws?.readyState === WebSocket.OPEN) {
    console.log('[WS] Already connected');
    return;
  }

  // If stuck in CONNECTING state, clean up and try again
  if (ws?.readyState === WebSocket.CONNECTING) {
    console.log('[WS] Previous connection stuck, cleaning up');
    cleanup();
  }

  isIntentionallyClosed = false;
  console.log(`[WS] Connecting to ${WS_URL}`);

  try {
    ws = new WebSocket(WS_URL);

    ws.onopen = handleOpen;
    ws.onmessage = handleMessage;
    ws.onclose = handleClose;
    ws.onerror = handleError;

    // Set connection timeout - if handshake doesn't complete, force reconnect
    connectionTimeout = setTimeout(() => {
      if (ws?.readyState === WebSocket.CONNECTING) {
        console.warn('[WS] Connection timeout - handshake did not complete');
        cleanup();
        useStore.getState().setConnected(false);
        scheduleReconnect();
      }
    }, CONNECTION_TIMEOUT_MS);
  } catch (error) {
    console.error('[WS] Failed to create WebSocket:', error);
    scheduleReconnect();
  }
}

/**
 * Disconnect from the backend WebSocket.
 */
export function disconnect(): void {
  isIntentionallyClosed = true;

  if (reconnectTimeout) {
    clearTimeout(reconnectTimeout);
    reconnectTimeout = null;
  }

  cleanup();
  useStore.getState().setConnected(false);
  console.log('[WS] Disconnected');
}

/**
 * Send an action to the backend via WebSocket.
 */
export function sendAction(action: string, payload?: Record<string, unknown>): void {
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    console.warn('[WS] Cannot send action - not connected');
    return;
  }

  ws.send(
    JSON.stringify({
      type: 'action',
      action,
      payload: payload || {},
    })
  );
}

/**
 * Send an action and await the corresponding action_result.
 */
export function sendActionWithResponse(
  action: string,
  payload: Record<string, unknown> = {},
  options?: { timeoutMs?: number }
): Promise<ActionResultMessage> {
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    return Promise.reject(new Error('WebSocket not connected'));
  }

  requestCounter += 1;
  const requestId = `${Date.now()}-${requestCounter}`;
  const timeoutMs = options?.timeoutMs ?? 10000;

  return new Promise((resolve, reject) => {
    const timeoutId = setTimeout(() => {
      pendingRequests.delete(requestId);
      reject(new Error(`Action timeout: ${action}`));
    }, timeoutMs);

    pendingRequests.set(requestId, { resolve, reject, timeoutId });
    sendAction(action, { ...payload, requestId });
  });
}

/**
 * Check if WebSocket is connected.
 */
export function isConnected(): boolean {
  return ws?.readyState === WebSocket.OPEN;
}

// --- Internal handlers ---

function handleOpen(): void {
  // Clear connection timeout since we connected successfully
  if (connectionTimeout) {
    clearTimeout(connectionTimeout);
    connectionTimeout = null;
  }
  console.log('[WS] Connected');
  reconnectAttempts = 0;
  useStore.getState().setConnected(true);

  // Send workspace folders to backend if provided by VS Code extension
  const workspaceFolders = getWorkspaceFolders();
  if (workspaceFolders.length > 0) {
    console.log('[WS] Sending workspace folders:', workspaceFolders);
    sendAction('setWorkspaceFolders', { folders: workspaceFolders });
  }
}

function handleMessage(event: MessageEvent): void {
  try {
    const message = JSON.parse(event.data) as BackendMessage;

    switch (message.type) {
      case 'state':
        // Full state replacement from backend
        useStore.getState().replaceState(message.data);
        break;

      case 'action_result':
        // Action response (success/failure)
        // Result is nested in message.result from backend
        const result = message.result || message;
        const requestId = typeof message.payload?.requestId === 'string'
          ? message.payload.requestId
          : null;
        if (requestId && pendingRequests.has(requestId)) {
          const pending = pendingRequests.get(requestId)!;
          clearTimeout(pending.timeoutId);
          pendingRequests.delete(requestId);
          if (result.success) {
            pending.resolve(message);
          } else {
            pending.reject(new Error(String(result.error || 'Action failed')));
          }
        }
        if (!result.success) {
          console.error(`[WS] Action failed: ${message.action}`, result.error);
        }
        if (typeof window !== 'undefined') {
          window.dispatchEvent(
            new CustomEvent('atopile:action_result', { detail: message })
          );
        }
        break;

      default:
        console.warn('[WS] Unknown message type:', message);
    }
  } catch (error) {
    console.error('[WS] Failed to parse message:', error, event.data);
  }
}

function handleClose(event: CloseEvent): void {
  // Clear connection timeout
  if (connectionTimeout) {
    clearTimeout(connectionTimeout);
    connectionTimeout = null;
  }
  console.log(`[WS] Closed: code=${event.code}, reason=${event.reason}`);
  ws = null;
  useStore.getState().setConnected(false);

  if (!isIntentionallyClosed) {
    scheduleReconnect();
  }
}

function handleError(event: Event): void {
  console.error('[WS] Error:', event);
  // Note: The close event usually follows an error event, so reconnection
  // will be handled by handleClose. However, if the WebSocket is still in
  // CONNECTING state after an error (edge case), the connection timeout
  // will handle cleanup and reconnection.
}

function scheduleReconnect(): void {
  if (isIntentionallyClosed) return;

  // Don't schedule if already scheduled
  if (reconnectTimeout) {
    console.log('[WS] Reconnect already scheduled');
    return;
  }

  // Calculate delay with exponential backoff
  const delay = Math.min(
    RECONNECT_DELAY_MS * Math.pow(RECONNECT_BACKOFF_MULTIPLIER, reconnectAttempts),
    MAX_RECONNECT_DELAY_MS
  );

  console.log(`[WS] Reconnecting in ${delay}ms (attempt ${reconnectAttempts + 1})`);

  reconnectTimeout = setTimeout(() => {
    reconnectTimeout = null; // Clear before calling connect
    reconnectAttempts++;
    connect();
  }, delay);
}

// --- React hook for connection lifecycle ---

/**
 * React hook to manage WebSocket connection lifecycle.
 * Call this once at the app root level.
 */
export function useWebSocketConnection(): void {
  // Connect on mount, disconnect on unmount
  // This uses a custom hook pattern that works with React's lifecycle
  if (typeof window !== 'undefined') {
    // Only run in browser
    const { useEffect } = require('react');

    useEffect(() => {
      connect();
      return () => disconnect();
    }, []);
  }
}

// Export for use in components
export default {
  connect,
  disconnect,
  sendAction,
  isConnected,
};
