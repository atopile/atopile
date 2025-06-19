// Copyright (c) Microsoft Corporation. All rights reserved.
// Licensed under the MIT License.

import { ConfigurationChangeEvent, Disposable, env, EventEmitter, ExtensionContext, LogOutputChannel } from 'vscode';
import {
    LanguageClient,
    LanguageClientOptions,
    RevealOutputChannelOn,
    ServerOptions,
} from 'vscode-languageclient/node';
import { traceError, traceInfo, traceVerbose } from './log/logging';
import { getWorkspaceSettings, ISettings } from './settings';
import { getLSClientTraceLevel, getProjectRoot } from './utilities';
import { isVirtualWorkspace, onDidChangeConfiguration, registerCommand } from './vscodeapi';
import { SERVER_ID } from './constants';
import { AtoBinInfo, getAtoBin, initAtoBin, onDidChangeAtoBinInfo } from './findbin';
import * as fs from 'fs';

async function _runServer(
    ato_path: string[],
    settings: ISettings,
    serverId: string,
    serverName: string,
    outputChannel: LogOutputChannel,
): Promise<LanguageClient> {
    const command = ato_path[0];
    const cwd = settings.cwd;
    const args = [...ato_path.slice(1), 'lsp', 'start'];

    traceInfo(`Server run command: ${[command, ...args].join(' ')}`);

    // need to run in non-interactive mode
    const env = { ...process.env, ATO_NON_INTERACTIVE: 'y' };

    const serverOptions: ServerOptions = {
        command,
        args,
        options: { cwd, env: env },
    };

    // Options to control the language client
    const clientOptions: LanguageClientOptions = {
        // Register the server for ato files
        // TODO: why the difference if virtual
        documentSelector: isVirtualWorkspace()
            ? [{ language: 'ato' }]
            : [
                  { scheme: 'file', language: 'ato' },
                  { scheme: 'untitled', language: 'ato' },
                  { scheme: 'vscode-notebook', language: 'ato' },
                  { scheme: 'vscode-notebook-cell', language: 'ato' },
              ],
        outputChannel: outputChannel,
        traceOutputChannel: outputChannel,
        revealOutputChannelOn: RevealOutputChannelOn.Never,
    };

    return new LanguageClient(serverId, serverName, serverOptions, clientOptions);
}

let _disposables: Disposable[] = [];
export async function startOrRestartServer(
    serverId: string,
    serverName: string,
    outputChannel: LogOutputChannel,
    lsClient?: LanguageClient,
): Promise<LanguageClient | undefined> {
    if (lsClient) {
        traceInfo(`Server: Stop requested`);
        await lsClient.stop();
        _disposables.forEach((d) => d.dispose());
        _disposables = [];
    }
    const projectRoot = await getProjectRoot();
    const workspaceSetting = await getWorkspaceSettings(projectRoot);

    const ato_path = await getAtoBin(workspaceSetting);
    if (!ato_path) {
        traceError(`Server: ato not found. Make sure the extension is properly installed.`);
        return undefined;
    }

    const newLSClient = await _runServer(ato_path.command, workspaceSetting, serverId, serverName, outputChannel);
    traceInfo(`Server: Start requested with ato from ${ato_path.source}.`);
    _disposables.push(
        newLSClient.onDidChangeState((e) => {
            traceVerbose(`Server State: ${e.newState}`);
        }),
    );
    try {
        await newLSClient.start();
    } catch (ex) {
        traceError(`Server: Start failed: ${ex}`);
        return undefined;
    }

    const level = getLSClientTraceLevel(outputChannel.logLevel, env.logLevel);
    await newLSClient.setTrace(level);
    return newLSClient;
}

const onNeedsRestartEvent = new EventEmitter<void>();
export const onNeedsRestart = onNeedsRestartEvent.event;

export async function initServer(context: ExtensionContext): Promise<void> {
    context.subscriptions.push(
        onDidChangeAtoBinInfo(async (e: AtoBinInfo) => {
            // No need to fire, already triggering with setImmediate
            if (e.init) {
                return;
            }
            onNeedsRestartEvent.fire();
        }),
        registerCommand(`${SERVER_ID}.restart`, async () => {
            onNeedsRestartEvent.fire();
        }),
    );

    await initAtoBin(context);

    setImmediate(async () => {
        onNeedsRestartEvent.fire();
    });
}
