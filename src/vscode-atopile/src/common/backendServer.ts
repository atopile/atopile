/**
 * Backend server lifecycle management for the atopile dashboard.
 *
 * This module manages:
 * - Auto-starting the backend server when extension activates
 * - Restarting the server on user request
 * - Graceful shutdown when extension deactivates
 * - Connection status tracking via WebSocket
 * - Fixed port based on configuration
 */

import * as vscode from 'vscode';
import { traceInfo, traceError, traceVerbose } from './log/logging';
import { getAtoBin, getAtoCommand } from './findbin';
import { appStateManager } from './appState';

const DEFAULT_PORT = 8501;
const DEFAULT_API_URL = `http://localhost:${DEFAULT_PORT}`;
const SERVER_STARTUP_TIMEOUT_MS = 30000; // 30 seconds to wait for server startup
const SERVER_HEALTH_CHECK_INTERVAL_MS = 1000; // Check every second during startup

interface BuildResponse {
    success: boolean;
    message: string;
    build_id?: string;
    targets?: string[];
    build_targets?: { target: string; build_id: string }[];
}

function getApiUrl(): string {
    const config = vscode.workspace.getConfiguration('atopile');
    return config.get<string>('dashboardApiUrl', DEFAULT_API_URL);
}

function getConfiguredPort(): number | undefined {
    try {
        const url = new URL(getApiUrl());
        const port = url.port ? parseInt(url.port, 10) : undefined;
        if (port && !isNaN(port) && port > 0 && port < 65536) {
            return port;
        }
        return undefined;
    } catch {
        return undefined;
    }
}

function buildWsUrlFromApiUrl(apiUrl: string): string | undefined {
    try {
        const url = new URL(apiUrl);
        const wsProtocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
        const port = url.port ? `:${url.port}` : '';
        return `${wsProtocol}//${url.hostname}${port}/ws/state`;
    } catch {
        return undefined;
    }
}

/**
 * Get the workspace root path (first workspace folder).
 */
function getWorkspaceRoot(): string | undefined {
    const folders = vscode.workspace.workspaceFolders;
    return folders && folders.length > 0 ? folders[0].uri.fsPath : undefined;
}

/**
 * Build the WebSocket URL from a port number.
 */
function buildWsUrl(port: number): string {
    return `ws://localhost:${port}/ws/state`;
}

/**
 * Manages the backend server lifecycle.
 */
class BackendServerManager implements vscode.Disposable {
    private _terminal: vscode.Terminal | undefined;
    private _isStarting: boolean = false;
    private _isConnected: boolean = false;
    private _startupPromise: Promise<boolean> | null = null;
    private _disposables: vscode.Disposable[] = [];
    private _statusBarItem: vscode.StatusBarItem | undefined;

    private readonly _onStatusChange = new vscode.EventEmitter<boolean>();
    public readonly onStatusChange = this._onStatusChange.event;

    constructor() {
        // Create status bar item
        this._statusBarItem = vscode.window.createStatusBarItem(
            vscode.StatusBarAlignment.Right,
            100
        );
        this._statusBarItem.command = 'atopile.backendStatus';
        this._statusBarItem.tooltip = 'Click to configure atopile backend';
        this._updateStatusBar();
        this._statusBarItem.show();

        const configuredPort = getConfiguredPort();
        traceInfo(`BackendServer: Init - configuredPort=${configuredPort}, apiUrl=${getApiUrl()}`);

        // Listen for terminal close events to clean up our reference
        this._disposables.push(
            vscode.window.onDidCloseTerminal((terminal) => {
                if (terminal === this._terminal) {
                    traceInfo('BackendServer: Terminal was closed');
                    this._terminal = undefined;
                    this._updateStatusBar();
                }
            })
        );

        // Register the backend status command
        this._disposables.push(
            vscode.commands.registerCommand('atopile.backendStatus', () => {
                this._showBackendStatusMenu();
            })
        );

        this._disposables.push(
            vscode.workspace.onDidChangeConfiguration((event) => {
                if (event.affectsConfiguration('atopile.dashboardApiUrl')) {
                    this._updateStatusBar();
                }
            })
        );

        // Listen to appStateManager for connection state changes
        this._disposables.push(
            appStateManager.onStateChange((state) => {
                this.setConnected(state.isConnected);
            })
        );
    }

    /**
     * Update the status bar item to reflect current connection state.
     */
    private _updateStatusBar(): void {
        if (!this._statusBarItem) return;

        if (this._isStarting) {
            this._statusBarItem.text = '$(sync~spin) ato: Starting...';
            this._statusBarItem.backgroundColor = undefined;
        } else if (this._isConnected) {
            this._statusBarItem.text = `$(check) ato: ${this.port}`;
            this._statusBarItem.backgroundColor = undefined;
        } else {
            this._statusBarItem.text = '$(warning) ato: Disconnected';
            this._statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.warningBackground');
        }
    }

