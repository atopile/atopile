import * as vscode from 'vscode';
import { getLogoUri } from '../common/logo';
import { BaseWebview } from './webview-base';
import { traceInfo } from '../common/log/logging';
import { runAtoCommandInTerminal } from '../common/findbin';
import { getBuildTarget, onBuildTargetChanged } from '../common/target';
import { getPackageDependency } from '../common/manifest';
import * as path from 'path';

const packagesUrl = 'https://packages.atopile.io';

class PackageExplorerWebview extends BaseWebview {
    private themeChangeDisposable?: vscode.Disposable;
    private messageDisposable?: vscode.Disposable;
    private buildTargetChangeDisposable?: vscode.Disposable;
    private fileWatcher?: vscode.FileSystemWatcher;
    private subscribedPackage?: string;

    constructor() {
        super({
            id: 'atopile.packages.panel',
            title: 'Packages',
            column: vscode.ViewColumn.Active,
            iconName: undefined, // Uses custom logo
        });
    }

    private getPackagesUrl(path?: string): string {
        if (path) {
            traceInfo(`getPackagesUrl: ${packagesUrl}/${path}?embedded=true`);
            return `${packagesUrl}/${path}?embedded=true`;
        }
        traceInfo(`getPackagesUrl: ${packagesUrl}?embedded=true`);
        return `${packagesUrl}?embedded=true`;
    }

    protected getHtmlContent(_webview: vscode.Webview, path?: string): string {
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
    <iframe id="packages-iframe" src="${this.getPackagesUrl(path)}"></iframe>
    <script>
        const vscode = acquireVsCodeApi();
        const iframe = document.getElementById('packages-iframe');

        // forward messages from VSCode to iframe
        const downwardEventTypes = ['vscode-theme', 'project-name', 'package-status'];
        window.addEventListener('message', (event) => {
            if (downwardEventTypes.includes(event.data.type)) {
                iframe.contentWindow.postMessage(event.data, '*');
            }
        });

        // forward messages from iframe to VSCode
        const upwardEventTypes = ['request-theme', 'install-package', 'upgrade-package', 'uninstall-package', 'request-project-name', 'subscribe-package', 'copy-text'];
        window.addEventListener('message', (event) => {
            if (event.source === iframe.contentWindow) {
                if (upwardEventTypes.includes(event.data.type)) {
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
            console.log('VSCode theme changed');
            this.sendThemeToWebview();
        });

        // Handle webview theme requests
        this.messageDisposable = this.panel.webview.onDidReceiveMessage(async message => {
            console.log('Received message from webview:', message);
            switch (message.type) {
                case 'request-theme':
                    this.sendThemeToWebview();
                    break;
                case 'install-package':
                    await this.handleAddPackage(message.packageId);
                    break;
                case 'upgrade-package':
                    await this.handleUpgradePackage(message.packageId);
                    break;
                case 'uninstall-package':
                    await this.handleRemovePackage(message.packageId);
                    break;
                case 'request-project-name':
                    this.sendProjectNameToWebview();
                    break;
                case 'subscribe-package':
                    this.subscribeToPackage(message.packageId);
                    break;
                case 'copy-text':
                    if (message.text) {
                        await vscode.env.clipboard.writeText(message.text);
                        vscode.window.showInformationMessage(`Copied to clipboard: ${message.text}`);
                    }
                    break;
            }
        });

        // Send initial project name
        this.sendProjectNameToWebview();

        // Listen for build target changes
        this.buildTargetChangeDisposable = onBuildTargetChanged(() => {
            this.sendProjectNameToWebview();
            this.setupManifestWatcher();
            // Update subscribed package status if any
            if (this.subscribedPackage) {
                this.sendPackageStatus(this.subscribedPackage);
            }
        });

        // Watch for ato.yaml changes
        this.setupManifestWatcher();
    }

    protected onDispose(): void {
        this.themeChangeDisposable?.dispose();
        this.messageDisposable?.dispose();
        this.buildTargetChangeDisposable?.dispose();
        this.fileWatcher?.dispose();
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

    private async _handleManagePackage(command: string, args: string[], packageId: string, statusMessage: string, errorMessage: string): Promise<void> {
        if (!packageId) {
            vscode.window.showErrorMessage('No package identifier provided');
            return;
        }

        const build = getBuildTarget();
        if (!build) {
            vscode.window.showErrorMessage('No build target selected. Please select a build target first.');
            return;
        }

        try {
            const terminal = await runAtoCommandInTerminal(command, build.root, [command, ...args, packageId], false);
            if (terminal) {
                vscode.window.showInformationMessage(statusMessage);
            }
        } catch (error) {
            traceInfo(errorMessage);
        }
    }

    private async handleAddPackage(packageId: string): Promise<void> {
        await this._handleManagePackage('add', [], packageId, `Adding package: ${packageId}`, `Failed to add package: ${packageId}`);
    }

    private async handleUpgradePackage(packageId: string): Promise<void> {
        await this._handleManagePackage('add', ['--upgrade'], packageId, `Upgrading package: ${packageId}`, `Failed to upgrade package: ${packageId}`);
    }

    private async handleRemovePackage(packageId: string): Promise<void> {
        await this._handleManagePackage('remove', [], packageId, `Removing package: ${packageId}`, `Failed to remove package: ${packageId}`);
    }

    private sendProjectNameToWebview(): void {
        if (!this.panel) return;

        const build = getBuildTarget();

        if (build) {
            const projectName = path.basename(build.root);
            this.panel.webview.postMessage({
                type: 'project-name',
                projectName: projectName
            });
        }
    }

    private setupManifestWatcher(): void {
        // Dispose existing watcher if any
        this.fileWatcher?.dispose();

        const build = getBuildTarget();
        if (!build) return;

        // Watch the ato.yaml file for the current build target
        const pattern = new vscode.RelativePattern(build.root, 'ato.yaml');
        this.fileWatcher = vscode.workspace.createFileSystemWatcher(pattern);

        // Send package status when file changes
        this.fileWatcher.onDidChange(() => {
            if (this.subscribedPackage) {
                this.sendPackageStatus(this.subscribedPackage);
            }
        });
        this.fileWatcher.onDidCreate(() => {
            if (this.subscribedPackage) {
                this.sendPackageStatus(this.subscribedPackage);
            }
        });
    }

    private subscribeToPackage(packageId: string): void {
        // Replace existing subscription
        this.subscribedPackage = packageId;

        // Send immediate status update
        this.sendPackageStatus(packageId);
    }

    private async sendPackageStatus(packageId: string): Promise<void> {
        if (!this.panel) return;

        const build = getBuildTarget();
        if (!build) {
            this.panel.webview.postMessage({
                type: 'package-status',
                packageId: packageId,
                installed: false
            });
            return;
        }

        // Get package dependency status
        const atoYamlPath = vscode.Uri.file(path.join(build.root, 'ato.yaml'));
        const dependency = await getPackageDependency(atoYamlPath, packageId);

        this.panel.webview.postMessage({
            type: 'package-status',
            packageId: packageId,
            installed: dependency.installed,
            version: dependency.version
        });
    }
}

let packageExplorer: PackageExplorerWebview | undefined;

export async function openPackageExplorer(packageIdentifier?: string) {
    if (!packageExplorer) {
        packageExplorer = new PackageExplorerWebview();
    }
    await packageExplorer.open(packageIdentifier);
}
