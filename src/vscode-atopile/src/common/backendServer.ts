/**
 * Backend server lifecycle management for the atopile dashboard.
 *
 * This module manages:
 * - Auto-starting the backend server when extension activates
 * - Restarting the server when atopile version changes
 * - Graceful shutdown when extension deactivates
 * - Connection status tracking via WebSocket
 */

import * as vscode from 'vscode';
import axios from 'axios';
import { traceInfo, traceError, traceVerbose } from './log/logging';
import { getAtoBin, getAtoCommand } from './findbin';

const DEFAULT_API_URL = 'http://localhost:8501';
const SERVER_STARTUP_TIMEOUT_MS = 30000; // 30 seconds to wait for server startup
const SERVER_HEALTH_CHECK_INTERVAL_MS = 1000; // Check every second during startup

interface BuildRequest {
    project_path: string;
    targets: string[];
}

interface BuildResponse {
    build_id: string;
    status: string;
    project_path: string;
    targets: string[];
}

function getApiUrl(): string {
    const config = vscode.workspace.getConfiguration('atopile');
    return config.get<string>('dashboardApiUrl', DEFAULT_API_URL);
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

    private readonly _onStatusChange = new vscode.EventEmitter<boolean>();
    public readonly onStatusChange = this._onStatusChange.event;

    constructor() {
        // Listen for terminal close events to clean up our reference
        this._disposables.push(
            vscode.window.onDidCloseTerminal((terminal) => {
                if (terminal === this._terminal) {
                    traceInfo('BackendServer: Terminal was closed');
                    this._terminal = undefined;
                }
            })
        );
    }

    get isConnected(): boolean {
        return this._isConnected;
    }

    get isStarting(): boolean {
        return this._isStarting;
    }

    get apiUrl(): string {
        return getApiUrl();
    }

    /**
     * Update connection status (called from appStateManager when WebSocket connects/disconnects).
     */
    setConnected(connected: boolean): void {
        if (this._isConnected !== connected) {
            this._isConnected = connected;
            traceInfo(`BackendServer: ${connected ? 'Connected' : 'Disconnected'}`);
            this._onStatusChange.fire(connected);

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

        // Check if server is already running externally
        if (await this._checkServerHealth()) {
            traceInfo('BackendServer: Server already running externally');
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

        try {
            const command = await getAtoCommand(undefined, ['serve', 'start', '--force']);
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
                traceInfo('BackendServer: Server started successfully');
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
        if (this._terminal) {
            this._terminal.show();
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

    /**
     * Check if the server is healthy.
     */
    private async _checkServerHealth(): Promise<boolean> {
        try {
            const response = await axios.get(`${this.apiUrl}/health`, { timeout: 2000 });
            return response.status === 200;
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
                await axios.post(`${this.apiUrl}/api/config`, null, {
                    params: { ato_binary: atoBinary },
                    timeout: 5000,
                });
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

        const request: BuildRequest = {
            project_path: projectPath,
            targets: targets,
        };

        try {
            const response = await axios.post<BuildResponse>(
                `${this.apiUrl}/api/build`,
                request,
                { timeout: 10000 }
            );
            traceInfo(`Build started: ${response.data.build_id}`);
            return response.data;
        } catch (error) {
            if (axios.isAxiosError(error)) {
                const detail = error.response?.data?.detail || error.message;
                throw new Error(`Build failed: ${detail}`);
            }
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

        this._onStatusChange.dispose();

        for (const disposable of this._disposables) {
            disposable.dispose();
        }
        this._disposables = [];
    }
}

// Singleton instance
export const backendServer = new BackendServerManager();
