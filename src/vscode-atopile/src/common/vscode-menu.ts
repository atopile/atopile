/**
 * VS Code menu for atopile extension.
 *
 * This module provides the main atopile quick pick menu accessible
 * from the status bar item.
 */

import * as vscode from 'vscode';
import { getAtoCommand } from './findbin';
import { backendServer } from './backendServer';

/**
 * Get all workspace root paths.
 */
function getWorkspaceRoots(): string[] {
    const folders = vscode.workspace.workspaceFolders;
    return folders ? folders.map(f => f.uri.fsPath) : [];
}

/**
 * Open a new terminal with `ato` aliased to the extension-managed command.
 */
export async function openAtoShell(): Promise<void> {
    const atoCommand = await getAtoCommand();
    if (!atoCommand) {
        void vscode.window.showErrorMessage('Unable to resolve ato command. Check your atopile settings.');
        return;
    }

    const workspaceRoots = getWorkspaceRoots();
    const cwd = workspaceRoots.length > 0 ? workspaceRoots[0] : undefined;

    const inPowershell =
        vscode.env.shell &&
        (vscode.env.shell.toLowerCase().includes('powershell') ||
         vscode.env.shell.toLowerCase().includes('pwsh'));

    const terminal = vscode.window.createTerminal({
        name: 'ato shell',
        shellPath: '/bin/bash',
        cwd: cwd,
    });

    if (inPowershell) {
        terminal.sendText(`Function ato { & ${atoCommand} @args }`);
        terminal.sendText('cls');
    } else {
        terminal.sendText(`alias ato="${atoCommand}"`);
        terminal.sendText('clear');
    }

    terminal.sendText('ato');
    terminal.show();
}

/**
 * Clear build logs using the resolved ato command.
 */
async function clearBuildLogs(): Promise<void> {
    const atoCommand = await getAtoCommand(undefined, ['dev', 'clear-logs']);
    if (!atoCommand) {
        void vscode.window.showErrorMessage('Unable to resolve ato command. Check your atopile settings.');
        return;
    }

    const terminal = vscode.window.createTerminal({ name: 'atopile', shellPath: '/bin/bash' });
    terminal.show();
    terminal.sendText(atoCommand);
}

/**
 * Show the main atopile menu.
 */
async function showMenu(): Promise<void> {
    let statusText: string;
    if (backendServer.serverState === 'error') {
        statusText = `Error: ${backendServer.lastError || 'Unknown error'}`;
    } else if (backendServer.isConnected) {
        statusText = `Connected to port ${backendServer.port}`;
    } else if (backendServer.serverState === 'starting') {
        statusText = 'Starting...';
    } else if (backendServer.serverState === 'running') {
        statusText = 'Connecting...';
    } else {
        statusText = 'Disconnected';
    }

    interface MenuItem extends vscode.QuickPickItem {
        action: string;
    }

    const items: MenuItem[] = [
        { label: '$(terminal) Open ato Shell', action: 'open_ato_shell' },
        { label: '$(comment-discussion) Join Discord', action: 'open_discord' },
        { label: `$(info) Status: ${statusText}`, action: 'none' },
        { label: '', kind: vscode.QuickPickItemKind.Separator, action: 'none' },
        { label: '$(tools) Show Application Logs', action: 'show_logs' },
        { label: '$(tools) Clear Build Logs', action: 'clear_logs' },
        { label: '$(tools) Restart Extension Host', action: 'restart_extension_host' },
    ];

    const selected = await vscode.window.showQuickPick(items, {
        title: 'atopile',
    });

    if (!selected || selected.action === 'none') return;

    switch (selected.action) {
        case 'show_logs':
            backendServer.showLogs();
            break;
        case 'open_ato_shell':
            await openAtoShell();
            break;
        case 'clear_logs':
            await clearBuildLogs();
            break;
        case 'restart_extension_host':
            void vscode.commands.executeCommand('workbench.action.restartExtensionHost');
            break;
        case 'open_discord':
            void vscode.env.openExternal(vscode.Uri.parse('https://discord.gg/CRe5xaDBr3'));
            break;
    }
}

/**
 * Initialize the menu command. Call this during extension activation.
 */
export function initMenu(context: vscode.ExtensionContext): void {
    context.subscriptions.push(
        vscode.commands.registerCommand('atopile.showMenu', showMenu)
    );
}
