import * as vscode from 'vscode';
import { getLogoUri } from '../common/logo';

let _packagesPanel: vscode.WebviewPanel | undefined;

const packagesUrl = 'https://packages.atopile.io';

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
    <iframe id="packages-iframe" src="${packagesUrl}?embedded=true"></iframe>
    <script>
        const vscode = acquireVsCodeApi();
        const iframe = document.getElementById('packages-iframe');

        // forward messages from VSCode to iframe
        window.addEventListener('message', (event) => {
            if (event.data.type === 'vscode-theme') {
                iframe.contentWindow.postMessage(event.data, '*');
            }
        });

        // forward messages from iframe to VSCode
        window.addEventListener('message', (event) => {
            if (event.source === iframe.contentWindow && event.data.type === 'request-theme') {
                vscode.postMessage(event.data);
            }
        });
    </script>
</body>
</html>`;
}

function _getVSCodeTheme(): string {
    const theme = vscode.window.activeColorTheme;
    // VSCode ColorThemeKind: Light = 1, Dark = 2, HighContrast = 3, HighContrastLight = 4
    switch (theme.kind) {
        case vscode.ColorThemeKind.Light:
        case vscode.ColorThemeKind.HighContrastLight:
            return 'light';
        case vscode.ColorThemeKind.Dark:
        case vscode.ColorThemeKind.HighContrast:
        default:
            return 'dark';
    }
}

function _sendThemeToWebview(webview: vscode.Webview) {
    const theme = _getVSCodeTheme();
    webview.postMessage({
        type: 'vscode-theme',
        theme: theme
    });
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

    // send initial theme
    _sendThemeToWebview(_packagesPanel.webview);

    // listen for theme changes
    const themeChangeDisposable = vscode.window.onDidChangeActiveColorTheme(() => {
        console.log('VSCode theme changed');
        if (_packagesPanel) {
            _sendThemeToWebview(_packagesPanel.webview);
        }
    });

    // handle webview theme requests
    const messageDisposable = _packagesPanel.webview.onDidReceiveMessage(message => {
        console.log('Received message from webview:', message);
        if (message.type === 'request-theme' && _packagesPanel) {
            _sendThemeToWebview(_packagesPanel.webview);
        }
    });

    // cleanup
    _packagesPanel.onDidDispose(() => {
        _packagesPanel = undefined;
        themeChangeDisposable.dispose();
        messageDisposable.dispose();
    });
}
