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
import * as cp from 'child_process';
import axios from 'axios';
import * as net from 'net';
import { traceInfo, traceError, traceVerbose } from './log/logging';
import { resolveAtoBinForWorkspace } from './findbin';

const BACKEND_HOST = '127.0.0.1';
const SERVER_STARTUP_TIMEOUT_MS = 30000; // 30 seconds to wait for server startup

interface BuildResponse {
    success: boolean;
    message: string;
    build_targets?: { target: string; build_id: string }[];
}

type ServerState = 'stopped' | 'starting' | 'running' | 'error';

function buildApiUrl(port: number): string {
    return `http://${BACKEND_HOST}:${port}`;
}

function buildWsUrl(port: number): string {
    return `ws://${BACKEND_HOST}:${port}/ws/state`;
}

async function getAvailablePort(): Promise<number> {
    return new Promise((resolve, reject) => {
        const server = net.createServer();
        server.unref();
        server.once('error', reject);
        server.listen(0, BACKEND_HOST, () => {
            const address = server.address();
            if (!address || typeof address === 'string') {
                server.close(() => reject(new Error('Failed to allocate port')));
                return;
            }
            const { port } = address;
            server.close((err) => {
                if (err) {
                    reject(err);
                    return;
                }
                resolve(port);
            });
        });
    });
}

/**
 * Get all workspace root paths (synchronous version for spawn calls).
 */
function getWorkspaceRoots(): string[] {
    const folders = vscode.workspace.workspaceFolders;
    return folders ? folders.map(f => f.uri.fsPath) : [];
}

/**
 * Build the WebSocket URL from a port number.
 */
/**
 * Check server health via HTTP endpoint (doesn't require WebSocket).
 */
async function checkServerHealthHttp(apiUrl: string): Promise<boolean> {
    try {
        const response = await axios.get(`${apiUrl}/health`, { timeout: 2000 });
        return response.status === 200 && response.data?.status === 'ok';
    } catch {
        return false;
    }
}

/**
 * Manages the backend server lifecycle.
 */
class BackendServerManager implements vscode.Disposable {
    private _process: cp.ChildProcess | undefined;
    private _outputChannel: vscode.OutputChannel | vscode.LogOutputChannel;
    private _serverState: ServerState = 'stopped';
    private _stdoutBuffer: string = '';
    private _stderrBuffer: string = '';
    private _stdoutFlushTimer: NodeJS.Timeout | undefined;
    private _stderrFlushTimer: NodeJS.Timeout | undefined;
    private _isConnected: boolean = false;
    private _serverReady: boolean = false;
    private _startupPromise: Promise<boolean> | null = null;
    private _restartPromise: Promise<boolean> | null = null;
    private _disposables: vscode.Disposable[] = [];
    private _statusBarItem: vscode.StatusBarItem | undefined;
    private _lastError: string | undefined;
    private _port: number = 0;
    private _apiUrl: string = buildApiUrl(0);
    private _wsUrl: string = buildWsUrl(0);

    private readonly _onStatusChange = new vscode.EventEmitter<boolean>();
    public readonly onStatusChange = this._onStatusChange.event;

    // Event emitter for messages to be sent to the webview
    private readonly _onWebviewMessage = new vscode.EventEmitter<Record<string, unknown>>();
    public readonly onWebviewMessage = this._onWebviewMessage.event;

    constructor() {
        // Create output channel for server logs (log channel when available)
        this._outputChannel = vscode.window.createOutputChannel('atopile Server', { log: true });

        // Create status bar item
        this._statusBarItem = vscode.window.createStatusBarItem(
            vscode.StatusBarAlignment.Right,
            100
        );
        this._statusBarItem.command = 'atopile.backendStatus';
        this._statusBarItem.tooltip = 'Click to manage atopile backend';
        this._updateStatusBar();
        this._statusBarItem.show();

        // Register the backend status command
        this._disposables.push(
            vscode.commands.registerCommand('atopile.backendStatus', () => {
                this._showBackendStatusMenu();
            })
        );

        // Note: Connection state is now updated via postMessage from the webview
        // (see SidebarProvider._handleWebviewMessage)
    }

