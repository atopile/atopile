import * as vscode from 'vscode';
import { getLogoUri } from '../common/logo';
import { BaseWebview } from './webview-base';

const packagesUrl = 'https://packages.atopile.io';

class PackageExplorerWebview extends BaseWebview {
    private themeChangeDisposable?: vscode.Disposable;
    private messageDisposable?: vscode.Disposable;

    constructor() {
        super({
            id: 'atopile.packages.panel',
            title: 'Packages',
            column: vscode.ViewColumn.Active,
            iconName: undefined, // Uses custom logo
        });
    }

    protected getHtmlContent(_webview: vscode.Webview): string {
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

    protected setupPanel(): void {
        if (!this.panel) return;

        // Set custom icon
        this.panel.iconPath = getLogoUri();

        // Send initial theme
        this.sendThemeToWebview();

        // Listen for theme changes
        this.themeChangeDisposable = vscode.window.onDidChangeActiveColorTheme(() => {
            console.log('VSCode theme changed');
            this.sendThemeToWebview();
        });

        // Handle webview theme requests
        this.messageDisposable = this.panel.webview.onDidReceiveMessage(message => {
            console.log('Received message from webview:', message);
            if (message.type === 'request-theme') {
                this.sendThemeToWebview();
            }
        });
    }

    protected onDispose(): void {
        this.themeChangeDisposable?.dispose();
        this.messageDisposable?.dispose();
    }

    private sendThemeToWebview(): void {
        if (!this.panel) return;

        const theme = this.getVSCodeTheme();
        this.panel.webview.postMessage({
            type: 'vscode-theme',
            theme: theme
        });
    }

    private getVSCodeTheme(): string {
        const theme = vscode.window.activeColorTheme;
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
}

let packageExplorer: PackageExplorerWebview | undefined;

export async function openPackageExplorer() {
    if (!packageExplorer) {
        packageExplorer = new PackageExplorerWebview();
    }
    await packageExplorer.open();
}