    /**
     * Show the backend status quick pick menu.
     */
    private async _showBackendStatusMenu(): Promise<void> {
        const statusText = this._isConnected
            ? `Connected to port ${this.port}`
            : this._isStarting
                ? 'Starting...'
                : 'Disconnected';

        interface BackendMenuItem extends vscode.QuickPickItem {
            action: string;
        }

        const items: BackendMenuItem[] = [
            {
                label: `$(info) Status: ${statusText}`,
                description: this._isConnected ? this.apiUrl : undefined,
                action: 'none',
            },
            { label: '', kind: vscode.QuickPickItemKind.Separator, action: 'none' },
            {
                label: '$(settings) Configure Backend URL',
                description: 'Open settings for atopile.dashboardApiUrl',
                action: 'open_settings',
            },
            { label: '', kind: vscode.QuickPickItemKind.Separator, action: 'none' },
        ];

        if (this._isConnected) {
            items.push({
                label: '$(debug-restart) Restart Backend Server',
                description: 'Stop and restart the backend server',
                action: 'restart',
            });
        } else {
            items.push({
                label: '$(play) Start Backend Server',
                description: 'Start the backend server in a terminal',
                action: 'start',
            });
        }

        items.push({
            label: '$(terminal) Show Server Terminal',
            description: 'Show the backend server terminal',
            action: 'show_terminal',
        });

        const selected = await vscode.window.showQuickPick(items, {
            placeHolder: 'Backend Server Configuration',
            title: 'atopile Backend',
        });

        if (!selected || selected.action === 'none') return;

        switch (selected.action) {
            case 'open_settings':
                await vscode.commands.executeCommand(
                    'workbench.action.openSettings',
                    'atopile.dashboardApiUrl'
                );
                break;
            case 'restart':
                await this.restartServer();
                break;
            case 'start':
                await this.startServer();
                break;
            case 'show_terminal':
                await this.showTerminal();
                break;
        }
    }

    get isConnected(): boolean {
        return this._isConnected;
    }

    get isStarting(): boolean {
        return this._isStarting;
    }

    get port(): number {
        return getConfiguredPort() || DEFAULT_PORT;
    }

    get apiUrl(): string {
        return getApiUrl();
    }

    get wsUrl(): string {
        return buildWsUrlFromApiUrl(this.apiUrl) || buildWsUrl(this.port);
    }

    /**
     * Update connection status (called from appStateManager when WebSocket connects/disconnects).
     */
    setConnected(connected: boolean): void {
        traceInfo(`BackendServer: setConnected(${connected}) called, current: ${this._isConnected}`);
        if (this._isConnected !== connected) {
            this._isConnected = connected;
            traceInfo(`BackendServer: ${connected ? 'Connected' : 'Disconnected'}, firing onStatusChange`);
            this._onStatusChange.fire(connected);
            this._updateStatusBar();

            // Configure ato binary path on first connection
            if (connected) {
                this._configureAtoBinary();
            }
        }
    }

    /**
     * Start the backend server automatically.
     * Returns true if server started successfully, false otherwise.
     */
    async startServer(): Promise<boolean> {
        // If already starting, wait for that to complete
        if (this._startupPromise) {
            return this._startupPromise;
        }

        // If already connected, nothing to do
        if (this._isConnected) {
            traceVerbose('BackendServer: Already connected, skipping start');
            return true;
        }

        // Check if server is already running on configured URL
        if (await this._checkServerHealth()) {
            traceInfo('BackendServer: Server already running on configured URL');
            return true;
        }

        this._startupPromise = this._doStartServer();
        try {
            return await this._startupPromise;
        } finally {
            this._startupPromise = null;
        }
    }

    private async _doStartServer(): Promise<boolean> {
        this._isStarting = true;
        this._updateStatusBar();

        try {
            const workspaceRoot = getWorkspaceRoot();
            const args = ['serve', 'backend', '--port', String(this.port)];
            if (workspaceRoot) {
                args.push('--workspace', workspaceRoot);
            }

            const command = await getAtoCommand(undefined, args);
            if (!command) {
                traceError('BackendServer: Cannot start server - ato binary not found');
                return false;
            }

            traceInfo(`BackendServer: Starting server: ${command}`);

            // Create terminal (hidden by default for auto-start)
            this._terminal = vscode.window.createTerminal({
                name: 'ato serve',
                hideFromUser: true,
            });
            this._terminal.sendText(command);

            // Wait for server to be ready
            const ready = await this._waitForServerReady();
            if (ready) {
                traceInfo(`BackendServer: Server started successfully on port ${this.port}`);
            } else {
                traceError('BackendServer: Server failed to start within timeout');
                // Show terminal so user can see what went wrong
                this._terminal?.show();
            }

            return ready;
        } catch (error) {
            traceError(`BackendServer: Failed to start server: ${error}`);
            return false;
        } finally {
            this._isStarting = false;
            this._updateStatusBar();
        }
    }