    /**
     * Process buffered output and emit complete lines.
     */
    private _processBufferedOutput(
        buffer: string,
        data: string,
        level: 'info' | 'error',
        flushPartial: boolean = false
    ): { newBuffer: string } {
        buffer += data.replace(/\r\n/g, '\n').replace(/\r/g, '\n');

        // Split by newlines but keep track of incomplete lines
        const lines = buffer.split('\n');

        // The last element might be an incomplete line
        const newBuffer = flushPartial ? '' : (lines.pop() || '');

        // Output complete lines
        for (const line of lines) {
            this._appendOutputLine(level, line);
        }

        return { newBuffer };
    }

    private _appendOutputLine(level: 'info' | 'error', line: string): void {
        this._log(level, line);
    }

    private _log(level: 'info' | 'warn' | 'error' | 'debug' | 'trace', message: string): void {
        if ('info' in this._outputChannel) {
            const logChannel = this._outputChannel as vscode.LogOutputChannel;
            switch (level) {
                case 'error':
                    logChannel.error(message);
                    break;
                case 'warn':
                    logChannel.warn(message);
                    break;
                case 'debug':
                    logChannel.debug(message);
                    break;
                case 'trace':
                    logChannel.trace(message);
                    break;
                default:
                    logChannel.info(message);
            }
            return;
        }

        const prefix = level === 'info' ? '' : `[${level}] `;
        this._outputChannel.appendLine(`${prefix}${message}`);
    }

    private _schedulePartialFlush(kind: 'stdout' | 'stderr'): void {
        const isStdout = kind === 'stdout';
        const buffer = isStdout ? this._stdoutBuffer : this._stderrBuffer;
        const timer = isStdout ? this._stdoutFlushTimer : this._stderrFlushTimer;
        if (!buffer) {
            if (timer) {
                clearTimeout(timer);
            }
            if (isStdout) {
                this._stdoutFlushTimer = undefined;
            } else {
                this._stderrFlushTimer = undefined;
            }
            return;
        }

        if (timer) {
            clearTimeout(timer);
        }
        const newTimer = setTimeout(() => {
            this._flushPartial(kind);
        }, 250);
        if (isStdout) {
            this._stdoutFlushTimer = newTimer;
        } else {
            this._stderrFlushTimer = newTimer;
        }
    }

    private _flushPartial(kind: 'stdout' | 'stderr'): void {
        if (kind === 'stdout') {
            if (this._stdoutBuffer) {
                this._stdoutBuffer = this._processBufferedOutput(this._stdoutBuffer, '', 'info', true).newBuffer;
            }
            if (this._stdoutFlushTimer) {
                clearTimeout(this._stdoutFlushTimer);
                this._stdoutFlushTimer = undefined;
            }
        } else {
            if (this._stderrBuffer) {
                this._stderrBuffer = this._processBufferedOutput(
                    this._stderrBuffer,
                    '',
                    'error',
                    true
                ).newBuffer;
            }
            if (this._stderrFlushTimer) {
                clearTimeout(this._stderrFlushTimer);
                this._stderrFlushTimer = undefined;
            }
        }
    }

    /**
     * Flush any remaining buffered output.
     */
    private _flushBuffers(): void {
        this._flushPartial('stdout');
        this._flushPartial('stderr');
        this._stdoutBuffer = '';
        this._stderrBuffer = '';
    }

    /**
     * Update the status bar item to reflect current connection state.
     */
    private _updateStatusBar(): void {
        if (!this._statusBarItem) return;

        if (this._serverState === 'starting') {
            this._statusBarItem.text = '$(sync~spin) ato: Starting...';
            this._statusBarItem.backgroundColor = undefined;
        } else if (this._serverState === 'error') {
            this._statusBarItem.text = '$(error) ato: Error';
            this._statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.errorBackground');
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
        let statusText: string;
        if (this._serverState === 'error') {
            statusText = `Error: ${this._lastError || 'Unknown error'}`;
        } else if (this._isConnected) {
            statusText = `Connected to port ${this.port}`;
        } else if (this._serverState === 'starting') {
            statusText = 'Starting...';
        } else {
            statusText = 'Disconnected';
        }

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
        ];

        items.push({
            label: '$(output) Show Server Logs',
            description: 'Show the backend server output',
            action: 'show_logs',
        });

        const selected = await vscode.window.showQuickPick(items, {
            placeHolder: 'Backend Server Configuration',
            title: 'atopile Backend',
        });

        if (!selected || selected.action === 'none') return;

        switch (selected.action) {
            case 'show_logs':
                this.showLogs();
                break;
        }
    }

    get isConnected(): boolean {
        return this._isConnected;
    }

    get isStarting(): boolean {
        return this._serverState === 'starting';
    }

    get port(): number {
        return this._port;
    }

