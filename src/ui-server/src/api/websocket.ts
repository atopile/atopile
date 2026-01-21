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
const MAX_RECONNECT_DELAY_MS = 30000;
const RECONNECT_BACKOFF_MULTIPLIER = 1.5;

// Message types from backend
interface StateMessage {
  type: 'state';
  data: AppState;
}

interface ActionResultMessage {
  type: 'action_result';
  action: string;
  success: boolean;
  error?: string;
}

type BackendMessage = StateMessage | ActionResultMessage;

// WebSocket connection state
let ws: WebSocket | null = null;
let reconnectAttempts = 0;
let reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
let isIntentionallyClosed = false;

/**
 * Connect to the backend WebSocket.
 * Automatically reconnects on disconnect.
 */
export function connect(): void {
  if (ws?.readyState === WebSocket.OPEN) {
    console.log('[WS] Already connected');
    return;
  }

  if (ws?.readyState === WebSocket.CONNECTING) {
    console.log('[WS] Connection in progress');
    return;
  }

  isIntentionallyClosed = false;
  console.log(`[WS] Connecting to ${WS_URL}`);

  try {
    ws = new WebSocket(WS_URL);

    ws.onopen = handleOpen;
    ws.onmessage = handleMessage;
    ws.onclose = handleClose;
    ws.onerror = handleError;
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

  if (ws) {
    ws.close();
    ws = null;
  }

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
        if (!message.success) {
          console.error(`[WS] Action failed: ${message.action}`, message.error);
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
  console.log(`[WS] Closed: code=${event.code}, reason=${event.reason}`);
  ws = null;
  useStore.getState().setConnected(false);

  if (!isIntentionallyClosed) {
    scheduleReconnect();
  }
}

function handleError(event: Event): void {
  console.error('[WS] Error:', event);
}

function scheduleReconnect(): void {
  if (isIntentionallyClosed) return;

  // Calculate delay with exponential backoff
  const delay = Math.min(
    RECONNECT_DELAY_MS * Math.pow(RECONNECT_BACKOFF_MULTIPLIER, reconnectAttempts),
    MAX_RECONNECT_DELAY_MS
  );

  console.log(`[WS] Reconnecting in ${delay}ms (attempt ${reconnectAttempts + 1})`);

  reconnectTimeout = setTimeout(() => {
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
