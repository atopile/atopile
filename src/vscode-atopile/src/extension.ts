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
import { appStateManager, initAtopileSettingsSync } from './common/appState';
import { backendServer } from './common/backendServer';

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

    await initializeTelemetry(context);
    captureEvent('vsce:startup');

    // Setup Language Server and Backend Server
    let isInitialStart = true;

    const _reStartServers = async () => {
        // Restart LSP server
        const newClient = await startOrRestartServer(SERVER_ID, SERVER_NAME, outputChannel, g_lsClient);
        g_lsClient = newClient;

        // On initial start, start backend server
        // On user-initiated restarts, restart backend server if configured
        if (isInitialStart) {
            isInitialStart = false;
            const success = await backendServer.startServer();
            if (success) {
                traceInfo('Backend server started successfully');
            } else {
                traceInfo('Backend server failed to start');
            }
        } else {
            traceInfo('User requested restart, restarting backend server...');
            const success = await backendServer.restartServer();
            if (!success) {
                traceInfo('Backend server restart failed');
            }
        }

        // Notify backend that installation/restart completed
        if (newClient) {
            appStateManager.sendAction('setAtopileInstalling', { installing: false });
        } else {
            appStateManager.sendAction('setAtopileInstalling', {
                installing: false,
                error: 'Failed to start language server'
            });
        }
    };

    context.subscriptions.push(
        onNeedsRestart(async () => {
            await _reStartServers();
        }),
        onBuildTargetChanged(async (target: Build | undefined) => {
            if (g_lsClient) {
                g_lsClient.sendNotification('atopile/didChangeBuildTarget', {
                    buildTarget: target?.entry ?? '',
                });
            }
        }),
        // Register backend server for cleanup on deactivate
        backendServer,
    );

    await initServer(context);
    await _reStartServers();

    await ui.activate(context);
    await llm.activate(context);

    // Sync atopile settings from UI to extension (manual restart required to apply)
    context.subscriptions.push(initAtopileSettingsSync(context));

    context.subscriptions.push(vscode.window.registerUriHandler(new atopileUriHandler()));

    vscode.workspace.onDidChangeConfiguration(handleConfigUpdate);

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
