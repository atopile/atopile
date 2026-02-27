/**
 * Webview-side WebSocket client backed by the shared WebSocketClient.
 *
 * Maintains a local state snapshot for React reactivity via a listener
 * fan-out and a useSubscribe() hook.
 */

import { useEffect, useState } from "react";
import { StoreState } from "../../shared/types";
import { WebSocketClient, type SocketLike } from "../../shared/webSocketClient";

/** Keys managed locally by the webview, not subscribed from the hub. */
const LOCAL_KEYS: ReadonlySet<keyof StoreState> = new Set(["hubStatus"]);

export class WebviewWebSocketClient {
  private _client: WebSocketClient;
  private _state = new StoreState();
  private _listeners = new Set<() => void>();

  constructor(hubUrl: string) {
    this._client = new WebSocketClient(
      () => new WebSocket(hubUrl) as unknown as SocketLike,
    );

    this._client.onConnected = () => {
      this._setState("hubStatus", { connected: true });
    };

    this._client.onDisconnected = () => {
      this._setState("hubStatus", { connected: false });
    };

    this._client.onState = (key, data) => {
      this._setState(key as keyof StoreState, data);
    };
  }

  connect(): void {
    this._client.connect();
  }

  subscribe(keys: string[]): void {
    const remote = keys.filter((k) => !LOCAL_KEYS.has(k as keyof StoreState));
    if (remote.length > 0) this._client.subscribe(remote);
  }

  get<K extends keyof StoreState>(key: K): StoreState[K] {
    return this._state[key];
  }

  sendAction(action: string, payload?: Record<string, unknown>): boolean {
    return this._client.sendAction(action, payload);
  }

  close(): void {
    this._client.close();
  }

  addListener(fn: () => void): void {
    this._listeners.add(fn);
  }

  removeListener(fn: () => void): void {
    this._listeners.delete(fn);
  }

  private _setState(key: keyof StoreState, data: unknown): void {
    this._state = { ...this._state, [key]: data } as StoreState;
    for (const fn of this._listeners) fn();
  }

  // -- React hook -------------------------------------------------------------

  static useSubscribe<K extends keyof StoreState>(key: K): StoreState[K] {
    const [, bump] = useState(0);
    useEffect(() => {
      webviewClient?.subscribe([key]);
      const cb = () => bump((n) => n + 1);
      webviewClient?.addListener(cb);
      return () => { webviewClient?.removeListener(cb); };
    }, [key]);
    return webviewClient?.get(key) ?? new StoreState()[key];
  }
}

// -- Module singleton ---------------------------------------------------------

export let webviewClient: WebviewWebSocketClient | null = null;

export function connectWebview(hubUrl: string): void {
  webviewClient = new WebviewWebSocketClient(hubUrl);
  webviewClient.connect();
}
