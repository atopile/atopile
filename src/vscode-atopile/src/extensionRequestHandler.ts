import * as vscode from "vscode";
import { getBuildTarget, openKicadForBuild } from "./kicad";
import { ExtensionLogger } from "./logger";

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
  private readonly _logger: ExtensionLogger;

  constructor(openPanel: (panelId: string) => void, logger: ExtensionLogger) {
    this._openPanel = openPanel;
    this._logger = logger.scope("ExtensionRequest");
  }

  async handle(
    webview: vscode.Webview,
    message: ExtensionRequestMessage,
  ): Promise<ExtensionRequestResult> {
    switch (message.action) {
      case "vscode.openPanel": {
        const panelId = this._requireString(message.panelId, "panelId");
        this._logger.info(`openPanel requested panelId=${panelId}`);
        try {
          this._openPanel(panelId);
        } catch (error) {
          const detail = error instanceof Error ? error.stack ?? error.message : String(error);
          this._logger.error(`openPanel failed panelId=${panelId}\n${detail}`);
          throw error;
        }
        this._logger.info(`openPanel completed panelId=${panelId}`);
        return { ok: true };
      }

      case "vscode.openFile": {
        const filePath = this._requireString(message.path, "path");
        const line = this._optionalNumber(message.line);
        const document = await vscode.workspace.openTextDocument(vscode.Uri.file(filePath));
        if (line == null) {
          await vscode.window.showTextDocument(document);
          return { ok: true };
        }
        const position = new vscode.Position(Math.max(0, line - 1), 0);
        await vscode.window.showTextDocument(document, {
          selection: new vscode.Range(position, position),
        });
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
        const modelFile = vscode.Uri.file(build.modelPath);
        const exists = await this._pathExists(modelFile);
        const stat = exists ? await vscode.workspace.fs.stat(modelFile) : undefined;

        return {
          ok: true,
          result: {
            exists,
            modelPath: build.modelPath,
            modelUri: webview.asWebviewUri(modelFile).toString(),
            version: stat?.mtime ?? null,
          },
        };
      }

      case "vscode.log": {
        const level = typeof message.level === "string" ? message.level : "log";
        const text = typeof message.message === "string" ? message.message : "";
        if (level === "error") {
          this._logger.error(`[Webview] ${text}`);
        } else if (level === "warn") {
          this._logger.warn(`[Webview] ${text}`);
        } else {
          this._logger.info(`[Webview] ${text}`);
        }
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

  private _optionalNumber(value: unknown): number | undefined {
    return typeof value === "number" && Number.isFinite(value) ? value : undefined;
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
