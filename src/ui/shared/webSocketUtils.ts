/**
 * WebSocket utilities shared between hub and webview.
 *
 * Provides reconnection scheduling, message-type constants,
 * safe parse/send helpers, and typed message builders.
 */

import { MSG_TYPE, type WebSocketMessage } from "./types";


// -- Reconnection -------------------------------------------------------------

export class ReconnectScheduler {
  private _delay: number;
  private _initialDelay: number;
  private _maxDelay: number;
  private _timer: ReturnType<typeof setTimeout> | null = null;
  private _stopped = true;

  constructor(initialDelay = 1000, maxDelay = 10000) {
    this._initialDelay = initialDelay;
    this._delay = initialDelay;
    this._maxDelay = maxDelay;
  }

  get stopped(): boolean {
    return this._stopped;
  }

  /** Reset delay to initial value (call on successful connection). */
  resetDelay(): void {
    this._delay = this._initialDelay;
  }

  /** Schedule a reconnection attempt. No-op if stopped. */
  schedule(fn: () => void): void {
    if (this._stopped) return;
    this._timer = setTimeout(() => {
      this._timer = null;
      fn();
    }, this._delay);
    this._delay = Math.min(this._delay * 2, this._maxDelay);
  }

  /** Mark as active (allows scheduling). */
  start(): void {
    this._stopped = false;
  }

  /** Cancel any pending reconnect and mark as stopped. */
  stop(): void {
    this._stopped = true;
    if (this._timer) {
      clearTimeout(this._timer);
      this._timer = null;
    }
  }
}

type WS = { readyState: number; send(data: string): void } | null | undefined;

// -- Parse / send helpers -----------------------------------------------------

/**
 * Parse a raw WebSocket message into a typed WebSocketMessage.
 * Returns null if the data isn't valid JSON or has an unknown type.
 */
export function parseMessage(data: unknown): WebSocketMessage | null {
  try {
    const str = typeof data === "string" ? data : String(data);
    const msg = JSON.parse(str);
    if (msg?.type === MSG_TYPE.SUBSCRIBE || msg?.type === MSG_TYPE.STATE || msg?.type === MSG_TYPE.ACTION) {
      return msg as WebSocketMessage;
    }
    return null;
  } catch {
    return null;
  }
}

/**
 * Send a JSON-serialized message over a WebSocket.
 * Returns false if the socket isn't open or the send threw.
 */
function sendJSON(
  ws: WS,
  msg: unknown,
): boolean {
  try {
    if (!ws || ws.readyState !== 1) return false;
    ws.send(JSON.stringify(msg));
    return true;
  } catch {
    return false;
  }
}

// -- Send helpers -------------------------------------------------------------

export function sendSubscribe(ws: WS, keys: string[]): boolean {
  return sendJSON(ws, { type: MSG_TYPE.SUBSCRIBE, keys });
}

export function sendState(ws: WS, key: string, data: unknown): boolean {
  return sendJSON(ws, { type: MSG_TYPE.STATE, key, data });
}

export function sendAction(ws: WS, action: string, payload?: Record<string, unknown>): boolean {
  return sendJSON(ws, { type: MSG_TYPE.ACTION, action, ...payload });
}