    get apiUrl(): string {
        return this._apiUrl;
    }

    get wsUrl(): string {
        return this._wsUrl;
    }

    private _setPort(port: number): void {
        this._port = port;
        this._apiUrl = buildApiUrl(port);
        this._wsUrl = buildWsUrl(port);
    }

    /**
     * Update connection status (called from SidebarProvider when WebSocket connects/disconnects).
     */
    setConnected(connected: boolean): void {
        traceInfo(`BackendServer: setConnected(${connected}) called, current: ${this._isConnected}`);
        if (this._isConnected !== connected) {
            this._isConnected = connected;
            traceInfo(`BackendServer: ${connected ? 'Connected' : 'Disconnected'}, firing onStatusChange`);
            this._onStatusChange.fire(connected);
            this._updateStatusBar();

            // No-op: connection state shouldn't trigger backend configuration.
        }
    }

    /**
     * Show the server logs output channel.
     */
    showLogs(): void {
        this._outputChannel.show();
    }

    /**
     * Start the backend server automatically.
     * Returns true if server started successfully, false otherwise.
     * @param preferredPort Optional port to use (for restart to keep same port)
     */
    async startServer(preferredPort?: number): Promise<boolean> {
        // If already starting, wait for that to complete
        if (this._startupPromise) {
            return this._startupPromise;
        }

        // If we already have a process, assume we're in control
        if (this._process) {
            if (this._serverState === 'running' || this._serverState === 'starting') {
                traceVerbose('BackendServer: Process already managed, skipping start');
                return true;
            }
            await this.stopServer();
        }

        this._startupPromise = this._doStartServer(preferredPort);
        try {
            return await this._startupPromise;
        } finally {
            this._startupPromise = null;
        }
    }

