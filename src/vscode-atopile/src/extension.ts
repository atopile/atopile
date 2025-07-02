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
import { captureEvent, deinitializeTelemetry, initializeTelemetry } from './common/telemetry';
import { onBuildTargetChanged } from './common/target';
import { Build } from './common/manifest';
import * as llm from './common/llm';

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

    await ui.activate(context);
    await llm.activate(context);

    traceInfo(`atopile extension activated in IDE: ${get_ide_type()}`);
}

export async function deactivate(): Promise<void> {
    if (g_lsClient) {
        await g_lsClient.stop();
    }

    deinitializeTelemetry();
}
