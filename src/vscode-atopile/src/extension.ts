// Copyright (c) Microsoft Corporation. All rights reserved.
// Licensed under the MIT License.

import * as vscode from 'vscode';
import { LanguageClient } from 'vscode-languageclient/node';
import { registerLogger, traceInfo, traceLog, traceVerbose } from './common/log/logging';
import { startOrRestartServer, initServer, onNeedsRestart } from './common/server';
import { getLSClientTraceLevel } from './common/utilities';
import { createOutputChannel } from './common/vscodeapi';
import * as ui from './ui/ui';
import { SERVER_ID, SERVER_NAME } from './common/constants';

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

    // Setup Language Server
    const _reStartServer = async () => {
        g_lsClient = await startOrRestartServer(SERVER_ID, SERVER_NAME, outputChannel, g_lsClient);
    };
    context.subscriptions.push(
        onNeedsRestart(async () => {
            await _reStartServer();
        }),
    );

    await initServer(context);

    ui.activate(context);
}

export async function deactivate(): Promise<void> {
    if (g_lsClient) {
        await g_lsClient.stop();
    }
}