    private async _doStartServer(preferredPort?: number): Promise<boolean> {
        this._serverState = 'starting';
        this._lastError = undefined;
        this._stdoutBuffer = '';
        this._stderrBuffer = '';
        this._serverReady = false;
        this._updateStatusBar();

        // Send initial progress update
        this._onWebviewMessage.fire({
            type: 'atopileInstalling',
            message: 'Looking for atopile...',
        });
        traceInfo('[BackendServer] Starting server initialization...');

        try {
            // Get a port to use - prefer the provided port, or get an available one
            const port = preferredPort || await getAvailablePort();
            this._setPort(port);
            traceInfo(`[BackendServer] Using port: ${port}`);

            const workspaceRoots = getWorkspaceRoots();
            traceInfo(`[BackendServer] Workspace roots: ${workspaceRoots.join(', ') || '(none)'}`);

            // Send progress update: resolving ato binary
            this._onWebviewMessage.fire({
                type: 'atopileInstalling',
                message: 'Resolving atopile binary...',
            });

            const resolved = await resolveAtoBinForWorkspace();
            if (!resolved) {
                this._lastError = 'ato binary not found. Check that atopile is installed in .venv/bin/ato or configure atopile.ato in settings.';
                traceError(`[BackendServer] Cannot start server - ${this._lastError}`);
                this._serverState = 'error';
                this._updateStatusBar();
                this._onWebviewMessage.fire({
                    type: 'atopileInstallError',
                    error: this._lastError,
                });
                return false;
            }
            const { settings, atoBin } = resolved;
            traceInfo(`[BackendServer] Found ato binary: ${atoBin.command.join(' ')} (source: ${atoBin.source})`);

            if (this._process) {
                await this.stopServer();
            }

            // Send progress update: starting server
            this._onWebviewMessage.fire({
                type: 'atopileInstalling',
                message: `Starting backend server (${atoBin.source})...`,
            });

            // Determine UI source type from settings and atoBin source
            // 'local' if using local installation (settings.ato or workspace-venv),
            // 'branch' if from starts with 'git+', else 'release'
            let uiSourceType = 'release';
            if (settings.ato || atoBin.source === 'workspace-venv' || atoBin.source === 'settings') {
                uiSourceType = 'local';
            } else if (settings.from?.startsWith('git+')) {
                uiSourceType = 'branch';
            }

            // Get the actual binary path (first element of the command)
            const atoBinaryPath = atoBin.command[0];

            // Build command args: ato serve backend --port <port> [--workspace <path>...]
            const args = [
                ...atoBin.command.slice(1),
                'serve', 'backend',
                '--port', String(this.port),
                '--ato-source', atoBin.source,
                '--ato-ui-source', uiSourceType,
                '--ato-binary-path', atoBinaryPath,
            ];
            // Pass all workspace roots to the backend
            for (const root of workspaceRoots) {
                args.push('--workspace', root);
            }

            const command = atoBin.command[0];
            traceInfo(`BackendServer: Starting server: ${command} ${args.join(' ')}`);
            this._log('info', `server: Starting: ${command} ${args.join(' ')}`);

            // Spawn the server process with unbuffered Python output
            const child = cp.spawn(command, args, {
                cwd: workspaceRoots.length > 0 ? workspaceRoots[0] : undefined,
                env: {
                    ...process.env,
                    ATO_NON_INTERACTIVE: 'y',
                    PYTHONUNBUFFERED: '1',  // Disable Python output buffering
                },
                stdio: ['ignore', 'pipe', 'pipe'],
            });

            this._process = child;

            let stderrCollected = '';
            child.stdout?.on('data', (data: Buffer) => {
                const text = data.toString();
                this._stdoutBuffer = this._processBufferedOutput(this._stdoutBuffer, text, 'info').newBuffer;
                this._schedulePartialFlush('stdout');
            });

            child.stderr?.on('data', (data: Buffer) => {
                const text = data.toString();
                stderrCollected += text;
                this._stderrBuffer = this._processBufferedOutput(this._stderrBuffer, text, 'error').newBuffer;
                this._schedulePartialFlush('stderr');
            });

            child.on('exit', (code, signal) => {
                this._flushBuffers();
                const exitMsg = signal
                    ? `Server process killed by signal ${signal}`
                    : `Server process exited with code ${code}`;

                traceInfo(`BackendServer: ${exitMsg}`);
                this._log('info', `server: ${exitMsg}`);
                this._process = undefined;
                this._serverReady = false;

                if (this._serverState === 'starting') {
                    const errorMsg = stderrCollected.trim() || `Process exited with code ${code}`;
                    this._lastError = errorMsg.slice(0, 200);
                    this._serverState = 'error';
                    this._updateStatusBar();
                } else if (this._serverState === 'running') {
                    this._serverState = 'stopped';
                    this._lastError = exitMsg;
                    this._updateStatusBar();
                }
            });

            child.on('error', (err) => {
                traceError(`BackendServer: Spawn error: ${err.message}`);
                this._log('error', `server: Spawn error: ${err.message}`);
                this._lastError = err.message;
                this._serverState = 'error';
                this._process = undefined;
                this._serverReady = false;
                this._updateStatusBar();
            });

            // Send progress update: waiting for server
            this._onWebviewMessage.fire({
                type: 'atopileInstalling',
                message: 'Waiting for server to initialize...',
            });

            const ready = await this._waitForServerReady(child);

            if (ready) {
                this._serverReady = true;
                traceInfo(`BackendServer: Server started successfully on port ${this.port}`);
                this._log('info', `server: Started successfully on port ${this.port}`);
                this._serverState = 'running';
                this._updateStatusBar();

                // Send progress update: server ready (will be cleared by WebSocket connection)
                this._onWebviewMessage.fire({
                    type: 'atopileInstalling',
                    message: 'Connecting to server...',
                });
                // Note: WebSocket connection is now managed by ui-server,
                // which connects when the webview loads
            } else {
                if (!this._lastError) {
                    this._lastError = 'Server startup timeout';
                }
                traceError(`BackendServer: Server failed to start: ${this._lastError}`);
                this._log('error', `server: Failed to start: ${this._lastError}`);
                this._serverState = 'error';
                this._updateStatusBar();

                // Send error notification
                this._onWebviewMessage.fire({
                    type: 'atopileInstallError',
                    error: this._lastError,
                });

                await this.stopServer();
            }

            return ready;
        } catch (error) {
            const errorMsg = error instanceof Error ? error.message : String(error);
            this._lastError = errorMsg;
            traceError(`BackendServer: Failed to start server: ${errorMsg}`);
            this._log('error', `server: Failed to start: ${errorMsg}`);
            this._serverState = 'error';
            this._updateStatusBar();

            // Send error notification
            this._onWebviewMessage.fire({
                type: 'atopileInstallError',
                error: errorMsg,
            });

            return false;
        }
    }

    private async _waitForServerReady(child: cp.ChildProcess): Promise<boolean> {
        const start = Date.now();
        while (Date.now() - start < SERVER_STARTUP_TIMEOUT_MS) {
            if (this._process !== child) {
                return false;
            }
            if (await checkServerHealthHttp(this.apiUrl)) {
                return true;
            }
            await new Promise(resolve => setTimeout(resolve, 500));
        }
        return false;
    }

