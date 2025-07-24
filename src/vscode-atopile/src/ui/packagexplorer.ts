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
        window.addEventListener('message', (event) => {
            if (event.data.type === 'vscode-theme' || event.data.type === 'project-name' || event.data.type === 'package-status') {
                iframe.contentWindow.postMessage(event.data, '*');
            }
        });

        // forward messages from iframe to VSCode
        window.addEventListener('message', (event) => {
            if (event.source === iframe.contentWindow) {
                if (event.data.type === 'request-theme' || event.data.type === 'install-package' || event.data.type === 'update-package' || event.data.type === 'uninstall-package' || event.data.type === 'request-project-name' || event.data.type === 'subscribe-package') {
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
            if (message.type === 'request-theme') {
                this.sendThemeToWebview();
            } else if (message.type === 'install-package') {
                await this.handlePackageInstall(message.packageId);
            } else if (message.type === 'update-package') {
                await this.handlePackageUpdate(message.packageId);
            } else if (message.type === 'uninstall-package') {
                await this.handlePackageUninstall(message.packageId);
            } else if (message.type === 'request-project-name') {
                this.sendProjectNameToWebview();
            } else if (message.type === 'subscribe-package') {
                this.subscribeToPackage(message.packageId);
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

    private async handlePackageInstall(packageId: string): Promise<void> {
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
            // not hidden from user so CLI-generated import statement is visible
            const terminal = await runAtoCommandInTerminal('add', build.root, ['add', packageId], false);
            if (terminal) {
                vscode.window.showInformationMessage(`Adding package: ${packageId}`);
            }
        } catch (error) {
            traceInfo(`Failed to install package: ${error}`);
        }
    }

    private async handlePackageUpdate(packageId: string): Promise<void> {
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
            // not hidden from user so CLI-generated output is visible
            const terminal = await runAtoCommandInTerminal('add', build.root, ['add', '--upgrade', packageId], false);
            if (terminal) {
                vscode.window.showInformationMessage(`Updating package: ${packageId}`);
            }
        } catch (error) {
            traceInfo(`Failed to update package: ${error}`);
        }
    }

    private async handlePackageUninstall(packageId: string): Promise<void> {
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
            // not hidden from user so they can see the removal
            const terminal = await runAtoCommandInTerminal('remove', build.root, ['remove', packageId], false);
            if (terminal) {
                vscode.window.showInformationMessage(`Removing package: ${packageId}`);
            }
        } catch (error) {
            traceInfo(`Failed to remove package: ${error}`);
        }
    }

    private sendProjectNameToWebview(): void {
        if (!this.panel) return;

        const build = getBuildTarget();
        const projectName = build ? path.basename(build.root) : 'No Project';

        this.panel.webview.postMessage({
            type: 'project-name',
            projectName: projectName
        });
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
