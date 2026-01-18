import * as vscode from 'vscode';
import { getLogoUri } from '../common/logo';
import { BaseWebview } from './webview-base';
import { traceInfo } from '../common/log/logging';

class DashboardWebview extends BaseWebview {
    private themeChangeDisposable?: vscode.Disposable;
    private currentUrl?: string;

    constructor() {
        super({
            id: 'atopile.dashboard.panel',
            title: 'Build Dashboard',
            column: vscode.ViewColumn.Beside,
            iconName: undefined, // Uses custom logo
        });
    }

    protected getHtmlContent(_webview: vscode.Webview, url?: string): string {
        const dashboardUrl = url || this.currentUrl || '';
        if (!dashboardUrl) {
            return this.getMissingResourceHtml('Dashboard URL');
        }

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
    <iframe id="dashboard-iframe" src="${dashboardUrl}"></iframe>
    <script>
        const vscode = acquireVsCodeApi();
        const iframe = document.getElementById('dashboard-iframe');

        // Forward theme messages from VSCode to iframe
        window.addEventListener('message', (event) => {
            if (event.data.type === 'vscode-theme') {
                iframe.contentWindow.postMessage(event.data, '*');
            }
        });

        // Forward theme request messages from iframe to VSCode
        window.addEventListener('message', (event) => {
            if (event.source === iframe.contentWindow) {
                if (event.data.type === 'request-theme') {
                    vscode.postMessage(event.data);
                }
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
            this.sendThemeToWebview();
        });

        // Handle webview theme requests
        this.panel.webview.onDidReceiveMessage(message => {
            if (message.type === 'request-theme') {
                this.sendThemeToWebview();
            }
        });
    }

    protected onDispose(): void {
        this.themeChangeDisposable?.dispose();
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

    public async openWithUrl(url: string): Promise<void> {
        this.currentUrl = url;
        traceInfo(`Opening dashboard with URL: ${url}`);
        await this.open(url);
    }
}

let dashboardWebview: DashboardWebview | undefined;

export async function openDashboard(url: string): Promise<void> {
    if (!dashboardWebview) {
        dashboardWebview = new DashboardWebview();
    }
    await dashboardWebview.openWithUrl(url);
}
