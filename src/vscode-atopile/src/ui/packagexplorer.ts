import * as vscode from 'vscode';
import { getLogoUri } from '../common/logo';

let _packagesPanel: vscode.WebviewPanel | undefined;

function _getPackageExplorerHTML(): string {
    return `<!DOCTYPE html>
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
    <iframe src="https://packages.atopile.io"></iframe>
</body>
</html>`;
}

export async function openPackageExplorer() {
    if (_packagesPanel) {
        _packagesPanel.reveal();
        return;
    }

    // create panel
    _packagesPanel = vscode.window.createWebviewPanel('atopile.packages.panel', 'Packages', vscode.ViewColumn.Active, {
        enableScripts: true,
    });

    _packagesPanel.webview.html = _getPackageExplorerHTML();
    _packagesPanel.iconPath = getLogoUri();

    // cleanup
    _packagesPanel.onDidDispose(() => {
        _packagesPanel = undefined;
    });
}
