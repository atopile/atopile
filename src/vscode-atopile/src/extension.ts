// Copyright (c) Microsoft Corporation. All rights reserved.
// Licensed under the MIT License.

import * as vscode from 'vscode';
import { LanguageClient } from 'vscode-languageclient/node';
import { registerLogger, traceInfo, traceLog, traceVerbose, initTimer, traceMilestone } from './common/log/logging';
import { startOrRestartServer, initServer, onNeedsRestart } from './common/lspServer';
import { getExtensionManagedUvPath, setUvPathLocal, onDidChangeAtoBinInfoEvent, resetAtoBinFailures } from './common/findbin';
import { getLSClientTraceLevel } from './common/utilities';
import { createOutputChannel, get_ide_type } from './common/vscodeapi';
import * as ui from './ui/ui';
import { SERVER_ID, SERVER_NAME } from './common/constants';
import { captureEvent, deinitializeTelemetry, initializeTelemetry, updateConfig } from './common/telemetry';
import { onBuildTargetChanged } from './common/target';
import { Build } from './common/manifest';
import { openPackageExplorer } from './ui/packagexplorer';
import * as llm from './common/llm';
import { backendServer } from './common/backendServer';
import { initMenu } from './common/vscode-menu';
import { SidebarProvider, LogViewerProvider } from './providers';
import { ensureAtoBin } from './ui/setup';

export let g_lsClient: LanguageClient | undefined;

function _setupLogging(context: vscode.ExtensionContext) {
    const outputChannel = createOutputChannel(SERVER_NAME);
    context.subscriptions.push(outputChannel, registerLogger(outputChannel));

    const changeLogLevel = async (c: vscode.LogLevel, g: vscode.LogLevel) => {
        const level = getLSClientTraceLevel(c, g);
        await g_lsClient?.setTrace(level);
    };

    context.subscriptions.push(
        outputChannel.onDidChangeLogLevel(async (e) => {
            await changeLogLevel(e, vscode.env.logLevel);
        }),
        vscode.env.onDidChangeLogLevel(async (e) => {
            await changeLogLevel(outputChannel.logLevel, e);
        }),
    );

    return outputChannel;
}

function _registerDevStatusButtons(context: vscode.ExtensionContext): void {
    const isDevUiEnabled = process.env.ATOPILE_EXTENSION_DEV_UI === '1';
    if (!isDevUiEnabled) {
        return;
    }

    const reloadWebviewsCmd = vscode.commands.registerCommand('atopile.dev.reloadWebviews', async () => {
        await vscode.commands.executeCommand('workbench.action.webview.reloadWebviewAction');
    });
    const restartExtHostCmd = vscode.commands.registerCommand('atopile.dev.restartExtensionHost', async () => {
        await vscode.commands.executeCommand('workbench.action.restartExtensionHost');
    });

    const reloadWebviewsItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, -100);
    reloadWebviewsItem.text = '$(refresh)$(window)';
    reloadWebviewsItem.tooltip = 'Reload Webviews';
    reloadWebviewsItem.command = 'atopile.dev.reloadWebviews';
    reloadWebviewsItem.backgroundColor = new vscode.ThemeColor('statusBarItem.warningBackground');
    reloadWebviewsItem.show();

    const restartExtHostItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, -101);
    restartExtHostItem.text = '$(refresh)$(tools)';
    restartExtHostItem.tooltip = 'Restart Extension Host';
    restartExtHostItem.command = 'atopile.dev.restartExtensionHost';
    restartExtHostItem.backgroundColor = new vscode.ThemeColor('statusBarItem.warningBackground');
    restartExtHostItem.show();

    context.subscriptions.push(
        reloadWebviewsCmd,
        restartExtHostCmd,
        reloadWebviewsItem,
        restartExtHostItem,
    );
}

class atopileUriHandler implements vscode.UriHandler {
    handleUri(uri: vscode.Uri): vscode.ProviderResult<void> {
        traceInfo(`handleUri: ${uri.toString()}`);
        const path = uri.path

        if (path === "/addPackage") {
            traceInfo('addPackage');
            // e.g. vscode://atopile.atopile/addPackage?packageIdentifier=atopile/esp32
            const queryParams = uri.query.split("&");
            const packageIdentifier = queryParams.find(param => param.startsWith("packageIdentifier="))?.split("=")[1];
            if (packageIdentifier) {
                traceInfo(`packageIdentifier: ${packageIdentifier}`);
                openPackageExplorer('packages/' + packageIdentifier);
            }
        } else if (path === "/openDashboard") {
            traceInfo('openDashboard - redirecting to log viewer panel');
            // Open the log viewer panel instead
            vscode.commands.executeCommand('atopile.logViewer.focus');
        } else if (path === "/restartExtensionHost") {
            traceInfo('restartExtensionHost - restarting extension host');
            vscode.commands.executeCommand('workbench.action.restartExtensionHost');
        } else if (path === "/promptRestart") {
            traceInfo('promptRestart - showing restart prompt');
            vscode.window.showInformationMessage(
                'atopile extension has been updated. Restart to apply changes.',
                'Restart Now',
                'Later'
            ).then(selection => {
                if (selection === 'Restart Now') {
                    vscode.commands.executeCommand('workbench.action.restartExtensionHost');
                }
            });
        }
    }
}

