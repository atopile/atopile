/**
 * PCBnew VNC viewer webview.
 *
 * Embeds the noVNC web UI (served by websockify) in an iframe inside
 * a VS Code webview panel. The VNC stack runs inside the Docker container
 * and provides a full PCBnew session accessible from the browser.
 */

import * as vscode from 'vscode';
import { BaseWebview } from './webview-base';
import { buildHtml } from './html-builder';
import { vncServer } from '../common/vnc-server';
import { traceInfo } from '../common/log/logging';

class PcbnewVncWebview extends BaseWebview {
    private noVncUrl: string = '';

    constructor() {
        super({
            id: 'pcbnew_vnc',
            title: 'PCBnew',
            iconName: 'pcb-icon-transparent.svg',
        });
    }

    setNoVncUrl(url: string): void {
        this.noVncUrl = url;
    }

    protected getHtmlContent(_webview: vscode.Webview): string {
        if (!this.noVncUrl) {
            return buildHtml({
                title: 'PCBnew VNC',
                styles: `
                    body {
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        background: var(--vscode-editor-background);
                        color: var(--vscode-descriptionForeground);
                        font-family: var(--vscode-font-family);
                    }
                    .msg {
                        text-align: center;
                        font-size: 0.9rem;
                        opacity: 0.8;
                    }
                    .spinner {
                        margin: 0 auto 1rem;
                        width: 32px;
                        height: 32px;
                        border: 3px solid var(--vscode-descriptionForeground);
                        border-top-color: transparent;
                        border-radius: 50%;
                        animation: spin 1s linear infinite;
                    }
                    @keyframes spin {
                        to { transform: rotate(360deg); }
                    }
                `,
                body: `
                    <div class="msg">
                        <div class="spinner"></div>
                        <div>Starting PCBnew...</div>
                    </div>
                `,
            });
        }

        return buildHtml({
            title: 'PCBnew VNC',
            styles: `
                html, body {
                    background: #1e1e1e;
                }
                iframe {
                    border: none;
                    width: 100%;
                    height: 100%;
                }
            `,
            body: `<iframe src="${this.noVncUrl}" allow="clipboard-read; clipboard-write"></iframe>`,
        });
    }

    protected onDispose(): void {
        traceInfo('PcbnewVnc: Webview disposed, stopping VNC server');
        vncServer.stop();
    }
}

// Singleton
let pcbnewVnc: PcbnewVncWebview | undefined;

/**
 * Open PCBnew in a VNC viewer webview panel.
 * Starts the VNC stack if not already running.
 */
export async function openPcbnewVnc(pcbFile?: string): Promise<void> {
    if (!pcbnewVnc) {
        pcbnewVnc = new PcbnewVncWebview();
    }

    // Show loading state immediately
    pcbnewVnc.setNoVncUrl('');
    await pcbnewVnc.open();

    // Start VNC server (or get existing URL)
    const url = await vncServer.start(pcbFile);

    // Update webview with the noVNC URL
    pcbnewVnc.setNoVncUrl(url);
    await pcbnewVnc.open();
}

export function closePcbnewVnc(): void {
    pcbnewVnc?.dispose();
    pcbnewVnc = undefined;
}

export async function activate(_context: vscode.ExtensionContext): Promise<void> {
    // Nothing to set up on activation — VNC starts on demand
}

export function deactivate(): void {
    closePcbnewVnc();
    vncServer.dispose();
}
