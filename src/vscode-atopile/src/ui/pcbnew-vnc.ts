/**
 * PCBnew VNC viewer — embedded in a VS Code webview panel.
 *
 * Uses a bundled noVNC RFB client that connects via WebSocket to websockify
 * (ws://localhost:6080). WebSocket connections to localhost are allowed from
 * HTTPS webview origins (Chromium treats localhost as a secure context).
 */

import * as vscode from 'vscode';
import { vncServer } from '../common/vnc-server';
import { getAndCheckResource } from '../common/resources';
import { BaseWebview } from './webview-base';
import { getNonce } from './webview-utils';
import { traceInfo, traceError } from '../common/log/logging';

const WS_PORT = 6080;

class PcbnewVncWebview extends BaseWebview {
    constructor() {
        super({
            id: 'pcbnew_vnc',
            title: 'PCBnew',
            iconName: 'pcb-icon-transparent.svg',
        });
    }

    protected getHtmlContent(webview: vscode.Webview): string {
        const nonce = getNonce();

        // Resolve the bundled noVNC script
        let novncBundlePath: string;
        try {
            novncBundlePath = getAndCheckResource('novnc/novnc.bundle.js');
        } catch {
            return this.getBundleMissingHtml();
        }
        const novncUri = webview.asWebviewUri(vscode.Uri.file(novncBundlePath));

        return /* html */ `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Security-Policy" content="
        default-src 'none';
        script-src 'nonce-${nonce}' ${webview.cspSource};
        style-src 'unsafe-inline';
        img-src data:;
        connect-src ws://localhost:${WS_PORT};
    ">
    <title>PCBnew</title>
    <style>
        html, body {
            margin: 0;
            padding: 0;
            width: 100%;
            height: 100%;
            overflow: hidden;
            background: #1e1e1e;
        }
        #vnc-container {
            width: 100%;
            height: 100%;
        }
        #status-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            background: var(--vscode-editor-background, #1e1e1e);
            color: var(--vscode-foreground, #ccc);
            font-family: var(--vscode-font-family, sans-serif);
            font-size: 14px;
            z-index: 100;
            transition: opacity 0.3s;
        }
        #status-overlay.hidden {
            opacity: 0;
            pointer-events: none;
        }
        .status-content {
            text-align: center;
        }
        .spinner {
            width: 24px;
            height: 24px;
            border: 3px solid rgba(255,255,255,0.2);
            border-top-color: #f95015;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            margin: 0 auto 12px;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        .reconnect-btn {
            margin-top: 12px;
            padding: 6px 16px;
            background: #f95015;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 13px;
        }
        .reconnect-btn:hover {
            background: #ff6b35;
        }
    </style>
</head>
<body>
    <div id="status-overlay">
        <div class="status-content">
            <div class="spinner"></div>
            <div id="status-text">Connecting...</div>
        </div>
    </div>
    <div id="vnc-container"></div>

    <script nonce="${nonce}" type="module">
        import noVNCModule from '${novncUri}';
        const RFB = noVNCModule.default || noVNCModule;

        const overlay = document.getElementById('status-overlay');
        const statusText = document.getElementById('status-text');
        const container = document.getElementById('vnc-container');

        function showStatus(msg, showReconnect) {
            statusText.textContent = msg;
            overlay.classList.remove('hidden');

            // Remove old reconnect button if any
            const old = overlay.querySelector('.reconnect-btn');
            if (old) old.remove();

            if (showReconnect) {
                const spinner = overlay.querySelector('.spinner');
                if (spinner) spinner.style.display = 'none';

                const btn = document.createElement('button');
                btn.className = 'reconnect-btn';
                btn.textContent = 'Reconnect';
                btn.onclick = () => connect();
                overlay.querySelector('.status-content').appendChild(btn);
            } else {
                const spinner = overlay.querySelector('.spinner');
                if (spinner) spinner.style.display = '';
            }
        }

        function hideStatus() {
            overlay.classList.add('hidden');
        }

        let rfb = null;

        function connect() {
            showStatus('Connecting...', false);

            if (rfb) {
                rfb.disconnect();
                rfb = null;
            }

            rfb = new RFB(container, 'ws://localhost:${WS_PORT}', {
                wsProtocols: ['binary']
            });
            rfb.scaleViewport = true;
            rfb.resizeSession = true;

            rfb.addEventListener('connect', () => {
                hideStatus();
            });

            rfb.addEventListener('disconnect', (e) => {
                const clean = e.detail && e.detail.clean;
                showStatus(
                    clean ? 'Disconnected' : 'Connection lost',
                    true
                );
                rfb = null;
            });
        }

        connect();
    </script>
</body>
</html>`;
    }

    protected onDispose(): void {
        traceInfo('PcbnewVnc: Webview panel closed');
    }

    private getBundleMissingHtml(): string {
        return /* html */ `<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
    body {
        display: flex; align-items: center; justify-content: center;
        height: 100vh; margin: 0;
        background: var(--vscode-editor-background);
        color: var(--vscode-foreground);
        font-family: var(--vscode-font-family);
    }
    code { background: var(--vscode-textCodeBlock-background); padding: 2px 6px; border-radius: 3px; }
</style>
</head><body>
<div><p>noVNC bundle not found.</p><p>Run <code>npm run build:novnc</code></p></div>
</body></html>`;
    }
}

let pcbnewVnc: PcbnewVncWebview | undefined;

/**
 * Open PCBnew in an embedded VNC viewer.
 * Starts the VNC stack if not already running, then opens the webview panel.
 *
 * PCB reload on changes is handled by the existing KiCad IPC mechanism:
 * `ato build` calls `reload_pcb()` which tells running PCBnew to reload
 * via the KiCad socket API (`/tmp/kicad/api*.sock`).
 */
export async function openPcbnewVnc(pcbFile?: string): Promise<void> {
    traceInfo(`PcbnewVnc: openPcbnewVnc called (pcbFile=${pcbFile ?? 'none'})`);

    try {
        if (!vncServer.isRunning) {
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
        }

        if (!pcbnewVnc) {
            pcbnewVnc = new PcbnewVncWebview();
        }
        await pcbnewVnc.open();
    } catch (err) {
        traceError(`PcbnewVnc: Failed to start VNC: ${err}`);
        vscode.window.showErrorMessage(
            'Failed to start PCBnew VNC server. Check the "PCBnew VNC" terminal for errors.',
        );
    }
}

export function closePcbnewVnc(): void {
    pcbnewVnc?.dispose();
    pcbnewVnc = undefined;
    vncServer.stop();
}

export async function activate(_context: vscode.ExtensionContext): Promise<void> {
    // PCB reload on changes is handled by the KiCad IPC mechanism:
    // `ato build` → `reload_pcb()` → KiCad socket API → PCBnew reloads from disk.
    // No extension-side handling needed.
}

export function deactivate(): void {
    closePcbnewVnc();
    vncServer.dispose();
}
