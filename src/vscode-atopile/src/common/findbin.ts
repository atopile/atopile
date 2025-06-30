import { ConfigurationChangeEvent, Disposable, Event, EventEmitter, ExtensionContext, env, window } from 'vscode';
import { onDidChangePythonInterpreter, IInterpreterDetails, initializePython } from './python';
import { onDidChangeConfiguration } from './vscodeapi';
import * as fs from 'fs';
import { getWorkspaceSettings, ISettings } from './settings';
import { traceError, traceInfo, traceVerbose } from './log/logging';
import * as os from 'os';
import * as path from 'path';
import { execFile } from 'child_process';
import { promisify } from 'util';
import * as which from 'which';
import { getProjectRoot } from './utilities';
import * as vscode from 'vscode';

export interface AtoBinInfo {
    init: boolean;
}

interface AtoBinLocator {
    command: string[];
    source: string;
}

export const onDidChangeAtoBinInfoEvent = new EventEmitter<AtoBinInfo>();
export const onDidChangeAtoBinInfo: Event<AtoBinInfo> = onDidChangeAtoBinInfoEvent.event;

const UV_ATO_VERSION = 'atopile';

export var g_uv_path_local: string | null = null;
let g_pyAtoBin: string | null = null;

export function getExtensionManagedUvPath(context: ExtensionContext): string | null {
    // Determine executable name based on platform
    const uvExecutableName = os.platform() === 'win32' ? 'uv.exe' : 'uv';
    return path.join(context.globalStorageUri.fsPath, 'uv-bin', uvExecutableName);
}

async function _getAtoBin(settings?: ISettings): Promise<AtoBinLocator | null> {
    // event based load
    if (settings?.ato && settings.ato !== '') {
        if (fs.existsSync(settings.ato)) {
            traceVerbose(`Using ato bin from settings: ${settings.ato}`);
            return {
                command: [settings.ato],
                source: 'settings',
            };
        }
        traceError(`Invalid atopile.ato path in settings: ${settings.ato} not found.`);
    }

    // event based python && lazy ato
    // Disabled, too buggy
    // if (g_pyAtoBin && fs.existsSync(g_pyAtoBin)) {
    //     traceInfo(`Using ato bin from venv: ${g_pyAtoBin}`);
    //     return {
    //         command: [g_pyAtoBin],
    //         source: 'venv',
    //     };
    // }

    // Check extension managed uv

    // lazy load
    // Using system (user-managed) ato is breaking too often to maintain
    // let sysAtoBin = await which('ato', { nothrow: true });
    // if (sysAtoBin) {
    //     traceVerbose(`Using ato bin from system PATH: ${sysAtoBin}`);
    //     return {
    //         command: [sysAtoBin],
    //         source: 'system',
    //     };
    // }

    // Using system uv introduces more branching e.g outdated system uv / python
    // let uvBin = await which('uv', { nothrow: true });
    // if (uvBin) {
    //     traceInfo(`Using system uv to run ato: ${uvBin}`);
    //     return {
    //         command: [uvBin, 'tool', 'run', '--from', UV_ATO_VERSION, 'ato'],
    //         source: 'system-uv',
    //     };
    // }

    if (g_uv_path_local) {
        const uvBinLocal = await which(g_uv_path_local, { nothrow: true });
        if (uvBinLocal) {
            let from = UV_ATO_VERSION;
            if (settings?.from && settings.from !== '') {
                from = settings.from;
            }
            traceVerbose(`Using local uv to run ato: ${uvBinLocal}`);
            traceVerbose(`Using from: ${from}`);
            return {
                // TODO don't hardcode python version lol
                // @python3.14
                command: [uvBinLocal, 'tool', 'run', '-p', '3.13', '--from', from, 'ato'],
                source: 'local-uv',
            };
        }
    }

    traceVerbose(`No ato bin found.`);
    return null;
}

