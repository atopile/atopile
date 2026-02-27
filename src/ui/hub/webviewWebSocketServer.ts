/**
 * WebSocket server for webview clients.
 *
 * Manages subscriptions and broadcasts state changes to
 * interested webview clients.
 */

import { WebSocketServer, WebSocket } from "ws";
import type { IncomingMessage } from "http";
import { store, coreSocket } from "./main";
import { MSG_TYPE, type ActionMessage, type WebSocketMessage } from "../shared/types";
import { parseMessage, sendState } from "../shared/webSocketClient";

export class WebviewWebSocketServer {
  private _wss: WebSocketServer | null = null;
  private _subscriptions = new Map<WebSocket, Set<string>>();

  /** Start the WebSocket server on the given port. Returns when listening. */
  start(port: number): Promise<void> {
    store.onChange = (key, value) => {
      this.broadcastChange(key, value);
    };
    return new Promise((resolve, reject) => {
      this._wss = new WebSocketServer({ host: "localhost", port });

      this._wss.on("listening", () => resolve());
      this._wss.on("error", (err) => reject(err));

      this._wss.on("connection", (ws: WebSocket, req: IncomingMessage) => {
        this._handleConnection(ws, req);
      });
    });
  }

  private _handleConnection(ws: WebSocket, req: IncomingMessage): void {
    const url = req.url ?? "";
    if (url !== "/atopile-ui") {
      ws.close(4000, "unknown path");
      return;
    }

    this._subscriptions.set(ws, new Set());
    console.log(
      `Client connected (${this._subscriptions.size} total)`
    );

    ws.on("message", (raw) => {
      const msg = parseMessage(raw);
      if (!msg) {
        console.error("Failed to parse client message");
        return;
      }
      this._onMessage(ws, msg);
    });

    ws.on("close", () => {
      this._subscriptions.delete(ws);
      console.log(
        `Client disconnected (${this._subscriptions.size} total)`
      );
    });
  }

  private _onMessage(ws: WebSocket, msg: WebSocketMessage): void {
    switch (msg.type) {
      case MSG_TYPE.SUBSCRIBE: {
        this._subscriptions.set(ws, new Set(msg.keys));
        for (const key of msg.keys) {
          try {
            const value = store.get(key as any);
            sendState(ws, key, value);
          } catch {
            console.error(`Client subscribed to unknown key: ${key}`);
          }
        }
        break;
      }
      case MSG_TYPE.ACTION: {
        this._handleAction(msg);
        break;
      }
    }
  }

  private _handleAction(msg: ActionMessage): void {
    switch (msg.action) {
      case "selectProject": {
        const projectRoot = (msg.projectRoot as string) ?? null;
        store.merge("projectState", {
          selectedProject: projectRoot,
          selectedTarget: null,
        });
        // Auto-fire list_files so the file tree loads immediately
        if (projectRoot) {
          coreSocket.sendAction("listFiles", { projectRoot });
        }
        return;
      }
      case "listFiles": {
        coreSocket.sendAction("listFiles", {
          projectRoot: msg.projectRoot as string,
        });
        return;
      }
      case "selectTarget": {
        store.merge("projectState", {
          selectedTarget: (msg.target as string) ?? null,
        });
        return;
      }
      case "startBuild": {
        coreSocket.sendAction("startBuild", {
          projectRoot: msg.projectRoot as string,
          targets: msg.targets as string[],
        });
        return;
      }
      case "resolverInfo": {
        store.merge("coreStatus", {
          uvPath: msg.uvPath as string,
          atoBinary: msg.atoBinary as string,
          mode: msg.mode as "local" | "production",
          version: msg.version as string,
        });
        return;
      }
      case "coreStartupError": {
        store.merge("coreStatus", { error: msg.message as string });
        coreSocket.stop();
        return;
      }
      case "extensionSettings": {
        store.merge("extensionSettings", {
          devPath: msg.devPath as string,
          autoInstall: msg.autoInstall as boolean,
        });
        return;
      }
      case "updateExtensionSetting": {
        store.merge("extensionSettings", {
          [msg.key as string]: msg.value,
        });
        return;
      }
      case "setActiveFile": {
        store.merge("projectState", {
          activeFilePath: msg.filePath as string,
        });
        return;
      }
      default: {
        coreSocket.sendAction(msg.action, msg as Record<string, unknown>);
      }
    }
  }

  /** Broadcast a store change to all clients subscribed to the given key. */
  broadcastChange(key: string, value: unknown): void {
    const dead: WebSocket[] = [];

    for (const [ws, keys] of this._subscriptions) {
      if (!keys.has(key)) continue;
      if (!sendState(ws, key, value)) {
        dead.push(ws);
      }
    }

    for (const ws of dead) {
      this._subscriptions.delete(ws);
    }
  }

  stop(): void {
    this._wss?.close();
    this._wss = null;
  }
}
