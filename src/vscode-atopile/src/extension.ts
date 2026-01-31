// Copyright (c) Microsoft Corporation. All rights reserved.
// Licensed under the MIT License.

import * as vscode from 'vscode';
import { LanguageClient } from 'vscode-languageclient/node';
import { registerLogger, traceInfo, traceLog, traceVerbose } from './common/log/logging';
import { startOrRestartServer, initServer, onNeedsRestart } from './common/lspServer';
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
import { SidebarProvider, LogViewerProvider } from './providers';

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
    const outputChannel = _setupLogging(context);
    traceInfo(`Activating atopile extension`);

    // 1. Register webview providers FIRST
    // If sidebar is open, webview starts loading immediately while servers start
    const extensionVersion = vscode.extensions.getExtension('atopile.atopile')?.packageJSON?.version ?? 'unknown';
    const sidebarProvider = new SidebarProvider(context.extensionUri, extensionVersion);
    const logViewerProvider = new LogViewerProvider(context.extensionUri);
    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider(SidebarProvider.viewType, sidebarProvider, { webviewOptions: { retainContextWhenHidden: true } }),
        vscode.window.registerWebviewViewProvider(LogViewerProvider.viewType, logViewerProvider, { webviewOptions: { retainContextWhenHidden: true } }),
        sidebarProvider,
        vscode.window.registerUriHandler(new atopileUriHandler()),
        vscode.workspace.onDidChangeConfiguration(handleConfigUpdate),
        backendServer,
    );

    // 2. Initialize (telemetry, ato binary detection)
    await initializeTelemetry(context);
    captureEvent('vsce:startup');
    await initServer(context);

    // 3. Start servers and UI in parallel
    let isInitialStart = true;
    const startServers = async () => {
        if (!isInitialStart) {
            traceInfo('User requested restart, restarting backend server...');
        }

        const [newClient, backendSuccess] = await Promise.all([
            startOrRestartServer(SERVER_ID, SERVER_NAME, outputChannel, g_lsClient),
            isInitialStart ? backendServer.startServer() : backendServer.restartServer(),
        ]);
        isInitialStart = false;
        g_lsClient = newClient;

        if (backendSuccess) {
            traceInfo('Backend server started successfully');
        } else {
            traceInfo('Backend server failed to start');
        }

        backendServer.sendToWebview({
            type: 'setAtopileInstalling',
            installing: false,
            ...(newClient ? {} : { error: 'Failed to start language server' }),
        });
    };

    context.subscriptions.push(
        onNeedsRestart(startServers),
        onBuildTargetChanged((target: Build | undefined) => {
            g_lsClient?.sendNotification('atopile/didChangeBuildTarget', { buildTarget: target?.entry ?? '' });
        }),
    );

    await Promise.all([ui.activate(context), startServers()]);

    traceInfo(`atopile extension activated in IDE: ${get_ide_type()}`);
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
