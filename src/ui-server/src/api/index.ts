/**
 * API module exports.
 */

export { api, APIError } from './client';
export {
  connect,
  disconnect,
  sendAction,
  isConnected,
} from './websocket';
