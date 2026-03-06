import * as vscode from "vscode";

const webviewCommandMap = {
  browseFolder: "atopile.browseFolder",
  openFile: "atopile.openFile",
  openKicad: "atopile.openKicad",
} as const satisfies Record<string, string>;

/**
 * Manages all atopile webviews — both the sidebar panel and
 * editor-tab panels. Shares a single HTML template across both.
 */
export class WebviewManager implements vscode.WebviewViewProvider {
  public static readonly sidebarViewId = "atopile.sidebarView";
  public static readonly logsViewId = "atopile.logsView";

  private _sidebarView?: vscode.WebviewView;
  private _logsView?: vscode.WebviewView;
  private _panels = new Map<string, vscode.WebviewPanel>();
  private readonly _extensionUri: vscode.Uri;
  private readonly _hubPort: number;
  private readonly _coreServerPort: number;
  private readonly _output: vscode.OutputChannel;

  constructor(extensionUri: vscode.Uri, hubPort: number, coreServerPort: number, output: vscode.OutputChannel) {
    this._extensionUri = extensionUri;
    this._hubPort = hubPort;
    this._coreServerPort = coreServerPort;
    this._output = output;
  }

  /** Called by VS Code when a registered webview view becomes visible. */
  resolveWebviewView(
    webviewView: vscode.WebviewView,
    _context: vscode.WebviewViewResolveContext,
    _token: vscode.CancellationToken
  ): void {
    webviewView.webview.options = {
      enableScripts: true,
      localResourceRoots: [this._extensionUri],
    };

    if (webviewView.viewType === WebviewManager.logsViewId) {
      this._logsView = webviewView;
      webviewView.webview.html = this._getHtml(webviewView.webview, "panel-logs");
    } else {
      this._sidebarView = webviewView;
      webviewView.webview.html = this._getHtml(webviewView.webview, "sidebar");
    }

    this._registerMessageHandler(webviewView.webview);
  }

  /** Open or reveal an editor-tab webview panel. */
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
        localResourceRoots: [this._extensionUri],
      }
    );

    panel.webview.html = this._getHtml(panel.webview, panelId);
    this._registerMessageHandler(panel.webview);

    panel.onDidDispose(() => {
      this._panels.delete(panelId);
    });

    this._panels.set(panelId, panel);
  }

  // --- Private ---

  private _registerMessageHandler(webview: vscode.Webview): void {
    webview.onDidReceiveMessage(async (msg) => {
      const requestId = typeof msg.requestId === "string" ? msg.requestId : undefined;

      if (msg.type === "log" && typeof msg.message === "string") {
        const prefix = msg.level === "error" ? "[Webview] ERR" : msg.level === "warn" ? "[Webview] WARN" : "[Webview]";
        this._output.appendLine(`${prefix} ${msg.message}`);
        return;
      }

      if (msg.type === "openPanel" && typeof msg.panelId === "string") {
        this.openPanel(msg.panelId);
        return;
      }

      const command = typeof msg.type === "string" ? webviewCommandMap[msg.type as keyof typeof webviewCommandMap] : undefined;
      if (command) {
        const { requestId: _, type: __, ...args } = msg as Record<string, unknown>;
        try {
          const result = await vscode.commands.executeCommand(command, args);
          if (requestId) {
            void webview.postMessage({
              type: "response",
              requestId,
              ok: true,
              result,
            });
          }
        } catch (err) {
          if (requestId) {
            void webview.postMessage({
              type: "response",
              requestId,
              ok: false,
              error: err instanceof Error ? err.message : String(err),
            });
          }
        }
        return;
      }

      if (requestId) {
        void webview.postMessage({
          type: "response",
          requestId,
          ok: false,
          error: `Unsupported request type: ${String(msg.type)}`,
        });
      }
    });
  }

  private _getHtml(webview: vscode.Webview, panelId: string): string {
    const distUri = vscode.Uri.joinPath(this._extensionUri, "webview-dist");
    const scriptUri = webview.asWebviewUri(vscode.Uri.joinPath(distUri, panelId, "index.js"));
    const styleUri = webview.asWebviewUri(vscode.Uri.joinPath(distUri, panelId, "index.css"));
    const logoUri = webview.asWebviewUri(vscode.Uri.joinPath(distUri, "logo.png"));
    const hubPort = this._hubPort;
    const corePort = this._coreServerPort;
    const csp = webview.cspSource;

    const extraGlobals = panelId === "panel-logs"
      ? `\n    window.__ATOPILE_CORE_SERVER_PORT__ = ${corePort};`
      : "";

    return /* html */ `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta http-equiv="Content-Security-Policy"
    content="default-src 'none';
      script-src 'unsafe-inline' ${csp};
      style-src 'unsafe-inline' ${csp};
      img-src ${csp} data:;
      font-src ${csp};
      connect-src ws://localhost:*;" />
  <link rel="stylesheet" href="${styleUri}" />
  <title>atopile</title>
</head>
<body>
  <div id="root"></div>
  <script>
    window.__ATOPILE_HUB_PORT__ = ${hubPort};
    window.__ATOPILE_PANEL_ID__ = "${panelId}";
    window.__ATOPILE_LOGO_URL__ = "${logoUri}";${extraGlobals}
  </script>
  <script type="module" src="${scriptUri}"></script>
</body>
</html>`;
  }
}
