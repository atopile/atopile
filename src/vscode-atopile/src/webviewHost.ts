import * as vscode from "vscode";
import { ExtensionLogger } from "./logger";
import { RpcProxy } from "./rpcProxy";

export const SIDEBAR_VIEW_ID = "atopile.sidebarView";
export const LOGS_VIEW_ID = "atopile.logsView";

class HostedPanel implements vscode.Disposable {
  private _panel: vscode.WebviewPanel | undefined;
  private readonly _sessionConnection: vscode.Disposable;

  constructor(
    extensionUri: vscode.Uri,
    proxy: RpcProxy,
    panelId: string,
    layoutServerPort: number,
    column: vscode.ViewColumn,
    onDispose: () => void,
  ) {
    const panel = vscode.window.createWebviewPanel(
      `atopile.${panelId}`,
      `atopile: ${panelId}`,
      column,
      buildPanelOptions(extensionUri, panelId, layoutServerPort),
    );
    this._panel = panel;
    configureWebview(extensionUri, panel.webview, panelId, layoutServerPort);
    this._sessionConnection = proxy.connectWebviewSession(panelId, panel.webview);
    panel.onDidDispose(() => {
      this._sessionConnection.dispose();
      this._panel = undefined;
      onDispose();
    });
  }

  isOpen(): boolean {
    return this._panel !== undefined;
  }

  reveal(column: vscode.ViewColumn): void {
    this._panel?.reveal(column);
  }

  dispose(): void {
    this._panel?.dispose();
  }
}

export class HostedWebviewViewProvider
  implements vscode.WebviewViewProvider, vscode.Disposable
{
  private readonly _extensionUri: vscode.Uri;
  private readonly _proxy: RpcProxy;
  private readonly _panelId: string;
  private _view: vscode.WebviewView | undefined;
  private _sessionConnection: vscode.Disposable | undefined;

  constructor(extensionUri: vscode.Uri, proxy: RpcProxy, panelId: string) {
    this._extensionUri = extensionUri;
    this._proxy = proxy;
    this._panelId = panelId;
  }

  resolveWebviewView(
    webviewView: vscode.WebviewView,
    _context: vscode.WebviewViewResolveContext,
    _token: vscode.CancellationToken,
  ): void {
    this._view = webviewView;
    configureWebview(this._extensionUri, webviewView.webview, this._panelId);
    this._connectSession(webviewView.webview);

    webviewView.onDidDispose(() => {
      this._view = undefined;
      this._disconnectSession();
    });
  }

  reveal(preserveFocus = false): void {
    this._view?.show?.(preserveFocus);
  }

  dispose(): void {
    this._view = undefined;
    this._disconnectSession();
  }

  private _connectSession(webview: vscode.Webview): void {
    this._disconnectSession();
    this._sessionConnection = this._proxy.connectWebviewSession(this._panelId, webview);
  }

  private _disconnectSession(): void {
    this._sessionConnection?.dispose();
    this._sessionConnection = undefined;
  }
}

export class PanelHost implements vscode.Disposable {
  private readonly _extensionUri: vscode.Uri;
  private readonly _proxy: RpcProxy;
  private readonly _layoutServerPort: number;
  private readonly _logger: ExtensionLogger;
  private readonly _panels = new Map<string, HostedPanel>();

  constructor(
    extensionUri: vscode.Uri,
    proxy: RpcProxy,
    layoutServerPort: number,
    logger: ExtensionLogger,
  ) {
    this._extensionUri = extensionUri;
    this._proxy = proxy;
    this._layoutServerPort = layoutServerPort;
    this._logger = logger.scope("PanelHost");
  }

  openPanel(panelId: string): void {
    if (panelId === "panel-logs") {
      throw new Error("panel-logs must be shown in the bottom logs view, not opened as a panel");
    }
    try {
      const existing = this._panels.get(panelId);
      this._logger.info(`openPanel panelId=${panelId} hasExisting=${Boolean(existing)}`);
      if (existing?.isOpen()) {
        try {
          existing.reveal(this._panelColumn(panelId));
          this._logger.info(
            `revealed existing panelId=${panelId} targetColumn=${this._panelColumn(panelId)}`,
          );
          return;
        } catch (error) {
          this._logger.warn(
            `disposing stale panelId=${panelId} error=${error instanceof Error ? error.message : String(error)}`,
          );
          existing.dispose();
          this._panels.delete(panelId);
        }
      } else if (existing) {
        this._panels.delete(panelId);
      }

      this._logger.info(
        `creating panelId=${panelId} targetColumn=${this._panelColumn(panelId)}`,
      );
      const panel = new HostedPanel(
        this._extensionUri,
        this._proxy,
        panelId,
        this._layoutServerPort,
        this._panelColumn(panelId),
        () => {
          this._logger.info(`onDidDispose panelId=${panelId}`);
          this._panels.delete(panelId);
        },
      );
      this._panels.set(panelId, panel);
      this._logger.info(`created panelId=${panelId}`);
    } catch (error) {
      const detail = error instanceof Error ? error.stack ?? error.message : String(error);
      this._logger.error(`openPanel exception panelId=${panelId}\n${detail}`);
      throw error;
    }
  }

