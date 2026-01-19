/**
 * VS Code Panel Providers - Consolidated webview setup for React panels.
 *
 * This module handles all VS Code webview boilerplate for the sidebar and
 * log viewer panels. Each panel is defined by a configuration object that
 * specifies its behavior.
 */

import * as vscode from 'vscode';
import * as path from 'path';
import { traceInfo, traceError } from '../common/log/logging';
import { buildStateManager, Build, BuildStage, LogEntry } from '../common/buildState';
import { getButtons } from './buttons';
import {
    findWebviewAssets,
    buildWebviewHtml,
    getWebviewLocalResourceRoots,
} from './webview-utils';

/**
 * Configuration for a webview panel.
 */
interface PanelConfig {
    viewType: string;
    webviewName: string;
    title: string;
    onReady: (panel: WebviewPanel) => void;
    onMessage: (panel: WebviewPanel, message: any) => Promise<void>;
    subscriptions?: (panel: WebviewPanel) => vscode.Disposable[];
}

/**
 * Generic webview panel that handles VS Code boilerplate.
 */
class WebviewPanel implements vscode.WebviewViewProvider {
    private _view?: vscode.WebviewView;
    private _disposables: vscode.Disposable[] = [];

    constructor(
        private readonly _extensionUri: vscode.Uri,
        private readonly _config: PanelConfig
    ) {
        // Set up subscriptions if defined
        if (_config.subscriptions) {
            this._disposables = _config.subscriptions(this);
        }
    }

    get viewType(): string {
        return this._config.viewType;
    }

    public resolveWebviewView(
        webviewView: vscode.WebviewView,
        _context: vscode.WebviewViewResolveContext,
        _token: vscode.CancellationToken
    ): void {
        this._view = webviewView;

        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: [
                ...getWebviewLocalResourceRoots(this._extensionUri),
                this._extensionUri, // For logo and other assets
            ],
        };

        const assets = findWebviewAssets(this._extensionUri.fsPath, this._config.webviewName);
        webviewView.webview.html = buildWebviewHtml({
            webview: webviewView.webview,
            assets,
            title: this._config.title,
        });

        webviewView.webview.onDidReceiveMessage(async (message) => {
            if (message.type === 'ready') {
                this._config.onReady(this);
            }
            await this._config.onMessage(this, message);
        });
    }

    /**
     * Send a message to the webview.
     */
    postMessage(type: string, data: any): void {
        if (!this._view) return;
        this._view.webview.postMessage({ type, data });
    }

    /**
     * Get a webview URI for a file path.
     */
    getWebviewUri(filePath: string): string {
        if (!this._view) return '';
        return this._view.webview.asWebviewUri(vscode.Uri.file(filePath)).toString();
    }

    /**
     * Get the extension URI.
     */
    get extensionUri(): vscode.Uri {
        return this._extensionUri;
    }

    dispose(): void {
        this._disposables.forEach(d => d.dispose());
    }
}

// =============================================================================
// Sidebar Panel
// =============================================================================

const sidebarConfig: PanelConfig = {
    viewType: 'atopile.project',
    webviewName: 'sidebar',
    title: 'Atopile',

    onReady: (panel) => {
        // Send extension info
        const extension = vscode.extensions.getExtension('atopile.atopile');
        const version = extension?.packageJSON?.version || 'dev';
        const logoPath = path.join(panel.extensionUri.fsPath, 'ato_logo_256x256.png');
        panel.postMessage('extensionInfo', {
            version,
            logoUri: panel.getWebviewUri(logoPath),
        });

        // Send action buttons
        const buttons = getButtons().map(btn => ({
            id: btn.id,
            label: btn.label,
            icon: btn.icon,
            tooltip: btn.tooltip,
        }));
        panel.postMessage('updateActionButtons', { buttons });

        // Send initial builds
        panel.postMessage('updateBuilds', {
            builds: buildStateManager.getBuilds(),
            isConnected: buildStateManager.isConnected,
        });
    },

    onMessage: async (_panel, message) => {
        switch (message.type) {
            case 'executeCommand':
                await vscode.commands.executeCommand(message.command);
                break;

            case 'selectBuild':
                buildStateManager.selectBuild(message.buildName);
                break;

            case 'selectStage':
                buildStateManager.selectBuild(message.buildName);
                buildStateManager.selectStage(message.stageName);
                await vscode.commands.executeCommand('atopile.logViewer.focus');
                break;
        }
    },

    subscriptions: (panel) => [
        buildStateManager.onDidChangeBuilds(() => {
            panel.postMessage('updateBuilds', {
                builds: buildStateManager.getBuilds(),
                isConnected: buildStateManager.isConnected,
            });
        }),
        buildStateManager.onDidChangeConnection(() => {
            panel.postMessage('updateBuilds', {
                builds: buildStateManager.getBuilds(),
                isConnected: buildStateManager.isConnected,
            });
        }),
    ],
};

