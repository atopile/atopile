/**
 * Environment-agnostic WebSocket client with reconnection,
 * subscription tracking, and typed message routing.
 *
 * Takes a socket factory so it never imports `ws` or browser `WebSocket`
 * directly — callers provide `() => new WebSocket(url)`.
 *
 * Also exports low-level parse/send helpers used by the WebviewWebSocketServer.
 */

import { MSG_TYPE, type WebSocketMessage } from "./types";

// -- SocketLike ---------------------------------------------------------------

/** Minimal interface satisfied by both browser WebSocket and Node `ws`. */
export interface SocketLike {
  readyState: number;
  send(data: string): void;
  close(): void;
  onopen: ((ev: any) => void) | null;
  onmessage: ((ev: { data: any }) => void) | null;
  onclose: ((ev: any) => void) | null;
  onerror: ((ev: any) => void) | null;
}

// -- Reconnection -------------------------------------------------------------

class ReconnectScheduler {
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

  resetDelay(): void {
    this._delay = this._initialDelay;
  }

  schedule(fn: () => void): void {
    if (this._stopped) return;
    this._timer = setTimeout(() => {
      this._timer = null;
      fn();
    }, this._delay);
    this._delay = Math.min(this._delay * 2, this._maxDelay);
  }

  start(): void {
    this._stopped = false;
  }

  stop(): void {
    this._stopped = true;
    if (this._timer) {
      clearTimeout(this._timer);
      this._timer = null;
    }
  }
}

// -- Parse / send helpers -----------------------------------------------------

type WS = { readyState: number; send(data: string): void } | null | undefined;

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

function sendJSON(ws: WS, msg: unknown): boolean {
  try {
    if (!ws || ws.readyState !== 1) return false;
    ws.send(JSON.stringify(msg));
    return true;
  } catch {
    return false;
  }
}

function sendSubscribe(ws: WS, keys: string[]): boolean {
  return sendJSON(ws, { type: MSG_TYPE.SUBSCRIBE, keys });
}

export function sendState(ws: WS, key: string, data: unknown): boolean {
  return sendJSON(ws, { type: MSG_TYPE.STATE, key, data });
}

function sendActionRaw(ws: WS, action: string, payload?: Record<string, unknown>): boolean {
  return sendJSON(ws, { type: MSG_TYPE.ACTION, action, ...payload });
}

// -- Options ------------------------------------------------------------------

export interface WebSocketClientOptions {
  /** Whether to automatically reconnect on close (default true). */
  reconnect?: boolean;
}

// -- WebSocketClient ----------------------------------------------------------

export class WebSocketClient {
  private _create: () => SocketLike;
  private _socket: SocketLike | null = null;
  private _reconnect: ReconnectScheduler | null;
  private _subscribedKeys = new Set<string>();

  /** Called for each state update. */
  onState: ((key: string, data: unknown) => void) | null = null;
  /** Called when the socket connects (including reconnects). */
  onConnected: (() => void) | null = null;
  /** Called when the socket disconnects. */
  onDisconnected: (() => void) | null = null;
  /** Called for every incoming message (before protocol routing). */
  onRawMessage: ((data: unknown) => void) | null = null;

  constructor(create: () => SocketLike, opts?: WebSocketClientOptions) {
    this._create = create;
    const doReconnect = opts?.reconnect !== false;
    this._reconnect = doReconnect ? new ReconnectScheduler() : null;
  }

  /**
   * Open the connection. Resolves on first successful open.
   * With reconnect enabled, never rejects — the scheduler retries in the
   * background and the promise resolves once any attempt succeeds.
   * With reconnect disabled, rejects if the first attempt fails.
   */
  connect(): Promise<void> {
    this._reconnect?.start();
    return new Promise<void>((resolve, reject) => {
      let settled = false;
      const settle = (fn: () => void) => {
        if (!settled) {
          settled = true;
          fn();
        }
      };

      const open = () => {
        if (this._socket) this._socket.close();

        const socket = this._create();
        this._socket = socket;

        socket.onopen = () => {
          this._reconnect?.resetDelay();
          if (this._subscribedKeys.size > 0) {
            sendSubscribe(socket, [...this._subscribedKeys]);
          }
          this.onConnected?.();
          settle(() => resolve());
        };

        socket.onmessage = (event) => {
          this.onRawMessage?.(event.data);
          const msg = parseMessage(event.data);
          if (msg?.type === MSG_TYPE.STATE) {
            this.onState?.(msg.key, msg.data);
          }
        };

        socket.onclose = () => {
          this._socket = null;
          this.onDisconnected?.();
          this._reconnect?.schedule(open);
          if (!this._reconnect) {
            settle(() => reject(new Error("WebSocket closed before open")));
          }
        };

        socket.onerror = () => {};
      };

      open();
    });
  }

  /** Track subscription keys (accumulated, re-sent on every reconnect). */
  subscribe(keys: string[]): void {
    for (const k of keys) this._subscribedKeys.add(k);
    if (this._socket) {
      sendSubscribe(this._socket, [...this._subscribedKeys]);
    }
  }

  /** Send an action message. Returns false if not connected. */
  sendAction(action: string, payload?: Record<string, unknown>): boolean {
    return sendActionRaw(this._socket, action, payload);
  }

  /** Stop reconnecting and close the socket. */
  close(): void {
    this._reconnect?.stop();
    if (this._socket) {
      this._socket.close();
      this._socket = null;
    }
  }
}
