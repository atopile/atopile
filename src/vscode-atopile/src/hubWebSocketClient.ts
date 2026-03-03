/**
 * WebSocket client for the extension ↔ hub connection.
 *
 * Wraps the shared WebSocketClient, handles two-way extensionSettings
 * sync with VS Code configuration, and implements vscode.Disposable.
 */

import * as vscode from "vscode";
import WebSocket from "ws";
import { WebSocketClient, type SocketLike } from "../../ui/shared/webSocketClient";
import type { ExtensionSettings } from "../../ui/shared/types";
export class HubWebSocketClient implements vscode.Disposable {
  private _client: WebSocketClient;

  constructor(port: number) {
    this._client = new WebSocketClient(
      () => new WebSocket(`ws://localhost:${port}/atopile-ui`) as unknown as SocketLike,
      { reconnect: false },
    );

    this._client.onState = (key, data) => {
      if (key === "extensionSettings") {
        const settings = data as Partial<ExtensionSettings>;
        const config = vscode.workspace.getConfiguration("atopile");
        if (settings.devPath !== undefined) {
          config.update("devPath", settings.devPath, vscode.ConfigurationTarget.Global);
        }
        if (settings.autoInstall !== undefined) {
          config.update("autoInstall", settings.autoInstall, vscode.ConfigurationTarget.Global);
        }
      }
    };
  }

  /** Connect to the hub and push current VS Code settings. */
  async connect(): Promise<void> {
    await this._client.connect();
    this._client.subscribe(["extensionSettings"]);

    const config = vscode.workspace.getConfiguration("atopile");
    this._client.sendAction("extensionSettings", {
      devPath: config.get<string>("devPath", ""),
      autoInstall: config.get<boolean>("autoInstall", true),
    });
  }

  /** Send an action message. Returns false if not connected. */
  sendAction(action: string, payload?: Record<string, unknown>): boolean {
    return this._client.sendAction(action, payload);
  }

  /** Close the socket (vscode.Disposable). */
  dispose(): void {
    this._client.close();
  }
}
