import * as vscode from "vscode";
import { getBuildTarget, openKicadForBuild } from "./kicad";

export type ExtensionRequestMessage = {
  type: "extension_request";
  requestId: string;
  action: string;
  [key: string]: unknown;
};

export type ExtensionRequestResult =
  | {
      ok: true;
      result?: unknown;
    }
  | {
      ok: false;
      error: string;
    };

export class ExtensionRequestHandler {
  private readonly _openPanel: (panelId: string) => void;
  private readonly _output: vscode.OutputChannel;

  constructor(openPanel: (panelId: string) => void, output: vscode.OutputChannel) {
    this._openPanel = openPanel;
    this._output = output;
  }

  async handle(
    webview: vscode.Webview,
    message: ExtensionRequestMessage,
  ): Promise<ExtensionRequestResult> {
    switch (message.action) {
      case "vscode.openPanel": {
        const panelId = this._requireString(message.panelId, "panelId");
        this._openPanel(panelId);
        return { ok: true };
      }

      case "vscode.openFile": {
        const filePath = this._requireString(message.path, "path");
        await vscode.window.showTextDocument(vscode.Uri.file(filePath));
        return { ok: true };
      }

      case "vscode.browseFolder": {
        const result = await vscode.window.showOpenDialog({
          canSelectFiles: false,
          canSelectFolders: true,
          canSelectMany: false,
          openLabel: "Select folder",
        });
        return {
          ok: true,
          result: result?.[0]?.fsPath,
        };
      }

      case "vscode.openKicad": {
        const projectRoot = this._requireString(message.projectRoot, "projectRoot");
        const target = this._requireString(message.target, "target");
        await openKicadForBuild(projectRoot, target);
        return { ok: true };
      }

      case "vscode.resolveThreeDModel": {
        const projectRoot = this._requireString(message.projectRoot, "projectRoot");
        const target = this._requireString(message.target, "target");
        const build = await getBuildTarget(projectRoot, target);
        const modelFile = vscode.Uri.file(build.model_path);
        const exists = await this._pathExists(modelFile);
        const stat = exists ? await vscode.workspace.fs.stat(modelFile) : undefined;

        return {
          ok: true,
          result: {
            exists,
            modelPath: build.model_path,
            modelUri: webview.asWebviewUri(modelFile).toString(),
            version: stat?.mtime ?? null,
          },
        };
      }

      case "vscode.log": {
        const level = typeof message.level === "string" ? message.level : "log";
        const text = typeof message.message === "string" ? message.message : "";
        const prefix =
          level === "error" ? "[Webview] ERR" : level === "warn" ? "[Webview] WARN" : "[Webview]";
        this._output.appendLine(`${prefix} ${text}`);
        return { ok: true };
      }

      default:
        return {
          ok: false,
          error: `Unsupported extension action: ${message.action}`,
        };
    }
  }

  private _requireString(value: unknown, name: string): string {
    if (typeof value !== "string" || !value) {
      throw new Error(`Missing required field: ${name}`);
    }
    return value;
  }

  private async _pathExists(uri: vscode.Uri): Promise<boolean> {
    try {
      await vscode.workspace.fs.stat(uri);
      return true;
    } catch {
      return false;
    }
  }
}
