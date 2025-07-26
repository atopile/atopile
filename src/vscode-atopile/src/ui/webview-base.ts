import * as vscode from 'vscode';
import * as path from 'path';
import { getResourcesPath } from '../common/resources';
import { buildHtml } from './html-builder';

export interface WebviewConfig {
    id: string;
    title: string;
    column?: vscode.ViewColumn;
    iconName?: string;
    enableScripts?: boolean;
    localResourceRoots?: vscode.Uri[];
}

export abstract class BaseWebview {
    protected panel: vscode.WebviewPanel | undefined;
    protected config: WebviewConfig;

    constructor(config: WebviewConfig) {
        this.config = config;
    }

    public isOpen(): boolean {
        return this.panel !== undefined;
    }

    public reveal(): void {
        this.panel?.reveal();
    }

    public dispose(): void {
        this.panel?.dispose();
        this.panel = undefined;
    }

    protected abstract getHtmlContent(webview: vscode.Webview, path?: string): string;

    public async open(urlPath?: string): Promise<void> {
        const localResourceRoots = this.getLocalResourceRoots();

        if (!this.panel) {
            this.panel = vscode.window.createWebviewPanel(
                this.config.id,
                this.config.title,
                this.config.column ?? vscode.ViewColumn.Beside,
                {
                    enableScripts: this.config.enableScripts ?? true,
                    localResourceRoots,
                }
            );

            this.panel.onDidDispose(() => {
                this.panel = undefined;
                this.onDispose();
            });

            if (this.config.iconName) {
                const iconPath = vscode.Uri.file(path.join(getResourcesPath(), this.config.iconName));
                this.panel.iconPath = {
                    light: iconPath,
                    dark: iconPath,
                };
            }

            this.setupPanel();
        }

        this.panel.webview.options = { ...this.panel.webview.options, localResourceRoots };
        this.panel.webview.html = this.getHtmlContent(this.panel.webview, urlPath);
        this.panel.reveal();
    }

    protected getLocalResourceRoots(): vscode.Uri[] {
        return [
            vscode.Uri.file(getResourcesPath()),
            ...(vscode.workspace.workspaceFolders?.map((f) => f.uri) ?? []),
        ];
    }

    protected setupPanel(): void {
        // Override in subclasses if needed
    }

    protected onDispose(): void {
        // Override in subclasses if needed
    }

    protected getMissingResourceHtml(resourceType: string): string {
        return buildHtml({
            title: `No ${resourceType}`,
            styles: `
                body {
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    background: var(--vscode-editor-background);
                    color: var(--vscode-descriptionForeground);
                    font-family: var(--vscode-font-family);
                }
                .msg {
                    font-size: 0.9rem;
                    opacity: 0.8;
                }
            `,
            body: `<div class="msg">Build target does not have a valid ${resourceType.toLowerCase()}.</div>`,
        });
    }

    protected getWebviewUri(webview: vscode.Webview, filePath: string, cacheBuster: boolean = true): vscode.Uri {
        let uri = webview.asWebviewUri(vscode.Uri.file(filePath));
        if (cacheBuster) {
            const cb = Date.now();
            uri = vscode.Uri.parse(`${uri.toString()}?cb=${cb}`);
        }
        return uri;
    }
}