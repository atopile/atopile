import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { getLogoUri } from '../common/logo';
import { BaseWebview } from './webview-base';
import { traceInfo } from '../common/log/logging';
import { getExtension } from '../common/vscodeapi';

/**
 * Get the dashboard API URL from settings.
 */
function getDashboardApiUrl(): string {
    const config = vscode.workspace.getConfiguration('atopile');
    return config.get<string>('dashboardApiUrl', 'http://localhost:8501');
}

/**
 * Get the path to the dashboard web dist directory.
 *
 * Checks in order:
 * 1. Bundled with extension (production) - resources/dashboard
 * 2. Development mode - dashboard/dist (relative to extension)
 */
function getDashboardDistPath(): string | null {
    const extensionPath = getExtension().extensionUri.fsPath;
    traceInfo(`Dashboard: extension path = ${extensionPath}`);

    // 1. Check if bundled with extension (production)
    const bundledPath = path.join(extensionPath, 'resources', 'dashboard');
    const bundledIndex = path.join(bundledPath, 'index.html');
    traceInfo(`Dashboard: checking bundled path = ${bundledIndex}`);
    if (fs.existsSync(bundledIndex)) {
        traceInfo(`Dashboard: found bundled dist at ${bundledPath}`);
        return bundledPath;
    }

    // 2. Development mode: dashboard/dist relative to extension
    const devPath = path.join(extensionPath, 'dashboard', 'dist');
    const devIndex = path.join(devPath, 'index.html');
    traceInfo(`Dashboard: checking dev path = ${devIndex}`);
    if (fs.existsSync(devIndex)) {
        traceInfo(`Dashboard: found dev dist at ${devPath}`);
        return devPath;
    }

    traceInfo(`Dashboard: dist not found in any location`);
    return null;
}

/**
 * Find the main JS and CSS files from the dashboard dist.
 * Vite outputs files with content hashes like: index-ABC123.js
 */
function findAssets(distPath: string): { js: string | null; css: string | null } {
    const assetsDir = path.join(distPath, 'assets');
    if (!fs.existsSync(assetsDir)) {
        return { js: null, css: null };
    }

    const files = fs.readdirSync(assetsDir);
    const js = files.find(f => f.endsWith('.js') && f.startsWith('index-'));
    const css = files.find(f => f.endsWith('.css') && f.startsWith('index-'));

    return {
        js: js ? path.join(assetsDir, js) : null,
        css: css ? path.join(assetsDir, css) : null,
    };
}

class DashboardWebview extends BaseWebview {
    private themeChangeDisposable?: vscode.Disposable;
    private apiUrl?: string;

    constructor() {
        super({
            id: 'atopile.dashboard.panel',
            title: 'Build Dashboard',
            column: vscode.ViewColumn.Active,
            iconName: undefined, // Uses custom logo
        });
    }

    protected getLocalResourceRoots(): vscode.Uri[] {
        const roots = super.getLocalResourceRoots();

        // Add dashboard dist directory
        const distPath = getDashboardDistPath();
        if (distPath) {
            roots.push(vscode.Uri.file(distPath));
        }

        return roots;
    }

    protected getHtmlContent(webview: vscode.Webview, _urlPath?: string): string {
        const distPath = getDashboardDistPath();
        if (!distPath) {
            return this.getDashboardNotBuiltHtml();
        }

        const assets = findAssets(distPath);
        if (!assets.js) {
            return this.getDashboardNotBuiltHtml();
        }

        // Get webview URIs for assets
        const jsUri = webview.asWebviewUri(vscode.Uri.file(assets.js));
        const cssUri = assets.css ? webview.asWebviewUri(vscode.Uri.file(assets.css)) : null;

        // Get API URL from settings
        const apiUrl = this.apiUrl || getDashboardApiUrl();

        // Generate nonce for Content Security Policy
        const nonce = getNonce();

        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Security-Policy" content="
        default-src 'none';
        style-src ${webview.cspSource} 'unsafe-inline';
        script-src 'nonce-${nonce}';
        connect-src ${apiUrl};
        img-src ${webview.cspSource} data:;
        font-src ${webview.cspSource};
    ">
    <title>atopile Build Dashboard</title>
    ${cssUri ? `<link rel="stylesheet" href="${cssUri}">` : ''}
    <style>
        html, body, #root {
            margin: 0;
            padding: 0;
            width: 100%;
            height: 100%;
        }
    </style>
</head>
<body>
    <div id="root"></div>
    <script nonce="${nonce}">
        // Set API URL before React loads
        window.__ATO_API_URL__ = '${apiUrl}';
    </script>
    <script nonce="${nonce}" type="module" src="${jsUri}"></script>
    <script nonce="${nonce}">
        // Set up VS Code API for messaging
        const vscode = acquireVsCodeApi();

        // Listen for theme changes from VS Code
        window.addEventListener('message', (event) => {
            if (event.data.type === 'vscode-theme') {
                // Could dispatch to React app if needed
                document.body.dataset.theme = event.data.theme;
            }
        });
    </script>
</body>
</html>`;
    }

    private getDashboardNotBuiltHtml(): string {
        return `<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100vh;
            margin: 0;
            background: var(--vscode-editor-background);
            color: var(--vscode-foreground);
            font-family: var(--vscode-font-family);
        }
        .container {
            text-align: center;
            padding: 2rem;
        }
        h1 { margin-bottom: 1rem; }
        code {
            background: var(--vscode-textCodeBlock-background);
            padding: 0.2rem 0.4rem;
            border-radius: 3px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Dashboard Not Built</h1>
        <p>The dashboard web app has not been built.</p>
        <p>Run <code>npm run build:dashboard</code> in</p>
        <p><code>src/vscode-atopile</code></p>
    </div>
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

        // Handle webview messages
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

    public async openWithUrl(apiUrl: string): Promise<void> {
        this.apiUrl = apiUrl;
        traceInfo(`Opening dashboard with API URL: ${apiUrl}`);
        await this.open();
    }
}

function getNonce(): string {
    let text = '';
    const possible = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    for (let i = 0; i < 32; i++) {
        text += possible.charAt(Math.floor(Math.random() * possible.length));
    }
    return text;
}

let dashboardWebview: DashboardWebview | undefined;

export async function openDashboard(apiUrl?: string): Promise<void> {
    if (!dashboardWebview) {
        dashboardWebview = new DashboardWebview();
    }

    const url = apiUrl || getDashboardApiUrl();
    await dashboardWebview.openWithUrl(url);
}
