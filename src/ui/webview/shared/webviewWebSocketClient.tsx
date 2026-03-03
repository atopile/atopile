/**
 * Webview-side WebSocket client backed by the shared WebSocketClient.
 *
 * Maintains a local state snapshot for React reactivity via
 * onState and a useSubscribe() hook.
 */

import { useEffect, useState } from "react";
import { StoreState } from "../../shared/types";
import { WebSocketClient, type SocketLike } from "../../shared/webSocketClient";

export class WebviewWebSocketClient {
  protected _client: WebSocketClient;
  protected _state = new StoreState();
  protected _listeners = new Set<() => void>();

  constructor(url: string) {
    this._client = new WebSocketClient(
      () => new WebSocket(url) as unknown as SocketLike,
    );

    const setState = (key: string, data: unknown) => {
      this._state = { ...this._state, [key]: data } as StoreState;
      this._notify();
    };

    this._client.onConnected = () => setState("hubConnected", true);
    this._client.onDisconnected = () => setState("hubConnected", false);
    this._client.onState = (key, data) => {
      if (key === "hubConnected") return; // managed locally by onConnected/onDisconnected
      setState(key, data);
    };
  }

  protected _notify(): void {
    for (const fn of this._listeners) fn();
  }

  connect(): void {
    this._client.connect();
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

  // -- React hooks --------------------------------------------------------------

  static useSubscribe<K extends keyof StoreState>(key: K): StoreState[K] {
    const [, bump] = useState(0);
    useEffect(() => {
      webviewClient?._client.subscribe([key]);
      const cb = () => bump((n) => n + 1);
      webviewClient?._listeners.add(cb);
      return () => { webviewClient?._listeners.delete(cb); };
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