  dispose(): void {
    for (const panel of this._panels.values()) {
      panel.dispose();
    }
    this._panels.clear();
  }

  private _panelColumn(panelId: string): vscode.ViewColumn {
    if (panelId === "panel-layout" || panelId === "panel-3d") {
      return vscode.ViewColumn.Beside;
    }
    return vscode.ViewColumn.Active;
  }
}

function configureWebview(
  extensionUri: vscode.Uri,
  webview: vscode.Webview,
  panelId: string,
  layoutServerPort = 0,
): void {
  webview.options = {
    enableScripts: true,
    localResourceRoots: getLocalResourceRoots(extensionUri),
  };
  webview.html = getHtml(extensionUri, webview, panelId, layoutServerPort);
}

function getHtml(
  extensionUri: vscode.Uri,
  webview: vscode.Webview,
  panelId: string,
  layoutServerPort = 0,
): string {
  const distUri = vscode.Uri.joinPath(extensionUri, "webview-dist");
  const scriptUri = webview.asWebviewUri(vscode.Uri.joinPath(distUri, panelId, "index.js"));
  const styleUri = webview.asWebviewUri(vscode.Uri.joinPath(distUri, panelId, "index.css"));
  const logoUri = webview.asWebviewUri(vscode.Uri.joinPath(distUri, "logo.png"));
  const stepViewerWasmUri = webview.asWebviewUri(vscode.Uri.joinPath(distUri, "occt-import-js.wasm"));
  const glbViewerScriptUri = webview.asWebviewUri(vscode.Uri.joinPath(distUri, "model-viewer.min.js"));
  const layoutServerUrl =
    panelId === "panel-layout" && layoutServerPort > 0
      ? `http://127.0.0.1:${layoutServerPort}`
      : "";
  const csp = webview.cspSource;
  const frameSrc =
    panelId === "panel-layout" && layoutServerPort > 0 ? `frame-src ${layoutServerUrl};` : "";

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta http-equiv="Content-Security-Policy"
    content="default-src 'none';
      script-src 'unsafe-inline' 'unsafe-eval' 'wasm-unsafe-eval' ${csp} https:;
      style-src 'unsafe-inline' ${csp} https:;
      img-src ${csp} https: data: blob:;
      font-src ${csp} https: data:;
      connect-src ${csp} https: blob:;
      ${frameSrc}
      worker-src ${csp} https: blob:;" />
  <link rel="stylesheet" href="${styleUri}" />
  <title>atopile</title>
</head>
<body>
  <div id="root"></div>
  <script>
    window.__ATOPILE_PANEL_ID__ = "${panelId}";
    window.__ATOPILE_LOGO_URL__ = "${logoUri}";
    window.__ATOPILE_STEP_VIEWER_WASM_URL__ = "${stepViewerWasmUri}";
    window.__ATOPILE_GLB_VIEWER_SCRIPT_URL__ = "${glbViewerScriptUri}";
    window.__ATOPILE_LAYOUT_SERVER_URL__ = "${layoutServerUrl}";
  </script>
  <script type="module" src="${scriptUri}"></script>
</body>
</html>`;
}

function buildPanelOptions(
  extensionUri: vscode.Uri,
  panelId: string,
  layoutServerPort: number,
): vscode.WebviewPanelOptions & {
  enableScripts: true;
  localResourceRoots: vscode.Uri[];
  portMapping?: { webviewPort: number; extensionHostPort: number }[];
} {
  return {
    enableScripts: true,
    retainContextWhenHidden: true,
    localResourceRoots: getLocalResourceRoots(extensionUri),
    ...(panelId === "panel-layout" && layoutServerPort > 0
      ? {
          portMapping: [
            {
              webviewPort: layoutServerPort,
              extensionHostPort: layoutServerPort,
            },
          ],
        }
      : {}),
  };
}

function getLocalResourceRoots(extensionUri: vscode.Uri): vscode.Uri[] {
  return [
    extensionUri,
    ...(vscode.workspace.workspaceFolders?.map((folder) => folder.uri) ?? []),
  ];
}