    /**
     * Restart the backend server (e.g., when version changes).
     */
    async restartServer(): Promise<boolean> {
        traceInfo('BackendServer: Restarting server...');

        // Stop existing server
        await this.stopServer();

        // Small delay to let the port be released
        await new Promise(resolve => setTimeout(resolve, 500));

        // Start new server
        return this.startServer();
    }

    /**
     * Stop the backend server.
     */
    async stopServer(): Promise<void> {
        if (this._terminal) {
            traceInfo('BackendServer: Stopping server...');
            // Send Ctrl+C to gracefully stop
            this._terminal.sendText('\x03');
            // Give it a moment to shut down
            await new Promise(resolve => setTimeout(resolve, 500));
            // Dispose the terminal
            this._terminal.dispose();
            this._terminal = undefined;
        }
    }

    /**
     * Show the server terminal (creates one if needed).
     */
    async showTerminal(): Promise<void> {
        const existingTerminal = this._terminal;
        if (existingTerminal) {
            existingTerminal.show();
            return;
        }

        // No terminal but maybe server is running externally
        if (this._isConnected) {
            const choice = await vscode.window.showInformationMessage(
                'Server is running but terminal is not available. Restart server in a new terminal?',
                'Restart Server',
                'Cancel'
            );
            if (choice === 'Restart Server') {
                await this.restartServer();
                this._terminal?.show();
            }
            return;
        }

        // Start server and show terminal
        await this.startServer();
        this._terminal?.show();
    }

    async startOrShowTerminal(): Promise<void> {
        await this.showTerminal();
    }

    /**
     * Check if the server is healthy.
     */
    private async _checkServerHealth(): Promise<boolean> {
        try {
            await appStateManager.sendActionWithResponse('ping', {}, { timeoutMs: 2000 });
            return true;
        } catch {
            return false;
        }
    }

    /**
     * Wait for the server to be ready.
     */
    private async _waitForServerReady(): Promise<boolean> {
        const startTime = Date.now();

        while (Date.now() - startTime < SERVER_STARTUP_TIMEOUT_MS) {
            if (await this._checkServerHealth()) {
                return true;
            }
            await new Promise(resolve => setTimeout(resolve, SERVER_HEALTH_CHECK_INTERVAL_MS));
        }

        return false;
    }

    /**
     * Configure the ato binary path on the server.
     */
    private async _configureAtoBinary(): Promise<void> {
        try {
            const atoBinInfo = await getAtoBin();
            if (atoBinInfo && atoBinInfo.command.length > 0) {
                const atoBinary = atoBinInfo.command[0];
                await appStateManager.sendActionWithResponse(
                    'setAtoBinary',
                    { atoBinary },
                    { timeoutMs: 5000 }
                );
                traceInfo(`BackendServer: Configured ato binary: ${atoBinary} (source: ${atoBinInfo.source})`);
            }
        } catch (error) {
            traceError(`BackendServer: Failed to configure ato binary: ${error}`);
        }
    }

    /**
     * Trigger a build via the API.
     */
    async build(projectPath: string, targets: string[]): Promise<BuildResponse> {
        if (!this._isConnected) {
            throw new Error('Backend server is not connected. Run "ato serve" to start it.');
        }

        try {
            const response = await appStateManager.sendActionWithResponse(
                'build',
                { projectRoot: projectPath, targets },
                { timeoutMs: 10000 }
            );
            const result = response.result || {};
            traceInfo(`Build started: ${result.build_id || 'unknown'}`);
            return result as BuildResponse;
        } catch (error) {
            throw error;
        }
    }

    dispose(): void {
        // Stop the server gracefully
        if (this._terminal) {
            this._terminal.sendText('\x03');
            this._terminal.dispose();
            this._terminal = undefined;
        }

        // Dispose status bar item
        if (this._statusBarItem) {
            this._statusBarItem.dispose();
            this._statusBarItem = undefined;
        }

        this._onStatusChange.dispose();

        for (const disposable of this._disposables) {
            disposable.dispose();
        }
        this._disposables = [];
    }
}

// Singleton instance
export const backendServer = new BackendServerManager();
