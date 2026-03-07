import * as vscode from "vscode";
import { RpcClient } from "../../ui/shared/rpcClient";
import type { ExtensionSettings } from "../../ui/shared/types";
import { EXTENSION_SESSION_ID, RpcProxy } from "./rpcProxy";

export class CoreClient implements vscode.Disposable {
  private readonly _client: RpcClient;
  private readonly _workspaceFolders: string[];
  private _resolverInfo:
    | {
        uvPath: string;
        atoBinary: string;
        mode: "local" | "production";
        version: string;
        coreServerPort: number;
      }
    | null = null;
  private _activeFilePath: string | null = null;
  private _waitingForSettingsEcho = false;

  constructor(proxy: RpcProxy, workspaceFolders: string[]) {
    this._workspaceFolders = workspaceFolders;
    this._client = new RpcClient(() => proxy.createTransport(EXTENSION_SESSION_ID));

    this._client.onConnected = () => {
      this._waitingForSettingsEcho = true;
      this.sendExtensionSettings();
      this._client.subscribe(["extensionSettings"]);
      this.sendAction("discoverProjects", { paths: this._workspaceFolders });
      if (this._resolverInfo) {
        this.sendAction("resolverInfo", this._resolverInfo);
      }
      this.sendActiveFile(this._activeFilePath);
    };

    this._client.onState = (key, data) => {
      if (key !== "extensionSettings") {
        return;
      }

      const settings = data as Partial<ExtensionSettings>;
      const localSettings = this._getExtensionSettings();
      const matchesLocalSettings =
        settings.devPath === localSettings.devPath &&
        settings.autoInstall === localSettings.autoInstall;

      if (this._waitingForSettingsEcho) {
        if (matchesLocalSettings) {
          this._waitingForSettingsEcho = false;
        }
        return;
      }
      if (matchesLocalSettings) {
        return;
      }

      const config = vscode.workspace.getConfiguration("atopile");

      if (settings.devPath !== undefined) {
        void config.update("devPath", settings.devPath, vscode.ConfigurationTarget.Global);
      }
      if (settings.autoInstall !== undefined) {
        void config.update(
          "autoInstall",
          settings.autoInstall,
          vscode.ConfigurationTarget.Global,
        );
      }
    };
  }

  start(): void {
    void this._client.connect();
  }

  sendResolverInfo(info: {
    uvPath: string;
    atoBinary: string;
    mode: "local" | "production";
    version: string;
    coreServerPort: number;
  }): boolean {
    this._resolverInfo = info;
    return this.sendAction("resolverInfo", info as Record<string, unknown>);
  }

  sendExtensionSettings(): boolean {
    return this.sendAction(
      "extensionSettings",
      this._getExtensionSettings() as unknown as Record<string, unknown>,
    );
  }

  sendActiveFile(filePath: string | null): boolean {
    this._activeFilePath = filePath;
    return this.sendAction("setActiveFile", { filePath });
  }

  sendAction(action: string, payload?: Record<string, unknown>): boolean {
    return this._client.sendAction(action, payload);
  }

  dispose(): void {
    this._client.close();
  }

  private _getExtensionSettings(): ExtensionSettings {
    const config = vscode.workspace.getConfiguration("atopile");
    return {
      devPath: config.get<string>("devPath", ""),
      autoInstall: config.get<boolean>("autoInstall", true),
    };
  }
}
