import * as vscode from "vscode";
import * as path from "path";
import { openPcb } from "./kicad";
import { ExtensionLogger } from "./logger";
import type { ResolvedBuildTarget } from "../../ui/shared/generated-types";

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
  private readonly _showLogsView: () => Promise<void> | void;
  private readonly _logger: ExtensionLogger;

  constructor(
    openPanel: (panelId: string) => void,
    showLogsView: () => Promise<void> | void,
    logger: ExtensionLogger,
  ) {
    this._openPanel = openPanel;
    this._showLogsView = showLogsView;
    this._logger = logger.scope("ExtensionRequest");
  }

  async handle(
    webview: vscode.Webview,
    message: ExtensionRequestMessage,
  ): Promise<ExtensionRequestResult> {
    switch (message.action) {
      case "vscode.openPanel": {
        const panelId = this._requireString(message.panelId, "panelId");
        if (panelId === "panel-logs") {
          return {
            ok: false,
            error: "panel-logs is not a panel; use vscode.showLogsView",
          };
        }
        this._logger.debug(`openPanel requested panelId=${panelId}`);
        try {
          this._openPanel(panelId);
        } catch (error) {
          const detail = error instanceof Error ? error.stack ?? error.message : String(error);
          this._logger.error(`openPanel failed panelId=${panelId}\n${detail}`);
          throw error;
        }
        this._logger.debug(`openPanel completed panelId=${panelId}`);
        return { ok: true };
      }

      case "vscode.showLogsView": {
        await this._showLogsView();
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

      case "vscode.openDiff": {
        const filePath = this._requireString(message.path, "path");
        const beforeContent = typeof message.beforeContent === "string" ? message.beforeContent : "";
        const afterContent = typeof message.afterContent === "string" ? message.afterContent : "";
        const title = typeof message.title === "string" && message.title
          ? message.title
          : `Agent diff: ${path.basename(filePath)}`;

        const left = vscode.Uri.parse(`untitled:${filePath}.before`);
        const right = vscode.Uri.parse(`untitled:${filePath}.after`);
        const leftEdit = new vscode.WorkspaceEdit();
        leftEdit.insert(left, new vscode.Position(0, 0), beforeContent);
        const rightEdit = new vscode.WorkspaceEdit();
        rightEdit.insert(right, new vscode.Position(0, 0), afterContent);
        await vscode.workspace.applyEdit(leftEdit);
        await vscode.workspace.applyEdit(rightEdit);
        await vscode.commands.executeCommand("vscode.diff", left, right, title, {
          preview: true,
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

      case "vscode.revealInOs": {
        const filePath = this._requireString(message.path, "path");
        await vscode.commands.executeCommand("revealFileInOS", vscode.Uri.file(filePath));
        return { ok: true };
      }

      case "vscode.openInTerminal": {
        const filePath = this._requireString(message.path, "path");
        const cwd = await this._terminalCwd(vscode.Uri.file(filePath));
        const terminal = vscode.window.createTerminal({
          cwd,
          name: `Terminal: ${path.basename(cwd.fsPath) || cwd.fsPath}`,
        });
        terminal.show();
        return { ok: true };
      }

      case "vscode.openKicad":
        await openPcb((message.target as ResolvedBuildTarget).pcbPath);
        return { ok: true };

      case "vscode.resolveThreeDModel": {
        const target = message.target as ResolvedBuildTarget;
        const modelFile = vscode.Uri.file(target.modelPath);
        const exists = await this._pathExists(modelFile);
        const stat = exists ? await vscode.workspace.fs.stat(modelFile) : undefined;

        return {
          ok: true,
          result: {
            exists,
            modelPath: target.modelPath,
            modelUri: webview.asWebviewUri(modelFile).toString(),
            version: stat?.mtime ?? null,
          },
        };
      }

      case "vscode.restartExtensionHost": {
        void vscode.commands.executeCommand("workbench.action.restartExtensionHost");
        return { ok: true };
      }

      case "vscode.log": {
        const level = typeof message.level === "string" ? message.level : "log";
        const text = typeof message.message === "string" ? message.message : "";
        if (level === "error") {
          this._logger.error(`[Webview] ${text}`);
        } else if (level === "warn") {
          this._logger.warn(`[Webview] ${text}`);
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
  private async _terminalCwd(uri: vscode.Uri): Promise<vscode.Uri> {
    const stat = await vscode.workspace.fs.stat(uri);
    if (this._isDirectory(stat.type)) {
      return uri;
    }
    return vscode.Uri.file(path.dirname(uri.fsPath));
  }

  private _isDirectory(fileType: vscode.FileType): boolean {
    return (fileType & vscode.FileType.Directory) !== 0;
  }

}
