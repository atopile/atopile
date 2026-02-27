/**
 * Reconnecting WebSocket client to the core server.
 *
 * Wraps the shared WebSocketClient, connects to /atopile-core,
 * and routes state updates into the hub store.
 */

import WebSocket from "ws";
import { store } from "./main";
import { WebSocketClient, type SocketLike } from "../shared/webSocketClient";

export type OnConnectedCallback = () => void;

export class CoreWebSocketClient {
  private _client: WebSocketClient | null = null;

  /** Start the connection loop. */
  start(port: number, onConnected: OnConnectedCallback | null = null): void {
    const url = `ws://localhost:${port}/atopile-core`;
    console.log(`Connecting to core server at ${url}`);

    this._client = new WebSocketClient(
      () => new WebSocket(url) as unknown as SocketLike,
    );

    this._client.onConnected = () => {
      console.log("Connected to core server");
      store.merge("coreStatus", { connected: true });
      onConnected?.();
    };

    this._client.onDisconnected = () => {
      store.merge("coreStatus", { connected: false });
    };

    this._client.onState = (key, data) => {
      switch (key) {
        case "currentBuilds":
        case "previousBuilds":
        case "projects":
        case "projectFiles":
        case "packagesSummary":
        case "partsSearch":
        case "installedParts":
        case "stdlibData":
        case "structureData":
        case "variablesData":
        case "bomData":
          store.set(key as any, data as any);
          break;
        default:
          console.warn(`Unknown state key from core: ${key}`);
      }
    };

    this._client.connect();
  }

  /** Send an action message to the core server. */
  sendAction(action: string, payload?: Record<string, unknown>): void {
    if (!this._client?.sendAction(action, payload)) {
      console.error("Failed to send action to core server");
    }
  }

  /** Stop the connection loop and close the socket. */
  stop(): void {
    this._client?.close();
    this._client = null;
  }
}
