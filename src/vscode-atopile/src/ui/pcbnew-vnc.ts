/**
 * PCBnew VNC viewer.
 *
 * Launches a VNC stack (Xvfb + x11vnc + websockify + pcbnew) inside the
 * Docker container, then opens the noVNC web UI in a new browser tab.
 *
 * In OpenVSCode Server (browser-based), webviews and Simple Browser can't
 * access localhost ports directly because they're served from a CDN origin.
 * Opening in a new browser tab works because the browser has direct access
 * to the Docker-exposed ports.
 */

import * as vscode from 'vscode';
import { vncServer } from '../common/vnc-server';
import { traceInfo, traceError } from '../common/log/logging';

const WS_PORT = 6080;

/**
 * Open PCBnew in a VNC viewer.
 * Starts the VNC stack if not already running, then opens noVNC.
 */
export async function openPcbnewVnc(pcbFile?: string): Promise<void> {
    traceInfo(`PcbnewVnc: openPcbnewVnc called (pcbFile=${pcbFile ?? 'none'})`);

    try {
        // Show a progress notification while starting the VNC stack
        await vscode.window.withProgress(
            {
                location: vscode.ProgressLocation.Notification,
                title: 'Starting PCBnew...',
                cancellable: false,
            },
            async () => {
                await vncServer.start(pcbFile);
            },
        );

        const noVncUrl = `http://localhost:${WS_PORT}/vnc.html?autoconnect=true&resize=scale&reconnect=true&reconnect_delay=1000`;
        traceInfo(`PcbnewVnc: Opening noVNC at: ${noVncUrl}`);

        // Open in external browser — this works in both desktop VS Code and
        // OpenVSCode Server because the browser has direct access to localhost.
        await vscode.env.openExternal(vscode.Uri.parse(noVncUrl));
    } catch (err) {
        traceError(`PcbnewVnc: Failed to start VNC: ${err}`);
        vscode.window.showErrorMessage(
            'Failed to start PCBnew VNC server. Check the "PCBnew VNC" terminal for errors.',
        );
    }
}

export function closePcbnewVnc(): void {
    vncServer.stop();
}

export async function activate(_context: vscode.ExtensionContext): Promise<void> {
    // VNC starts on demand — nothing to set up
}

export function deactivate(): void {
    closePcbnewVnc();
    vncServer.dispose();
}