export async function getAtoBin(settings?: ISettings, timeout_ms?: number): Promise<AtoBinLocator | null> {
    // TODO: consider raising exceptions instead of return null pattern
    if (!settings) {
        settings = await getWorkspaceSettings(await getProjectRoot());
    }
    const atoBin = await _getAtoBin(settings);
    if (!atoBin) {
        return null;
    }

    // Check if ato is working by running the version command
    try {
        const execFileAsync = promisify(execFile);

        const bin = atoBin.command[0];
        const args = [...atoBin.command.slice(1), 'self-check'];

        const _timeout_ms = timeout_ms ?? 15_000;
        const now = Date.now();

        // run with 30s timeout (uv pulling might take long)
        const result = await execFileAsync(bin, args, { timeout: _timeout_ms })
            .then(({ stdout, stderr }) => ({ err: null, stderr: stderr, stdout: stdout }))
            .catch((err: any) => {
                const command = `${bin} ${args.join(' ')}`;
                const elapsed_ms = Date.now() - now;
                const timed_out = elapsed_ms > _timeout_ms;
                let details = '';
                if (timed_out) {
                    details = `Error: Timed out after ${elapsed_ms / 1000}s`;
                } else if (err.stderr !== '' || err.stdout !== '' || err.exitCode !== undefined) {
                    details = `code: ${err.exitCode}\nstderr: ${err.stderr}\nstdout: ${err.stdout}`;
                }
                traceError(
                    `Error executing ato self-check for ato from ${atoBin.source}\ncommand: ${command}\n${details}`,
                );
                return { err: err, stderr: err.stderr, stdout: err.stdout };
            });

        if (result.err) {
            return null;
        }
    } catch (error) {
        traceError(`Error running ato: ${error}`);
        return null;
    }

    return atoBin;
}

export async function getAtoAlias(settings?: ISettings, timeout_ms?: number): Promise<string | null> {
    const atoBin = await getAtoBin(settings, timeout_ms);
    if (!atoBin) {
        return null;
    }

    const in_powershell =
        os.platform() === 'win32' && vscode.env.shell && vscode.env.shell.toLowerCase().includes('powershell');

    let atoAlias = atoBin.command.map((c) => `'${c}'`).join(' ');

    // if running in powershell, need to add & to the command
    if (in_powershell) {
        atoAlias = '& ' + atoAlias;
    }

    let alias = `alias ato="${atoAlias}"`;
    if (in_powershell) {
        alias = `Function ato { ${atoAlias} @args }`;
    }

    return alias;
}

export async function runAtoCommandInTerminal(
    terminal_or_name: string | vscode.Terminal,
    cwd: string | undefined,
    subcommand: string[],
    hideFromUser: boolean,
): Promise<vscode.Terminal> {
    const alias = await getAtoAlias();
    if (alias === null) {
        throw new Error('Ato bin not found');
    }

    let terminal: vscode.Terminal;
    if (typeof terminal_or_name === 'string') {
        terminal = vscode.window.createTerminal({
            name: `ato: ${terminal_or_name}`,
            cwd: cwd,
            hideFromUser: hideFromUser,
        });
    } else {
        terminal = terminal_or_name;
    }

    terminal.sendText(alias);
    terminal.sendText(`ato ${subcommand.map((c) => `'${c}'`).join(' ')}`);
    terminal.show();
    return terminal;
}

/**
 * Sets up ato alias in a newly created terminal
 */
async function setupAtoAliasInTerminal(terminal: any): Promise<void> {
    let alias = await getAtoAlias();
    if (alias === null) {
        return;
    }
    terminal.sendText(alias);
}

export async function initAtoBin(context: ExtensionContext): Promise<void> {
    g_uv_path_local = getExtensionManagedUvPath(context);

    context.subscriptions.push(
        onDidChangePythonInterpreter(async (e: IInterpreterDetails) => {
            const binDir = e.bin_dir;
            if (!binDir) {
                return;
            }
            g_pyAtoBin = binDir + '/ato';
            if (!fs.existsSync(g_pyAtoBin)) {
                traceVerbose(`ato bin not found in venv: ${g_pyAtoBin}`);
                return;
            }
            traceVerbose(`findbin: ato bin found in venv: ${g_pyAtoBin}`);
            onDidChangeAtoBinInfoEvent.fire({ init: e.init });
        }),
        onDidChangeConfiguration(async (e: ConfigurationChangeEvent) => {
            if (e.affectsConfiguration(`atopile.ato`) || e.affectsConfiguration('atopile.from')) {
                onDidChangeAtoBinInfoEvent.fire({ init: false });
            }
        }),
        // Set up ato alias when new terminals are created
        window.onDidOpenTerminal(async (terminal) => {
            traceVerbose(`Terminal created: ${terminal.name}, setting up ato alias`);
            await setupAtoAliasInTerminal(terminal);
        }),
        // rerun alias in all terminals
        onDidChangeAtoBinInfo(async (_: AtoBinInfo) => {
            for (const terminal of vscode.window.terminals) {
                await setupAtoAliasInTerminal(terminal);
            }
        }),
    );

    await initializePython(context);

    let ato_bin = await getAtoBin();
    if (ato_bin) {
        traceInfo(`findbin: ato bin found: ${ato_bin.source}. Firing event.`);
        onDidChangeAtoBinInfoEvent.fire({ init: true });
    }
}
