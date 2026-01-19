/**
 * Log Viewer Panel - WebviewViewProvider for the React-based log viewer.
 *
 * Displays logs for the selected build stage with level filtering,
 * expandable tracebacks, and auto-scroll functionality.
 */

import * as vscode from 'vscode';
import { traceInfo, traceError } from '../common/log/logging';
import {
    buildStateManager,
    Build,
    BuildStage,
    LogEntry,
} from '../common/buildState';
import {
    findWebviewAssets,
    buildWebviewHtml,
    getWebviewLocalResourceRoots,
} from './webview-utils';

export class LogViewerPanelProvider implements vscode.WebviewViewProvider {
    public static readonly viewType = 'atopile.logViewer';

    private _view?: vscode.WebviewView;
    private _currentBuild?: Build;
    private _currentStage?: BuildStage;
    private _logEntries: LogEntry[] = [];
    private _isLoading: boolean = false;

    constructor(private readonly _extensionUri: vscode.Uri) {
        // Subscribe to stage selection changes
        buildStateManager.onDidChangeSelectedStage(async (selection) => {
            if (selection) {
                await this.loadLogsForStage(selection.build, selection.stage);
            } else {
                this._currentBuild = undefined;
                this._currentStage = undefined;
                this._logEntries = [];
                this.updateLogs();
            }
        });
    }

    public resolveWebviewView(
        webviewView: vscode.WebviewView,
        _context: vscode.WebviewViewResolveContext,
        _token: vscode.CancellationToken
    ): void {
        this._view = webviewView;

        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: getWebviewLocalResourceRoots(this._extensionUri),
        };

        const assets = findWebviewAssets(this._extensionUri.fsPath, 'logViewer');
        webviewView.webview.html = buildWebviewHtml({
            webview: webviewView.webview,
            assets,
            title: 'Atopile Logs',
        });

        // Handle messages from the webview
        webviewView.webview.onDidReceiveMessage(async (message) => {
            switch (message.type) {
                case 'ready':
                    this.updateLogs();
                    break;

                case 'copyLogPath':
                    if (this._currentStage?.log_file) {
                        await vscode.env.clipboard.writeText(this._currentStage.log_file);
                        vscode.window.showInformationMessage('Log path copied to clipboard');
                    }
                    break;

                case 'toggleLevel':
                    // Level filtering is handled client-side in the React component
                    break;
            }
        });
    }

    private async loadLogsForStage(build: Build, stage: BuildStage): Promise<void> {
        this._currentBuild = build;
        this._currentStage = stage;
        this._isLoading = true;
        this.updateLogs();

        try {
            this._logEntries = await buildStateManager.fetchLogEntries(build.display_name, stage);
            this._isLoading = false;
            this.updateLogs();
        } catch (error) {
            traceError(`Failed to load logs: ${error}`);
            this._logEntries = [];
            this._isLoading = false;
            this.updateLogs();
        }
    }

    private updateLogs(): void {
        if (!this._view) return;

        this._view.webview.postMessage({
            type: 'updateLogs',
            data: {
                entries: this._logEntries,
                isLoading: this._isLoading,
                logFile: this._currentStage?.log_file || null,
            },
        });
    }
}

// Exported activate/deactivate
export async function activate(context: vscode.ExtensionContext) {
    const provider = new LogViewerPanelProvider(context.extensionUri);

    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider(LogViewerPanelProvider.viewType, provider)
    );

    traceInfo('LogViewerPanel: activated');
}

export function deactivate() {
    // Nothing to clean up
}