    /**
     * Restart the backend server (e.g., when version changes).
     * Reuses the same port so the webview's WebSocket can reconnect.
     */
    async restartServer(): Promise<boolean> {
        // If already restarting, wait for that to complete
        if (this._restartPromise) {
            traceInfo('BackendServer: Restart already in progress, waiting...');
            return this._restartPromise;
        }

        this._restartPromise = this._doRestartServer();
        try {
            return await this._restartPromise;
        } finally {
            this._restartPromise = null;
        }
    }

    private async _doRestartServer(): Promise<boolean> {
        traceInfo('BackendServer: Restarting server...');
        this._log('info', 'server: Restarting...');

        // Save the current port to reuse it
        const previousPort = this._port;

        // Stop existing server
        await this.stopServer();

        // Small delay to let the port be released
        await new Promise(resolve => setTimeout(resolve, 500));

        // Start new server with the same port
        return this.startServer(previousPort);
    }

    /**
     * Stop the backend server.
     */
    async stopServer(): Promise<void> {
        if (this._process) {
            traceInfo('BackendServer: Stopping server...');
            this._log('info', 'server: Stopping...');

            const proc = this._process;
            this._process = undefined;
            this._serverReady = false;

            // Try graceful shutdown first (SIGTERM)
            proc.kill('SIGTERM');

            // Wait for process to exit, with timeout
            const exitPromise = new Promise<void>((resolve) => {
                proc.once('exit', () => resolve());
                // Force kill after 3 seconds if still running
                setTimeout(() => {
                    if (!proc.killed) {
                        traceInfo('BackendServer: Force killing server (SIGKILL)');
                        proc.kill('SIGKILL');
                    }
                    resolve();
                }, 3000);
            });

            await exitPromise;
            if (this._serverState !== 'error') {
                this._serverState = 'stopped';
            }
            this._updateStatusBar();
            traceInfo('BackendServer: Server stopped');
            this._log('info', 'server: Stopped');
        }
        // Note: WebSocket disconnection is handled by ui-server when the webview unloads
    }

    /**
     * Show the server logs (for backwards compatibility with showTerminal).
     */
    async showTerminal(): Promise<void> {
        // If server is not running, start it
        if (!this._process && !this._isConnected) {
            await this.startServer();
        }
        this.showLogs();
    }

    async startOrShowTerminal(): Promise<void> {
        await this.showTerminal();
    }

    /**
     * Trigger a build via the API.
     */
    /**
     * Trigger a build via the webview's WebSocket connection.
     * The build is fire-and-forget - status updates come via WebSocket state broadcasts.
     */
    async build(projectPath: string, targets: string[]): Promise<BuildResponse> {
        if (!this._isConnected) {
            throw new Error('Backend server is not connected. Run "ato serve" to start it.');
        }

        const requestId = `build-${Date.now()}`;
        traceInfo(`Build requested: ${projectPath} targets=${targets.join(',')} requestId=${requestId}`);

        // Send message to webview to trigger build via WebSocket
        this._onWebviewMessage.fire({
            type: 'triggerBuild',
            projectRoot: projectPath,
            targets,
            requestId,
        });

        // Return immediately - build status comes via WebSocket state updates
        return {
            success: true,
            message: 'Build triggered',
            build_targets: [],
        };
    }

    /**
     * Send a message to the webview (for forwarding to backend via WebSocket).
     */
    sendToWebview(message: Record<string, unknown>): void {
        this._onWebviewMessage.fire(message);
    }

    dispose(): void {
        // Stop the server gracefully
        if (this._process) {
            this._process.kill('SIGTERM');
            // Give it a moment, then force kill
            setTimeout(() => {
                if (this._process && !this._process.killed) {
                    this._process.kill('SIGKILL');
                }
            }, 1000);
            this._process = undefined;
        }

        // Dispose output channel
        this._outputChannel.dispose();

        // Dispose status bar item
        if (this._statusBarItem) {
            this._statusBarItem.dispose();
            this._statusBarItem = undefined;
        }

        this._onStatusChange.dispose();
        this._onWebviewMessage.dispose();

        for (const disposable of this._disposables) {
            disposable.dispose();
        }
        this._disposables = [];
    }
}

// Singleton instance
export const backendServer = new BackendServerManager();