// =============================================================================
// Log Viewer Panel
// =============================================================================

// State for log viewer (kept outside config for mutability)
let logViewerState = {
    currentBuild: undefined as Build | undefined,
    currentStage: undefined as BuildStage | undefined,
    logEntries: [] as LogEntry[],
    isLoading: false,
};

let logViewerPanel: WebviewPanel | undefined;

const logViewerConfig: PanelConfig = {
    viewType: 'atopile.logViewer',
    webviewName: 'logViewer',
    title: 'Atopile Logs',

    onReady: (panel) => {
        panel.postMessage('updateLogs', {
            entries: logViewerState.logEntries,
            isLoading: logViewerState.isLoading,
            logFile: logViewerState.currentStage?.log_file || null,
        });
    },

    onMessage: async (_panel, message) => {
        switch (message.type) {
            case 'copyLogPath':
                if (logViewerState.currentStage?.log_file) {
                    await vscode.env.clipboard.writeText(logViewerState.currentStage.log_file);
                    vscode.window.showInformationMessage('Log path copied to clipboard');
                }
                break;
        }
    },

    subscriptions: (panel) => [
        buildStateManager.onDidChangeSelectedStage(async (selection) => {
            if (selection) {
                await loadLogsForStage(panel, selection.build, selection.stage);
            } else {
                logViewerState.currentBuild = undefined;
                logViewerState.currentStage = undefined;
                logViewerState.logEntries = [];
                sendLogUpdate(panel);
            }
        }),
    ],
};

async function loadLogsForStage(panel: WebviewPanel, build: Build, stage: BuildStage): Promise<void> {
    logViewerState.currentBuild = build;
    logViewerState.currentStage = stage;
    logViewerState.isLoading = true;
    sendLogUpdate(panel);

    try {
        logViewerState.logEntries = await buildStateManager.fetchLogEntries(build.display_name, stage);
    } catch (error) {
        traceError(`Failed to load logs: ${error}`);
        logViewerState.logEntries = [];
    } finally {
        logViewerState.isLoading = false;
        sendLogUpdate(panel);
    }
}

function sendLogUpdate(panel: WebviewPanel): void {
    panel.postMessage('updateLogs', {
        entries: logViewerState.logEntries,
        isLoading: logViewerState.isLoading,
        logFile: logViewerState.currentStage?.log_file || null,
    });
}

// =============================================================================
// Activation
// =============================================================================

let sidebarPanel: WebviewPanel | undefined;

export async function activate(context: vscode.ExtensionContext): Promise<void> {
    // Create and register sidebar panel
    sidebarPanel = new WebviewPanel(context.extensionUri, sidebarConfig);
    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider(sidebarConfig.viewType, sidebarPanel)
    );

    // Create and register log viewer panel
    logViewerPanel = new WebviewPanel(context.extensionUri, logViewerConfig);
    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider(logViewerConfig.viewType, logViewerPanel)
    );

    // Start polling for build updates
    buildStateManager.startPolling(500);

    traceInfo('vscode-panels: activated sidebar and log viewer');
}

export function deactivate(): void {
    sidebarPanel?.dispose();
    logViewerPanel?.dispose();
    buildStateManager.stopPolling();
    buildStateManager.dispose();
}
