/**
 * Reconnecting WebSocket client to the core server.
 *
 * Wraps the shared WebSocketClient, connects to /atopile-core,
 * and routes state updates into the hub store.
 */

import WebSocket from "ws";
import { store } from "./main";
import type { Build, FileNode } from "../shared/types";
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
      store.set("coreStatus", { connected: true });
      onConnected?.();
    };

    this._client.onDisconnected = () => {
      store.set("coreStatus", { connected: false });
    };

    this._client.onState = (key, data) => {
      const payload = (data as Record<string, unknown>) ?? {};
      switch (key) {
        case "currentBuilds":
          store.setArray("currentBuilds", (payload.currentBuilds ?? []) as Build[]);
          break;
        case "previousBuilds":
          store.setArray("previousBuilds", (payload.previousBuilds ?? []) as Build[]);
          break;
        case "projectFiles":
          store.setArray("projectFiles", (payload.projectFiles ?? []) as FileNode[]);
          break;
        case "projects":
          store.set("projectState", { projects: payload.projects as any });
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
