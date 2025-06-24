import * as vscode from 'vscode';

export class PackageViewerProvider implements vscode.WebviewViewProvider {
    public static readonly viewType = 'atopile.packages';

    public resolveWebviewView(
        webviewView: vscode.WebviewView,
        _context: vscode.WebviewViewResolveContext,
        _token: vscode.CancellationToken
    ) {
        webviewView.webview.options = {
            enableScripts: true
        };

        webviewView.webview.html = this._getHtmlForWebview();
    }

    private _getHtmlForWebview(): string {
        return `
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    body, html {
                        margin: 0;
                        padding: 0;
                        width: 100%;
                        height: 100%;
                        overflow: hidden;
                    }
                    iframe {
                        width: 100%;
                        height: 100%;
                        border: none;
                    }
                </style>
            </head>
            <body>
                <iframe src="https://packages.atopile.io/packages"></iframe>
            </body>
            </html>
        `;
    }
}

// Exported activate/deactivate so ui.ts can re-use this module uniformly
export function activate(context: vscode.ExtensionContext) {
    activatePackagesView(context);
}

export function deactivate() {
    // Nothing to clean up currently
}

let isPackageViewRegistered = false;

export function activatePackagesView(context: vscode.ExtensionContext) {
    if (isPackageViewRegistered) {
        return; // Prevent double-registration which causes extension activation failures
    }
    isPackageViewRegistered = true;
    const provider = new PackageViewerProvider();
    context.subscriptions.push(
        vscode.commands.registerCommand('atopile.packages.focus', async () => {
            await vscode.commands.executeCommand('workbench.view.extension.atopile-packages');
        }),
        vscode.window.registerWebviewViewProvider(
            PackageViewerProvider.viewType,
            provider
        )
    );
}