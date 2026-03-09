import * as vscode from 'vscode';
import { BaseWebview } from './webview-base';
import { traceInfo } from '../common/log/logging';
import { runAtoCommandInTerminal } from '../common/findbin';
import { getBuildTarget, onBuildTargetChanged } from '../common/target';
import { backendServer } from '../common/backendServer';
import * as path from 'path';
import { renderTemplate } from '../common/template';
import { getNonce } from '../common/webview';
// @ts-ignore
import * as _packageExplorerTemplateText from './packagexplorer.hbs';

const packageExplorerTemplateText: string = (_packageExplorerTemplateText as any).default || _packageExplorerTemplateText;

const packagesUrl = 'https://packages.atopile.io';

class PackageExplorerWebview extends BaseWebview {
    private themeChangeDisposable?: vscode.Disposable;
    private messageDisposable?: vscode.Disposable;
    private buildTargetChangeDisposable?: vscode.Disposable;
    private backendEventDisposable?: vscode.Disposable;
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
        const nonce = getNonce();
        const csp = [
            "default-src 'none'",
            `script-src 'nonce-${nonce}'`,
            "style-src 'unsafe-inline'",
            `frame-src ${packagesUrl}`,
            `connect-src ${packagesUrl}`,
        ].join('; ');

        return renderTemplate(packageExplorerTemplateText, {
            csp,
            nonce,
            packagesUrl: this.getPackagesUrl(path),
        });
    }

    protected setupPanel(): void {
        if (!this.panel) return;

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
            // Update subscribed package status if any
            if (this.subscribedPackage) {
                void this.sendPackageStatus(this.subscribedPackage);
            }
        });
        this.backendEventDisposable = backendServer.onBackendEvent((message) => {
            if (message.event === 'backend_socket_connected' || message.event === 'packages_changed') {
                if (this.subscribedPackage) {
                    void this.sendPackageStatus(this.subscribedPackage);
                }
            }
        });
    }

    protected onDispose(): void {
        this.themeChangeDisposable?.dispose();
        this.messageDisposable?.dispose();
        this.buildTargetChangeDisposable?.dispose();
        this.backendEventDisposable?.dispose();
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

    private subscribeToPackage(packageId: string): void {
        // Replace existing subscription
        this.subscribedPackage = packageId;

        // Send immediate status update
        void this.sendPackageStatus(packageId);
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

        let installed = false;
        let version: string | undefined;
        try {
            const response = await backendServer.sendBackendActionWithResponse(
                'getPackageDependencyStatus',
                {
                    projectRoot: build.root,
                    packageId,
                },
            );
            const result = response.result;
            installed = Boolean(result?.success && result.installed);
            version = typeof result?.version === 'string' ? result.version : undefined;
        } catch {
            installed = false;
            version = undefined;
        }

        this.panel.webview.postMessage({
            type: 'package-status',
            packageId: packageId,
            installed,
            version,
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
