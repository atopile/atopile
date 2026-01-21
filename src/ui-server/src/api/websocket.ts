/**
 * WebSocket client for real-time state updates from the Python backend.
 *
 * The backend broadcasts full state on every change. This client connects
 * to the WebSocket endpoint and updates the Zustand store.
 */

import { useStore } from '../store';
import type { AppState } from '../types/build';

// WebSocket URL - configurable for development or injected by extension
const WS_URL =
  (typeof window !== 'undefined' && window.__ATOPILE_WS_URL__) ||
  import.meta.env.VITE_WS_URL ||
  'ws://localhost:8501/ws/state';

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

/**
 * Clean up any pending timeouts and close the current WebSocket.
 */
function cleanup(): void {
  if (connectionTimeout) {
    clearTimeout(connectionTimeout);
    connectionTimeout = null;
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
