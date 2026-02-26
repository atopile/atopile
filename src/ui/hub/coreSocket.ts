/**
 * Reconnecting WebSocket client to the core server.
 *
 * Connects to /atopile-core on the core server, relays state
 * updates into the store, and forwards actions.
 */

import WebSocket from "ws";
import { store } from "./main";
import { MSG_TYPE, type Build } from "../shared/types";
import { ReconnectScheduler, parseMessage, sendAction } from "../shared/webSocketUtils";

export type OnConnectedCallback = () => void;

export class CoreSocket {
  private _port = 0;
  private _onConnected: OnConnectedCallback | null = null;
  private _ws: WebSocket | null = null;
  private _reconnect = new ReconnectScheduler();

  /** Start the connection loop. */
  start(port: number, onConnected: OnConnectedCallback | null = null): void {
    this._port = port;
    this._onConnected = onConnected;
    this._reconnect.start();
    this._connect();
  }

  private _connect(): void {
    if (this._reconnect.stopped) return;

    const url = `ws://localhost:${this._port}/atopile-core`;
    console.log(`Connecting to core server at ${url}`);

    const ws = new WebSocket(url);
    this._ws = ws;

    ws.on("open", () => {
      console.log("Connected to core server");
      store.set("coreStatus", { connected: true });
      this._reconnect.resetDelay();
      this._onConnected?.();
    });

    ws.on("message", (data) => {
      const msg = parseMessage(data);
      if (!msg) {
        console.error("Failed to parse core server message");
        return;
      }
      if (msg.type === MSG_TYPE.STATE) {
        const payload = (msg.data as Record<string, unknown>) ?? {};
        switch (msg.key) {
          case "currentBuilds":
            store.setArray("currentBuilds", (payload.currentBuilds ?? []) as Build[]);
            break;
          case "previousBuilds":
            store.setArray("previousBuilds", (payload.previousBuilds ?? []) as Build[]);
            break;
          case "projects":
            store.set("projectState", { projects: payload.projects as any });
            break;
          default:
            console.warn(`Unknown state key from core: ${msg.key}`);
        }
      }
    });

    ws.on("close", () => {
      this._ws = null;
      store.set("coreStatus", { connected: false });
      this._reconnect.schedule(() => this._connect());
    });

    ws.on("error", (err) => {
      // Error is followed by close event, so reconnect happens there
      console.error(`Core server connection error: ${err.message}`);
    });
  }

  /** Send an action message to the core server. */
  sendAction(action: string, payload?: Record<string, unknown>): void {
    if (!sendAction(this._ws, action, payload)) {
      console.error("Failed to send action to core server");
    }
  }

  /** Stop the connection loop and close the socket. */
  stop(): void {
    this._reconnect.stop();
    if (this._ws) {
      this._ws.close();
      this._ws = null;
    }
  }
}
