import { useEffect, useState } from "react";
import { RpcClient } from "../../shared/rpcClient";
import { StoreState } from "../../shared/types";
import { PostMessageTransport } from "./postMessageTransport";

type RawMessageListener = (data: string) => void;
type ConnectionListener = (connected: boolean) => void;

export class WebviewRpcClient {
  protected readonly _client: RpcClient;
  protected _state = new StoreState();
  protected _listeners = new Set<() => void>();
  private readonly _rawListeners = new Set<RawMessageListener>();
  private readonly _connectionListeners = new Set<ConnectionListener>();

  constructor() {
    this._client = new RpcClient(() => new PostMessageTransport());

    this._client.onConnected = () => {
      this._setState("connected", true);
      this._notifyConnection(true);
    };

    this._client.onDisconnected = () => {
      this._setState("connected", false);
      this._notifyConnection(false);
    };

    this._client.onState = (key, data) => {
      if (key === "connected") {
        return;
      }
      this._setState(key as keyof StoreState, data);
    };

    this._client.onRawMessage = (data) => {
      for (const listener of this._rawListeners) {
        listener(data);
      }
    };
  }

  connect(): void {
    void this._client.connect();
  }

  close(): void {
    this._client.close();
    this._setState("connected", false);
  }

  isConnected(): boolean {
    return this._client.isConnected;
  }

  get<K extends keyof StoreState>(key: K): StoreState[K] {
    return this._state[key];
  }

  sendAction(action: string, payload?: Record<string, unknown>): boolean {
    return this._client.sendAction(action, payload);
  }

  requestAction<T>(action: string, payload?: Record<string, unknown>): Promise<T> {
    return this._client.requestAction<T>(action, payload);
  }

  addRawListener(listener: RawMessageListener): void {
    this._rawListeners.add(listener);
  }

  removeRawListener(listener: RawMessageListener): void {
    this._rawListeners.delete(listener);
  }

  addConnectionListener(listener: ConnectionListener): void {
    this._connectionListeners.add(listener);
  }

  removeConnectionListener(listener: ConnectionListener): void {
    this._connectionListeners.delete(listener);
  }

  subscribe(keys: string[]): void {
    const remoteKeys = keys.filter((key) => key !== "connected");
    if (remoteKeys.length > 0) {
      this._client.subscribe(remoteKeys);
    }
  }

  static useSubscribe<K extends keyof StoreState>(key: K): StoreState[K] {
    const [, bump] = useState(0);
    useEffect(() => {
      rpcClient?.subscribe([key]);
      const callback = () => bump((n) => n + 1);
      rpcClient?._listeners.add(callback);
      return () => {
        rpcClient?._listeners.delete(callback);
      };
    }, [key]);
    return rpcClient?.get(key) ?? new StoreState()[key];
  }

  protected _notify(): void {
    for (const listener of this._listeners) {
      listener();
    }
  }

  private _notifyConnection(connected: boolean): void {
    for (const listener of this._connectionListeners) {
      listener(connected);
    }
  }

  private _setState(key: keyof StoreState, data: unknown): void {
    this._state = { ...this._state, [key]: data } as StoreState;
    this._notify();
  }
}

export let rpcClient: WebviewRpcClient | null = null;

export function connectWebview(): void {
  rpcClient = new WebviewRpcClient();
  rpcClient.connect();
}
