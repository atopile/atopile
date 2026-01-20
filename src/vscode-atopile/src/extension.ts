// Copyright (c) Microsoft Corporation. All rights reserved.
// Licensed under the MIT License.

import * as vscode from 'vscode';
import { LanguageClient } from 'vscode-languageclient/node';
import { registerLogger, traceInfo, traceLog, traceVerbose } from './common/log/logging';
import { startOrRestartServer, initServer, onNeedsRestart } from './common/server';
import { getLSClientTraceLevel } from './common/utilities';
import { createOutputChannel, get_ide_type } from './common/vscodeapi';
import * as ui from './ui/ui';
import { SERVER_ID, SERVER_NAME } from './common/constants';
import { captureEvent, deinitializeTelemetry, initializeTelemetry, updateConfig } from './common/telemetry';
import { onBuildTargetChanged } from './common/target';
import { Build } from './common/manifest';
import { openPackageExplorer } from './ui/packagexplorer';
import * as llm from './common/llm';
import { appStateManager } from './common/appState';

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

    // Setup Language Server
    const _reStartServer = async () => {
        g_lsClient = await startOrRestartServer(SERVER_ID, SERVER_NAME, outputChannel, g_lsClient);
    };
    context.subscriptions.push(
        onNeedsRestart(async () => {
            await _reStartServer();
        }),
        onBuildTargetChanged(async (target: Build | undefined) => {
            if (g_lsClient) {
                g_lsClient.sendNotification('atopile/didChangeBuildTarget', {
                    buildTarget: target?.entry ?? '',
                });
            }
        }),
    );

    await initServer(context);

    // Backend server connection is now tracked via WebSocket in appStateManager
    // No HTTP polling needed - appStateManager.startListening() handles it

    await ui.activate(context);
    await llm.activate(context);

    context.subscriptions.push(vscode.window.registerUriHandler(new atopileUriHandler()));

    vscode.workspace.onDidChangeConfiguration(handleConfigUpdate);

    traceInfo(`atopile extension activated in IDE: ${get_ide_type()}`);
}

export async function deactivate(): Promise<void> {
    if (g_lsClient) {
        await g_lsClient.stop();
    }


    deinitializeTelemetry();
}
