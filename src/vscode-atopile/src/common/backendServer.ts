/**
 * Backend server lifecycle management for the atopile dashboard.
 *
 * This module manages:
 * - Auto-starting the backend server when extension activates
 * - Restarting the server when atopile version changes
 * - Graceful shutdown when extension deactivates
 * - Connection status tracking via WebSocket
 * - Port discovery via port file (.atopile/.server_port)
 */

import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import { traceInfo, traceError, traceVerbose } from './log/logging';
import { getAtoBin, getAtoCommand } from './findbin';
import { appStateManager, setServerPort } from './appState';

const DEFAULT_PORT = 8501;
const DEFAULT_API_URL = `http://localhost:${DEFAULT_PORT}`;
const SERVER_STARTUP_TIMEOUT_MS = 30000; // 30 seconds to wait for server startup
const SERVER_HEALTH_CHECK_INTERVAL_MS = 1000; // Check every second during startup
const PORT_FILE_CHECK_INTERVAL_MS = 200; // Check for port file every 200ms

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

/**
 * Get the workspace root path (first workspace folder).
 */
function getWorkspaceRoot(): string | undefined {
    const folders = vscode.workspace.workspaceFolders;
    return folders && folders.length > 0 ? folders[0].uri.fsPath : undefined;
}

/**
 * Read the server port from the port file.
 * Returns the port number if found, undefined otherwise.
 */
function readPortFile(workspaceRoot?: string): number | undefined {
    const searchPaths: string[] = [];

    if (workspaceRoot) {
        searchPaths.push(path.join(workspaceRoot, '.atopile', '.server_port'));
    }

    // Also check current working directory as fallback
    const cwd = process.cwd();
    if (cwd && cwd !== workspaceRoot) {
        searchPaths.push(path.join(cwd, '.atopile', '.server_port'));
    }

    for (const portFilePath of searchPaths) {
        try {
            if (fs.existsSync(portFilePath)) {
                const content = fs.readFileSync(portFilePath, 'utf-8').trim();
                const port = parseInt(content, 10);
                if (!isNaN(port) && port > 0 && port < 65536) {
                    traceVerbose(`BackendServer: Read port ${port} from ${portFilePath}`);
                    return port;
                }
            }
        } catch (error) {
            // Ignore read errors, try next path
        }
    }
    return undefined;
}

/**
 * Wait for the port file to appear and return the port.
 */
async function waitForPortFile(workspaceRoot: string | undefined, timeoutMs: number): Promise<number | undefined> {
    const startTime = Date.now();
    while (Date.now() - startTime < timeoutMs) {
        const port = readPortFile(workspaceRoot);
        if (port !== undefined) {
            return port;
        }
        await new Promise(resolve => setTimeout(resolve, PORT_FILE_CHECK_INTERVAL_MS));
    }
    return undefined;
}

/**
 * Build the API URL from a port number.
 */
function buildApiUrl(port: number): string {
    return `http://localhost:${port}`;
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
    private _discoveredPort: number | undefined;

    private readonly _onStatusChange = new vscode.EventEmitter<boolean>();
    public readonly onStatusChange = this._onStatusChange.event;

    private readonly _onPortDiscovered = new vscode.EventEmitter<number>();
    public readonly onPortDiscovered = this._onPortDiscovered.event;

    constructor() {
        // Listen for terminal close events to clean up our reference
        this._disposables.push(
            vscode.window.onDidCloseTerminal((terminal) => {
                if (terminal === this._terminal) {
                    traceInfo('BackendServer: Terminal was closed');
                    this._terminal = undefined;
                    this._discoveredPort = undefined;
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

    get port(): number {
        return this._discoveredPort || DEFAULT_PORT;
    }

    get apiUrl(): string {
        if (this._discoveredPort) {
            return buildApiUrl(this._discoveredPort);
        }
        return getApiUrl();
    }

    get wsUrl(): string {
        return buildWsUrl(this.port);
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

        // Try to discover port from existing port file
        const workspaceRoot = getWorkspaceRoot();
        const existingPort = readPortFile(workspaceRoot);
        if (existingPort) {
            this._discoveredPort = existingPort;
            setServerPort(existingPort);
            traceInfo(`BackendServer: Found existing port file with port ${existingPort}`);

            // Check if server is actually running on that port
            if (await this._checkServerHealth()) {
                traceInfo('BackendServer: Server already running on discovered port');
                this._onPortDiscovered.fire(existingPort);
                return true;
            } else {
                traceVerbose('BackendServer: Port file exists but server not responding, will start new server');
                this._discoveredPort = undefined;
            }
        }

        // Check if server is running on default port
        this._discoveredPort = DEFAULT_PORT;
        setServerPort(DEFAULT_PORT);
        if (await this._checkServerHealth()) {
            traceInfo('BackendServer: Server already running on default port');
            return true;
        }
        this._discoveredPort = undefined;

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
            const workspaceRoot = getWorkspaceRoot();

            // Build command with --auto-port to avoid conflicts and --workspace for port file location
            const args = ['serve', 'backend', '--auto-port'];
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

            // Wait for port file to appear (server writes it on startup)
            traceVerbose('BackendServer: Waiting for port file...');
            const discoveredPort = await waitForPortFile(workspaceRoot, SERVER_STARTUP_TIMEOUT_MS / 2);
            if (discoveredPort) {
                this._discoveredPort = discoveredPort;
                setServerPort(discoveredPort);
                traceInfo(`BackendServer: Discovered port ${discoveredPort} from port file`);
                this._onPortDiscovered.fire(discoveredPort);
            } else {
                // Fall back to default port if port file not found
                traceVerbose('BackendServer: Port file not found, using default port');
                this._discoveredPort = DEFAULT_PORT;
                setServerPort(DEFAULT_PORT);
            }

            // Wait for server to be ready
            const ready = await this._waitForServerReady();
            if (ready) {
                traceInfo(`BackendServer: Server started successfully on port ${this._discoveredPort}`);
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

        this._discoveredPort = undefined;
        this._onStatusChange.dispose();
        this._onPortDiscovered.dispose();

        for (const disposable of this._disposables) {
            disposable.dispose();
        }
        this._disposables = [];
    }
}

// Singleton instance
export const backendServer = new BackendServerManager();
