// Copyright (c) Microsoft Corporation. All rights reserved.
// Licensed under the MIT License.

import { Disposable, env, EventEmitter, ExtensionContext, LogOutputChannel } from 'vscode';
import {
    CloseAction,
    ErrorAction,
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
import * as fs from 'fs/promises';
import * as cp from 'child_process';
import { constants as fsc } from 'fs';

async function trySpawn(
    command: string,
    args: string[],
    options: cp.SpawnOptions,
): Promise<cp.ChildProcess | undefined> {
    try {
        await fs.access(command, fsc.X_OK);
    } catch {
        return undefined;
    }

    const child = cp.spawn(command, args, { ...options, stdio: 'pipe' });
    let exited = false;
    child.once('error', () => {
        exited = true;
    });
    child.once('exit', () => {
        exited = true;
    });

    let stderr = '';

    child.stderr.on('data', (data) => {
        stderr += data;
    });

    // Wait for either the process to exit or a 2 second timeout, whichever comes first.
    await Promise.race([
        new Promise<void>((resolve) => {
            if (exited) {
                resolve();
            } else {
                child.once('exit', resolve);
                child.once('error', resolve);
            }
        }),
        new Promise((resolve) => setTimeout(resolve, 2000)),
    ]);
    if (exited) {
        traceError(`LSP stderr: ${stderr}`);
        return undefined;
    }
    return child;
}

async function _runServer(
    ato_path: string[],
    settings: ISettings,
    serverId: string,
    serverName: string,
    outputChannel: LogOutputChannel,
): Promise<LanguageClient | undefined> {
    const command = ato_path[0];
    const args = [...ato_path.slice(1), 'lsp', 'start'];
    const envp = { ...process.env, ATO_NON_INTERACTIVE: 'y' };

    // 🔑 preflight + self-spawn
    traceInfo(`LSP: Running ${command} ${args.join(' ')} in ${settings.cwd}.`);
    const child = await trySpawn(command, args, { cwd: settings.cwd, env: envp });
    if (!child) {
        traceError(`LSP: preflight/spawn failed; not starting client.`);
        return undefined; // no client => no “couldn't create connection” toast
    }

    // Hand the already-running process to the client (never rejects)
    const serverOptions: ServerOptions = () => Promise.resolve(child);

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
        // Don't be annoying on LSP crash
        revealOutputChannelOn: RevealOutputChannelOn.Never,
        connectionOptions: {
            maxRestartCount: 0,
        },
        errorHandler: {
            error: () => ({ action: ErrorAction.Shutdown, handled: true }),
            closed: () => ({ action: CloseAction.DoNotRestart, handled: true }),
        },
        initializationFailedHandler: () => false, // don’t try to re-init on init failure
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
    traceInfo(`Server: Requesting start with ato from ${ato_path.source}.`);
    const newLSClient = await _runServer(ato_path.command, workspaceSetting, serverId, serverName, outputChannel);
    if (!newLSClient) {
        traceError(`Server: Could not start server.`);
        return undefined;
    }

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