async function handleConfigUpdate(event: vscode.ConfigurationChangeEvent) {
    if (event.affectsConfiguration('atopile.telemetry')) {
        // mirror to CLI config
        const telemetry = vscode.workspace.getConfiguration('atopile').get('telemetry');
        updateConfig(telemetry as boolean);
    }
}


export async function activate(context: vscode.ExtensionContext): Promise<void> {
    const activationTime = Date.now();
    const outputChannel = _setupLogging(context);
    _registerDevStatusButtons(context);
    initTimer();
    traceMilestone('activate()');

    // 1. Register webview providers FIRST
    // If sidebar is open, webview starts loading immediately while servers start
    const extensionVersion = vscode.extensions.getExtension('atopile.atopile')?.packageJSON?.version ?? 'unknown';
    const sidebarProvider = new SidebarProvider(context.extensionUri, extensionVersion, activationTime);
    const logViewerProvider = new LogViewerProvider(context.extensionUri);
    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider(SidebarProvider.viewType, sidebarProvider, { webviewOptions: { retainContextWhenHidden: true } }),
        vscode.window.registerWebviewViewProvider(LogViewerProvider.viewType, logViewerProvider, { webviewOptions: { retainContextWhenHidden: true } }),
        sidebarProvider,
        vscode.window.registerUriHandler(new atopileUriHandler()),
        vscode.workspace.onDidChangeConfiguration(handleConfigUpdate),
        backendServer,
    );
    traceMilestone('providers registered');

    // 2. Initialize menu, telemetry, ato binary detection
    initMenu(context);
    await initializeTelemetry(context);
    traceMilestone('telemetry initialized');
    captureEvent('vsce:startup');
    setUvPathLocal(getExtensionManagedUvPath(context));
    context.subscriptions.push(
        vscode.workspace.onDidChangeConfiguration(async (e) => {
            if (e.affectsConfiguration('atopile.ato') || e.affectsConfiguration('atopile.from')) {
                resetAtoBinFailures();
                onDidChangeAtoBinInfoEvent.fire({ init: false });
            }
        }),
    );
    initServer(context);
    // If backend port is pre-configured (web-ide mode), skip ensureAtoBin —
    // the pre-started backend proves the binary works.
    if (!process.env.ATOPILE_BACKEND_PORT) {
        await ensureAtoBin(context);
        traceMilestone('ensureAtoBin done');
    }

    // 3. Start servers and UI in parallel
    let isInitialStart = true;
    const startLsp = async () => {
        const newClient = await startOrRestartServer(SERVER_ID, SERVER_NAME, outputChannel, g_lsClient);
        g_lsClient = newClient;
        traceMilestone('LSP ready');
        backendServer.sendToWebview({
            type: 'setAtopileInstalling',
            installing: false,
            ...(newClient ? {} : { error: 'Failed to start language server' }),
        });
    };

    const startBackend = async () => {
        const backendSuccess = isInitialStart
            ? await backendServer.startServer()
            : await backendServer.restartServer();
        isInitialStart = false;
        if (!backendSuccess) {
            traceMilestone('backend failed');
        }
    };

    const restartAll = async () => {
        traceInfo('User requested restart, restarting servers...');
        await Promise.all([startLsp(), startBackend()]);
    };

    context.subscriptions.push(
        onNeedsRestart(restartAll),
        onBuildTargetChanged((target: Build | undefined) => {
            g_lsClient?.sendNotification('atopile/didChangeBuildTarget', { buildTarget: target?.entry ?? '' });
        }),
    );

    // LSP starts in background (only needed for .ato editing), backend and UI block activation
    startLsp();
    await Promise.all([ui.activate(context), startBackend()]);

    traceMilestone('activated');
}

export async function deactivate(): Promise<void> {
    // Stop LSP server
    if (g_lsClient) {
        await g_lsClient.stop();
    }

    // Stop backend server (also handled by dispose, but explicit is clearer)
    await backendServer.stopServer();

    deinitializeTelemetry();
}
