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
import { ISettings } from './settings';
import { getEffectiveMemoryLimitBytes, getLSClientTraceLevel, getProcessRssBytes, sleep } from './utilities';
import { isVirtualWorkspace, onDidChangeConfiguration, registerCommand } from './vscodeapi';
import { SERVER_ID } from './constants';
import { resolveAtoBinForWorkspace, onDidChangeAtoBinInfo } from './findbin';
import * as fs from 'fs/promises';
import * as cp from 'child_process';
import { constants as fsc } from 'fs';

const SERVER_STOP_TIMEOUT_MS = 5000;
const SERVER_FORCE_KILL_GRACE_MS = 1000;

let _serverProcess: cp.ChildProcess | undefined;

function setServerProcess(child: cp.ChildProcess | undefined): void {
    _serverProcess = child;
    if (!child) {
        return;
    }

    const clearIfCurrent = () => {
        if (_serverProcess === child) {
            _serverProcess = undefined;
        }
    };
    child.once('exit', clearIfCurrent);
    child.once('error', clearIfCurrent);
}

function isProcessRunning(child: cp.ChildProcess): boolean {
    return child.exitCode === null && child.signalCode === null;
}

async function stopCurrentServerProcess(): Promise<void> {
    const child = _serverProcess;
    if (!child?.pid) {
        return;
    }

    traceError(`Server: stop timed out, terminating LSP pid ${child.pid}`);

    if (isProcessRunning(child)) {
        child.kill('SIGTERM');
    }

    await sleep(SERVER_FORCE_KILL_GRACE_MS);

    if (_serverProcess === child && isProcessRunning(child)) {
        traceError(`Server: force-killing LSP pid ${child.pid}`);
        child.kill('SIGKILL');
    }
}

async function stopLanguageClient(lsClient: LanguageClient): Promise<void> {
    const stopPromise = lsClient.stop();
    const outcome = await Promise.race([
        stopPromise.then(() => 'stopped' as const),
        sleep(SERVER_STOP_TIMEOUT_MS).then(() => 'timeout' as const),
    ]);

    if (outcome === 'timeout') {
        await stopCurrentServerProcess();
        return;
    }

    await stopPromise;
}

export async function getRunningServerMemorySnapshot(): Promise<
    | {
          pid: number;
          rssBytes: number;
          limitBytes: number;
          percentOfLimit: number;
      }
    | undefined
> {
    const pid = _serverProcess?.pid;
    if (!pid) {
        return undefined;
    }

    const rssBytes = await getProcessRssBytes(pid);
    if (rssBytes === undefined) {
        return undefined;
    }

    const limitBytes = await getEffectiveMemoryLimitBytes();
    return {
        pid,
        rssBytes,
        limitBytes,
        percentOfLimit: (rssBytes / limitBytes) * 100,
    };
}

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
    setServerProcess(child);

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
        try {
            await stopLanguageClient(lsClient);
        } catch (error) {
            traceError(`Server: Stop failed: ${String(error)}`);
            await stopCurrentServerProcess();
        }
        _disposables.forEach((d) => d.dispose());
        _disposables = [];
        setServerProcess(undefined);
    }
    const resolved = await resolveAtoBinForWorkspace();
    if (!resolved) {
        traceError(`Server: ato not found. Make sure the extension is properly installed.`);
        return undefined;
    }
    const { settings: workspaceSetting, atoBin } = resolved;
    traceInfo(`Server: Requesting start with ato from ${atoBin.source}.`);
    const newLSClient = await _runServer(atoBin.command, workspaceSetting, serverId, serverName, outputChannel);
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

export function initServer(context: ExtensionContext): void {
    context.subscriptions.push(
        registerCommand(`${SERVER_ID}.restart`, async () => {
            onNeedsRestartEvent.fire();
        }),
        // Automatically restart servers when atopile.ato or atopile.from settings change
        onDidChangeAtoBinInfo((info) => {
            if (!info.init) {
                traceInfo(`Server: ato/from settings changed, triggering restart`);
                onNeedsRestartEvent.fire();
            }
        }),
    );
}
