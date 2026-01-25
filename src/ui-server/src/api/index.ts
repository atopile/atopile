/**
 * API module exports and centralized backend URL configuration.
 */

export {
  API_URL,
  WS_STATE_URL,
  WS_LOGS_URL,
  getWorkspaceFolders,
} from './config';

// ============================================================================
// API Exports
// ============================================================================

export { api, APIError } from './client';
export {
  connect,
  disconnect,
  sendAction,
  isConnected,
} from './websocket';
