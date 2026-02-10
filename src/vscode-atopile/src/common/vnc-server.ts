/**
 * VNC server lifecycle management for PCBnew viewer.
 *
 * Manages the VNC stack (Xvfb + openbox + x11vnc + websockify + pcbnew)
 * by running start-pcbnew-vnc.sh in a VS Code terminal.
 */

import * as vscode from 'vscode';
import * as http from 'http';
import { traceInfo, traceError } from './log/logging';

const WS_PORT = 6080;
const STARTUP_TIMEOUT_MS = 15000;
const HEALTH_POLL_INTERVAL_MS = 500;

/**
 * Check if websockify is responding on the expected port.
 */
function checkWebsockifyHealth(): Promise<boolean> {
    return new Promise((resolve) => {
        const req = http.get(`http://localhost:${WS_PORT}/`, { timeout: 2000 }, (res) => {
            // websockify serves noVNC; any response means it's up
            resolve(res.statusCode !== undefined);
        });
        req.on('error', () => resolve(false));
        req.on('timeout', () => {
            req.destroy();
            resolve(false);
        });
    });
}

/**
 * Singleton that manages the VNC server stack lifecycle.
 */
class VncServerManager implements vscode.Disposable {
    private terminal: vscode.Terminal | undefined;
    private _isRunning = false;
    private _disposables: vscode.Disposable[] = [];
    private _lastPcbFile: string | undefined;
    private _lastDarkMode: boolean | undefined;

    constructor() {
        // Clean up if the user closes the terminal manually
        this._disposables.push(
            vscode.window.onDidCloseTerminal((closed) => {
                if (closed === this.terminal) {
                    traceInfo('VncServer: Terminal closed by user');
                    this.terminal = undefined;
                    this._isRunning = false;
                }
            })
        );
    }

    get isRunning(): boolean {
        return this._isRunning;
    }

    /**
     * Start the VNC stack and return the WebSocket URL for noVNC.
     * @param pcbFile — optional path to .kicad_pcb file
     * @param darkMode — if true, set GTK dark theme for KiCad
     */
    async start(pcbFile?: string, darkMode?: boolean): Promise<string> {
        // If already running, just return the URL
        if (this._isRunning && this.terminal) {
            traceInfo('VncServer: Already running');
            return this.getNoVncUrl();
        }

        // Store for restart()
        this._lastPcbFile = pcbFile;
        this._lastDarkMode = darkMode;

        traceInfo(`VncServer: Starting VNC stack${pcbFile ? ` with ${pcbFile}` : ''} (dark=${darkMode ?? 'unset'})`);

        // Build command with dark mode env var prefix
        const darkEnv = darkMode !== undefined ? `KICAD_DARK_MODE=${darkMode ? '1' : '0'} ` : '';
        const cmd = pcbFile
            ? `${darkEnv}start-pcbnew-vnc.sh "${pcbFile}"`
            : `${darkEnv}start-pcbnew-vnc.sh`;

        // Create terminal and run the script
        this.terminal = vscode.window.createTerminal({
            name: 'PCBnew VNC',
            hideFromUser: true,
        });
        this.terminal.sendText(cmd);

        // Wait for websockify to become healthy
        const ready = await this.waitForReady();
        if (!ready) {
            traceError('VncServer: Timed out waiting for websockify');
            vscode.window.showErrorMessage(
                'PCBnew VNC server failed to start. Check the "PCBnew VNC" terminal for errors.'
            );
            // Show terminal so user can debug
            this.terminal.show();
            return this.getNoVncUrl();
        }

        this._isRunning = true;
        traceInfo('VncServer: VNC stack ready');
        return this.getNoVncUrl();
    }

    /**
     * Stop the VNC stack.
     */
    async stop(): Promise<void> {
        if (this.terminal) {
            traceInfo('VncServer: Stopping VNC stack');
            // Send Ctrl+C to trigger the trap handler in the script
            this.terminal.sendText('\x03');
            // Give it a moment, then dispose the terminal
            await new Promise((resolve) => setTimeout(resolve, 1000));
            this.terminal.dispose();
            this.terminal = undefined;
        }
        this._isRunning = false;
    }

    /**
     * Restart the VNC stack with the given dark mode, re-using the last PCB file.
     */
    async restart(darkMode: boolean): Promise<string> {
        await this.stop();
        return this.start(this._lastPcbFile, darkMode);
    }

    /**
     * Get the noVNC web UI URL with auto-connect parameters.
     */
    getNoVncUrl(): string {
        return `http://localhost:${WS_PORT}/vnc.html?autoconnect=true&resize=scale&reconnect=true&reconnect_delay=1000`;
    }

    /**
     * Get the WebSocket URL for direct noVNC client connections.
     */
    getWsUrl(): string {
        return `ws://localhost:${WS_PORT}`;
    }

    private async waitForReady(): Promise<boolean> {
        const start = Date.now();
        while (Date.now() - start < STARTUP_TIMEOUT_MS) {
            if (await checkWebsockifyHealth()) {
                return true;
            }
            await new Promise((resolve) => setTimeout(resolve, HEALTH_POLL_INTERVAL_MS));
        }
        return false;
    }

    dispose(): void {
        this.stop();
        for (const d of this._disposables) {
            d.dispose();
        }
        this._disposables = [];
    }
}

// Singleton instance
export const vncServer = new VncServerManager();
