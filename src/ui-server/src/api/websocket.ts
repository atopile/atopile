/**
 * WebSocket client for real-time state updates from the Python backend.
 *
 * The backend broadcasts full state on every change. This client connects
 * to the WebSocket endpoint and updates the Zustand store.
 */

import { useStore } from '../store';
import type { AppState } from '../types/build';
import { api } from './client';
import { WS_STATE_URL, getWorkspaceFolders } from './config';
import { postMessage } from './vscodeApi';

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

interface EventMessage {
  type: 'event';
  event: string;
  data?: Record<string, unknown>;
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

type BackendMessage = StateMessage | ActionResultMessage | EventMessage;

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
  console.log(`[WS] Connecting to ${WS_STATE_URL}`);

  try {
    ws = new WebSocket(WS_STATE_URL);

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

  // Notify VS Code extension of connection status
  postMessage({ type: 'connectionStatus', isConnected: true });

  // Send workspace folders to backend if provided by VS Code extension
  const workspaceFolders = getWorkspaceFolders();
  if (workspaceFolders.length > 0) {
    console.log('[WS] Sending workspace folders:', workspaceFolders);
    sendAction('setWorkspaceFolders', { folders: workspaceFolders });
  }

  void refreshProjects();
}

function handleMessage(event: MessageEvent): void {
  try {
    const message = JSON.parse(event.data) as BackendMessage;

    switch (message.type) {
      case 'state':
        // Full state replacement from backend
        // Note: Backend's to_frontend_dict() converts all keys to camelCase
        {
          const state = message.data as AppState;

          // Extract one-shot open signals before replacing state
          const { openFile, openFileLine, openFileColumn, openLayout, openKicad, open3D, ...stateWithoutSignals } = state;

          // Update store with state (excluding one-shot signals)
          useStore.getState().replaceState(stateWithoutSignals);

          // Forward open signals to VS Code extension (one-shot actions)
          if (openFile || openLayout || openKicad || open3D) {
            postMessage({
              type: 'openSignals',
              openFile: openFile ?? null,
              openFileLine: openFileLine ?? null,
              openFileColumn: openFileColumn ?? null,
              openLayout: openLayout ?? null,
              openKicad: openKicad ?? null,
              open3d: open3D ?? null,
            });
          }

          // Forward atopile settings changes to VS Code extension
          if (state.atopile) {
            postMessage({
              type: 'atopileSettings',
              atopile: {
                source: state.atopile.source,
                currentVersion: state.atopile.currentVersion,
                branch: state.atopile.branch,
                localPath: state.atopile.localPath,
              },
            });
          }
        }
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
      case 'event':
        handleEventMessage(message);
        break;

      default:
        console.warn('[WS] Unknown message type:', message);
    }
  } catch (error) {
    console.error('[WS] Failed to parse message:', error, event.data);
  }
}

async function refreshProjects(): Promise<void> {
  try {
    const response = await api.projects.list();
    useStore.getState().setProjects(response.projects || []);
  } catch (error) {
    console.warn('[WS] Failed to refresh projects:', error);
  }
}

function getSelectedTargetName(): string | null {
  const state = useStore.getState();
  if (!state.selectedProjectRoot) return null;
  if (state.selectedTargetNames?.length) return state.selectedTargetNames[0] ?? null;
  const project = state.projects.find((p) => p.root === state.selectedProjectRoot);
  return project?.targets?.[0]?.name ?? null;
}

async function refreshDependencies(projectRoot?: string | null): Promise<void> {
  const root = projectRoot || useStore.getState().selectedProjectRoot;
  if (!root) return;
  try {
    const response = await api.dependencies.list(root);
    useStore.getState().setProjectDependencies(root, response.dependencies || []);
  } catch (error) {
    console.warn('[WS] Failed to refresh dependencies:', error);
  }
}

async function refreshBom(): Promise<void> {
  const state = useStore.getState();
  if (!state.selectedProjectRoot) return;
  const targetName = getSelectedTargetName();
  if (!targetName) return;
  try {
    state.setLoadingBom(true);
    const response = await api.bom.get(state.selectedProjectRoot, targetName);
    state.setBomData(response || null);
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Failed to fetch BOM';
    state.setBomError(message);
  }
}

async function refreshVariables(): Promise<void> {
  const state = useStore.getState();
  if (!state.selectedProjectRoot) return;
  const targetName = getSelectedTargetName();
  if (!targetName) return;
  try {
    state.setLoadingVariables(true);
    const response = await api.variables.get(state.selectedProjectRoot, targetName);
    state.setVariablesData(response || null);
  } catch (error) {
    const message =
      error instanceof Error ? error.message : 'Failed to fetch variables';
    state.setVariablesError(message);
  }
}

async function refreshPackages(): Promise<void> {
  const state = useStore.getState();
  try {
    state.setLoadingPackages(true);
    const response = await api.packages.list();
    state.setPackages(response.packages || []);
  } catch (error) {
    console.warn('[WS] Failed to refresh packages:', error);
    state.setPackages([]);
  }
}

async function refreshStdlib(): Promise<void> {
  const state = useStore.getState();
  try {
    state.setLoadingStdlib(true);
    const response = await api.stdlib.list();
    state.setStdlibItems(response.items || []);
  } catch (error) {
    console.warn('[WS] Failed to refresh stdlib:', error);
    state.setStdlibItems([]);
  }
}

async function refreshProblems(): Promise<void> {
  const state = useStore.getState();
  try {
    state.setLoadingProblems(true);
    const response = await api.problems.list();
    state.setProblems(response.problems || []);
  } catch (error) {
    console.warn('[WS] Failed to refresh problems:', error);
    state.setProblems([]);
  }
}

function handleEventMessage(message: EventMessage): void {
  const data = message.data ?? {};
  const projectRoot =
    (typeof data.projectRoot === 'string' && data.projectRoot) ||
    (typeof data.project_root === 'string' && data.project_root) ||
    null;

  switch (message.event) {
    case 'projects_changed':
      void refreshProjects();
      break;
    case 'project_dependencies_changed':
      void refreshDependencies(projectRoot);
      break;
    case 'bom_changed':
      void refreshBom();
      break;
    case 'variables_changed':
      void refreshVariables();
      break;
    case 'packages_changed':
      void refreshPackages();
      break;
    case 'stdlib_changed':
      void refreshStdlib();
      break;
    case 'problems_changed':
      void refreshProblems();
      break;
    default:
      break;
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

  // Notify VS Code extension of connection status
  postMessage({ type: 'connectionStatus', isConnected: false });

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

// Export for use in components
export default {
  connect,
  disconnect,
  sendAction,
  isConnected,
};
