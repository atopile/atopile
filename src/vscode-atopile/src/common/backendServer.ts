/**
 * Backend server client for the atopile dashboard API.
 *
 * The server must be started manually via the Server button in the sidebar.
 * Connection status is tracked via WebSocket connection in appStateManager.
 */

import * as vscode from 'vscode';
import axios from 'axios';
import { traceInfo, traceError } from './log/logging';
import { getAtoBin } from './findbin';

const DEFAULT_API_URL = 'http://localhost:8501';

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

class BackendServerClient {
    private _isConnected: boolean = false;

    private readonly _onStatusChange = new vscode.EventEmitter<boolean>();
    public readonly onStatusChange = this._onStatusChange.event;

    get isConnected(): boolean {
        return this._isConnected;
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

    /**
     * Configure the ato binary path on the server.
     */
    private async _configureAtoBinary(): Promise<void> {
        try {
            const atoBinInfo = await getAtoBin();
            if (atoBinInfo && atoBinInfo.command.length > 0) {
                // The command array typically looks like ["/path/to/ato"] or ["uv", "run", "ato"]
                // For simple cases, use the first element as the binary path
                // For uv-based execution, we'll use the full command
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
     * Manually start or show the server terminal.
     * Called from command palette or sidebar button.
     */
    async startOrShowTerminal(): Promise<void> {
        // Check if terminal already exists (look for our named terminal)
        const existingTerminal = vscode.window.terminals.find(t => t.name === 'ato serve');
        if (existingTerminal) {
            existingTerminal.show();
            return;
        }

        // Check if server is already running (started externally or terminal was closed)
        if (this._isConnected) {
            const choice = await vscode.window.showInformationMessage(
                'Server is already running but terminal is not available. Restart server in a new terminal?',
                'Restart Server',
                'Cancel'
            );
            if (choice !== 'Restart Server') {
                return;
            }
            // Fall through to create new terminal with --force to replace old server
        }

        // Create new terminal and start server
        try {
            const atoBinInfo = await getAtoBin();
            if (!atoBinInfo || atoBinInfo.command.length === 0) {
                vscode.window.showErrorMessage('Cannot start server - ato binary not found');
                return;
            }

            // Use --force if server is already running to kill the orphaned process
            const forceFlag = this._isConnected ? '--force' : '';
            const command = [...atoBinInfo.command, 'serve', 'start', forceFlag].filter(Boolean).join(' ');
            traceInfo(`BackendServer: Starting server in terminal: ${command}`);

            const terminal = vscode.window.createTerminal({
                name: 'ato serve',
                hideFromUser: false,
            });
            terminal.sendText(command);
            terminal.show();
        } catch (error) {
            traceError(`BackendServer: Failed to start server: ${error}`);
            vscode.window.showErrorMessage(`Failed to start server: ${error}`);
        }
    }

    dispose(): void {
        this._onStatusChange.dispose();
    }
}

// Singleton instance
export const backendServer = new BackendServerClient();
