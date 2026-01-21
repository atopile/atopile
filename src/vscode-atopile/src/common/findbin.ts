import { ConfigurationChangeEvent, Event, EventEmitter, ExtensionContext, window } from 'vscode';
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

// Track the build terminal for reuse
let g_buildTerminal: vscode.Terminal | undefined;

/**
 * Get the full ato command as a string (for running in terminals).
 * Unlike getAtoBin(), this returns the command ready to be sent to a terminal.
 */
export async function getAtoCommand(settings?: ISettings, subcommand: string[] = []): Promise<string | null> {
    const atoBin = await getAtoBin(settings);
    if (!atoBin) {
        return null;
    }

    // Build the full command string with proper quoting
    const commandParts = atoBin.command.map(c => c.includes(' ') ? `'${c}'` : c);
    if (subcommand.length > 0) {
        commandParts.push(...subcommand.map(c => c.includes(' ') ? `'${c}'` : c));
    }
    return commandParts.join(' ');
}

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


/**
 * Check if a terminal is still valid (not disposed).
 */
function isTerminalValid(terminal: vscode.Terminal | undefined): terminal is vscode.Terminal {
    if (!terminal) return false;
    // Check if terminal is still in the list of active terminals
    return vscode.window.terminals.includes(terminal);
}

/**
 * Get or create the build terminal, reusing if it still exists.
 */
function getOrCreateBuildTerminal(name: string, cwd: string | undefined, hideFromUser: boolean): vscode.Terminal {
    // Reuse existing build terminal if it's still valid
    if (isTerminalValid(g_buildTerminal)) {
        // Send Ctrl+C to interrupt any running process, then clear
        g_buildTerminal.sendText('\x03'); // Ctrl+C
        return g_buildTerminal;
    }

    // Create new terminal and track it
    g_buildTerminal = vscode.window.createTerminal({
        name: `ato: ${name}`,
        cwd: cwd,
        hideFromUser: hideFromUser,
    });

    return g_buildTerminal;
}

export async function runAtoCommandInTerminal(
    terminal_or_name: string | vscode.Terminal,
    cwd: string | undefined,
    subcommand: string[],
    hideFromUser: boolean,
): Promise<vscode.Terminal> {
    // Get the full command to run (includes ato binary path + subcommand)
    const fullCommand = await getAtoCommand(undefined, subcommand);
    if (fullCommand === null) {
        throw new Error('Ato bin not found');
    }

    let terminal: vscode.Terminal;
    if (typeof terminal_or_name === 'string') {
        // Check if this is a build command - reuse terminal for builds
        const isBuildCommand = subcommand[0] === 'build';
        if (isBuildCommand) {
            terminal = getOrCreateBuildTerminal(terminal_or_name, cwd, hideFromUser);
        } else {
            terminal = vscode.window.createTerminal({
                name: `ato: ${terminal_or_name}`,
                cwd: cwd,
                hideFromUser: hideFromUser,
            });
        }
    } else {
        terminal = terminal_or_name;
    }

    // Run the full command directly (no alias setup needed)
    terminal.sendText(fullCommand);

    // Don't show terminal for build commands - user will see output in Atopile Logs panel
    const isBuildCommand = subcommand[0] === 'build';
    if (!isBuildCommand) {
        terminal.show();
    }

    return terminal;
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
    );

    await initializePython(context);

    let ato_bin = await getAtoBin();
    if (ato_bin) {
        traceInfo(`findbin: ato bin found: ${ato_bin.source}. Firing event.`);
        onDidChangeAtoBinInfoEvent.fire({ init: true });
    }
}
