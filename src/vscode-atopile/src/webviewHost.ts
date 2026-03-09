import * as vscode from "vscode";
import { RpcProxy } from "./rpcProxy";

export const SIDEBAR_VIEW_ID = "atopile.sidebarView";
export const LOGS_VIEW_ID = "atopile.logsView";

export class HostedWebviewViewProvider
  implements vscode.WebviewViewProvider, vscode.Disposable
{
  private readonly _extensionUri: vscode.Uri;
  private readonly _proxy: RpcProxy;
  private readonly _panelId: string;
  private readonly _proxyDisposables = new Map<vscode.Webview, vscode.Disposable>();

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
    configureWebview(this._extensionUri, webviewView.webview, this._panelId);
    this._attachProxy(webviewView.webview);

    webviewView.onDidDispose(() => {
      this._disposeProxy(webviewView.webview);
    });
  }

  dispose(): void {
    for (const disposable of this._proxyDisposables.values()) {
      disposable.dispose();
    }
    this._proxyDisposables.clear();
  }

  private _attachProxy(webview: vscode.Webview): void {
    this._disposeProxy(webview);
    this._proxyDisposables.set(
      webview,
      this._proxy.registerWebview(this._panelId, webview),
    );
  }

  private _disposeProxy(webview: vscode.Webview): void {
    const disposable = this._proxyDisposables.get(webview);
    if (!disposable) {
      return;
    }
    disposable.dispose();
    this._proxyDisposables.delete(webview);
  }
}

export class PanelHost implements vscode.Disposable {
  private readonly _extensionUri: vscode.Uri;
  private readonly _proxy: RpcProxy;
  private readonly _panels = new Map<string, vscode.WebviewPanel>();
  private readonly _proxyDisposables = new Map<vscode.Webview, vscode.Disposable>();

  constructor(extensionUri: vscode.Uri, proxy: RpcProxy) {
    this._extensionUri = extensionUri;
    this._proxy = proxy;
  }

  openPanel(panelId: string): void {
    const existing = this._panels.get(panelId);
    if (existing) {
      existing.reveal();
      return;
    }

    const panel = vscode.window.createWebviewPanel(
      `atopile.${panelId}`,
      `atopile: ${panelId}`,
      vscode.ViewColumn.One,
      {
        enableScripts: true,
        retainContextWhenHidden: true,
        localResourceRoots: getLocalResourceRoots(this._extensionUri),
      },
    );

    configureWebview(this._extensionUri, panel.webview, panelId);
    this._proxyDisposables.set(
      panel.webview,
      this._proxy.registerWebview(panelId, panel.webview),
    );

    panel.onDidDispose(() => {
      this._disposePanel(panelId, panel.webview);
    });

    this._panels.set(panelId, panel);
  }

  dispose(): void {
    for (const panel of this._panels.values()) {
      panel.dispose();
    }
    this._panels.clear();
    for (const disposable of this._proxyDisposables.values()) {
      disposable.dispose();
    }
    this._proxyDisposables.clear();
  }

  private _disposePanel(panelId: string, webview: vscode.Webview): void {
    this._panels.delete(panelId);
    const disposable = this._proxyDisposables.get(webview);
    if (!disposable) {
      return;
    }
    disposable.dispose();
    this._proxyDisposables.delete(webview);
  }
}

function configureWebview(
  extensionUri: vscode.Uri,
  webview: vscode.Webview,
  panelId: string,
): void {
  webview.options = {
    enableScripts: true,
    localResourceRoots: getLocalResourceRoots(extensionUri),
  };
  webview.html = getHtml(extensionUri, webview, panelId);
}

function getHtml(
  extensionUri: vscode.Uri,
  webview: vscode.Webview,
  panelId: string,
): string {
  const distUri = vscode.Uri.joinPath(extensionUri, "webview-dist");
  const scriptUri = webview.asWebviewUri(vscode.Uri.joinPath(distUri, panelId, "index.js"));
  const styleUri = webview.asWebviewUri(vscode.Uri.joinPath(distUri, panelId, "index.css"));
  const logoUri = webview.asWebviewUri(vscode.Uri.joinPath(distUri, "logo.png"));
  const stepViewerWasmUri = webview.asWebviewUri(vscode.Uri.joinPath(distUri, "occt-import-js.wasm"));
  const glbViewerScriptUri = webview.asWebviewUri(vscode.Uri.joinPath(distUri, "model-viewer.min.js"));
  const csp = webview.cspSource;

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
  </script>
  <script type="module" src="${scriptUri}"></script>
</body>
</html>`;
}

function getLocalResourceRoots(extensionUri: vscode.Uri): vscode.Uri[] {
  return [
    extensionUri,
    ...(vscode.workspace.workspaceFolders?.map((folder) => folder.uri) ?? []),
  ];
}
