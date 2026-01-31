import { ConfigurationChangeEvent, Event, EventEmitter, ExtensionContext, window } from 'vscode';
import { initializePython } from './python';
import { getExtensionVersion, onDidChangeConfiguration } from './vscodeapi';
import * as fs from 'fs';
import { getWorkspaceSettings, ISettings } from './settings';
import { traceError, traceInfo, traceVerbose } from './log/logging';
import * as os from 'os';
import * as path from 'path';
import { execFile } from 'child_process';
import { promisify } from 'util';
import * as which from 'which';
import { getProjectRoot } from './utilities';
import { getAtopileWorkspaceFolders } from './vscodeapi';
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

export var g_uv_path_local: string | null = null;

/**
 * Get the default atopile package specifier based on the extension version.
 * Returns a pip-installable specifier like "atopile==0.14.0".
 */
function getDefaultAtoFrom(): string {
    const version = getExtensionVersion();
    if (version === 'unknown') {
        traceError(`[findbin] Could not determine extension version, using 'atopile' without version pin`);
        return 'atopile';
    }
    return `atopile==${version}`;
}

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

/**
 * Get the default atopile binary (extension-managed uv with matching release version).
 * This is the fallback when user-configured options fail.
 */
async function _getDefaultAtoBin(): Promise<AtoBinLocator | null> {
    if (!g_uv_path_local) {
        traceError(`[findbin] Default: No local uv path configured`);
        return null;
    }
    const uvBinLocal = await which(g_uv_path_local, { nothrow: true });
    if (uvBinLocal) {
        const defaultFrom = getDefaultAtoFrom();
        traceInfo(`[findbin] Default: Will install "${defaultFrom}"`);
        return {
            command: [uvBinLocal, 'tool', 'run', '-p', '3.14', '--from', defaultFrom, 'ato'],
            source: 'default',
        };
    }
    traceError(`[findbin] Default: uv binary not found at ${g_uv_path_local}`);
    return null;
}

/**
 * Get the atopile binary from explicit settings path (atopile.ato).
 * Returns null if not configured or path doesn't exist.
 */
async function _getExplicitAtoBin(settings?: ISettings): Promise<AtoBinLocator | null> {
    if (settings?.ato && settings.ato !== '') {
        traceInfo(`[findbin] Explicit: Configured path is "${settings.ato}"`);
        if (fs.existsSync(settings.ato)) {
            traceInfo(`[findbin] Explicit: Path exists`);
            return {
                command: [settings.ato],
                source: 'explicit-path',
            };
        }
        traceError(`[findbin] Explicit: Path does not exist: ${settings.ato}`);
    }
    return null;
}

/**
 * Get the atopile binary using uv with user-configured from path (atopile.from).
 * Returns null if not configured.
 */
async function _getFromSettingAtoBin(settings?: ISettings): Promise<AtoBinLocator | null> {
    if (!settings?.from || settings.from === '') {
        return null;
    }
    if (!g_uv_path_local) {
        traceError(`[findbin] From-setting: No local uv path configured`);
        return null;
    }
    traceInfo(`[findbin] From-setting: Configured source is "${settings.from}"`);
    const uvBinLocal = await which(g_uv_path_local, { nothrow: true });
    if (uvBinLocal) {
        traceInfo(`[findbin] From-setting: Using uv at ${uvBinLocal}`);
        return {
            command: [uvBinLocal, 'tool', 'run', '-p', '3.14', '--from', settings.from, 'ato'],
            source: 'from-setting',
        };
    }
    traceError(`[findbin] From-setting: uv binary not found at ${g_uv_path_local}`);
    return null;
}

/**
 * Run self-check on an atopile binary to verify it works.
 * Returns true if the binary passes self-check, false otherwise.
 */
async function _runSelfCheck(atoBin: AtoBinLocator, timeout_ms: number): Promise<boolean> {
    try {
        const execFileAsync = promisify(execFile);

        const bin = atoBin.command[0];
        const args = [...atoBin.command.slice(1), 'self-check'];
        const fullCommand = `${bin} ${args.join(' ')}`;

        const now = Date.now();
        traceInfo(`[findbin] Self-check: Executing "${fullCommand}"`);
        traceInfo(`[findbin] Self-check: Timeout set to ${timeout_ms / 1000}s`);

        const result = await execFileAsync(bin, args, { timeout: timeout_ms })
            .then(({ stdout, stderr }) => {
                const elapsed = Date.now() - now;
                traceInfo(`[findbin] Self-check: PASSED in ${elapsed}ms`);
                if (stdout.trim()) {
                    traceInfo(`[findbin] Self-check: Output: ${stdout.trim()}`);
                }
                return { err: null, stderr: stderr, stdout: stdout };
            })
            .catch((err: any) => {
                const elapsed_ms = Date.now() - now;
                const timed_out = elapsed_ms > timeout_ms;
                if (timed_out) {
                    traceError(`[findbin] Self-check: FAILED - Timed out after ${elapsed_ms / 1000}s`);
                } else {
                    traceError(`[findbin] Self-check: FAILED after ${elapsed_ms}ms`);
                    if (err.exitCode !== undefined) {
                        traceError(`[findbin] Self-check: Exit code: ${err.exitCode}`);
                    }
                    if (err.stderr) {
                        traceError(`[findbin] Self-check: stderr: ${err.stderr}`);
                    }
                    if (err.stdout) {
                        traceInfo(`[findbin] Self-check: stdout: ${err.stdout}`);
                    }
                }
                return { err: err, stderr: err.stderr, stdout: err.stdout };
            });

        return !result.err;
    } catch (error) {
        traceError(`[findbin] Self-check: Unexpected error: ${error}`);
        return false;
    }
}

export async function getAtoBin(settings?: ISettings, timeout_ms?: number): Promise<AtoBinLocator | null> {
    if (!settings) {
        settings = await getWorkspaceSettings(await getProjectRoot());
    }

    const _timeout_ms = timeout_ms ?? 15_000;

    traceInfo(`[findbin] ========== Starting ato binary search ==========`);

    // 1. Try explicit ato path from settings (atopile.ato)
    traceInfo(`[findbin] [1/3] Checking for explicit ato path (atopile.ato setting)...`);
    const explicitBin = await _getExplicitAtoBin(settings);
    if (explicitBin) {
        traceInfo(`[findbin] [1/3] Found explicit path: ${explicitBin.command.join(' ')}`);
        traceInfo(`[findbin] [1/3] Running self-check...`);
        const explicitWorks = await _runSelfCheck(explicitBin, _timeout_ms);
        if (explicitWorks) {
            traceInfo(`[findbin] [1/3] SUCCESS: Using explicit ato binary from settings`);
            traceInfo(`[findbin] ========== Search complete ==========`);
            return explicitBin;
        }
        traceError(`[findbin] [1/3] FAILED: Explicit ato binary failed self-check`);
    } else {
        traceInfo(`[findbin] [1/3] SKIPPED: No explicit path configured (atopile.ato not set)`);
    }

    // 2. Try uv with user-configured from path (atopile.from)
    traceInfo(`[findbin] [2/3] Checking for user-configured from path (atopile.from setting)...`);
    const fromSettingBin = await _getFromSettingAtoBin(settings);
    if (fromSettingBin) {
        traceInfo(`[findbin] [2/3] Found from setting, will install: ${settings?.from}`);
        traceInfo(`[findbin] [2/3] Command: ${fromSettingBin.command.join(' ')}`);
        traceInfo(`[findbin] [2/3] Running self-check (this may download/install atopile)...`);
        const fromWorks = await _runSelfCheck(fromSettingBin, _timeout_ms);
        if (fromWorks) {
            traceInfo(`[findbin] [2/3] SUCCESS: Using ato from atopile.from setting: ${settings?.from}`);
            traceInfo(`[findbin] ========== Search complete ==========`);
            return fromSettingBin;
        }
        traceError(`[findbin] [2/3] FAILED: ato binary from atopile.from failed self-check`);
    } else {
        traceInfo(`[findbin] [2/3] SKIPPED: No from path configured (atopile.from not set)`);
    }

    // 3. Fall back to default (uv with release matching extension version)
    const defaultFrom = getDefaultAtoFrom();
    traceInfo(`[findbin] [3/3] Falling back to default installation...`);
    traceInfo(`[findbin] [3/3] Default source: ${defaultFrom}`);
    const defaultBin = await _getDefaultAtoBin();
    if (defaultBin) {
        traceInfo(`[findbin] [3/3] Command: ${defaultBin.command.join(' ')}`);
        traceInfo(`[findbin] [3/3] Running self-check (this may download/install atopile)...`);
        const defaultWorks = await _runSelfCheck(defaultBin, _timeout_ms);
        if (defaultWorks) {
            traceInfo(`[findbin] [3/3] SUCCESS: Using default ato installation: ${defaultFrom}`);
            traceInfo(`[findbin] ========== Search complete ==========`);
            return defaultBin;
        }
        traceError(`[findbin] [3/3] FAILED: Default ato binary failed self-check`);
    } else {
        traceError(`[findbin] [3/3] FAILED: Could not create default ato binary (uv not available?)`);
    }

    traceError(`[findbin] ========== Search FAILED: No working ato binary found ==========`);
    return null;
}

export async function resolveAtoBinForWorkspace(): Promise<{
    settings: ISettings;
    atoBin: AtoBinLocator;
} | null> {
    // Try atopile workspace folders first (folders containing ato.yaml)
    const atopileWorkspaces = await getAtopileWorkspaceFolders();
    for (const workspace of atopileWorkspaces) {
        const settings = await getWorkspaceSettings(workspace);
        const atoBin = await getAtoBin(settings);
        if (atoBin) {
            traceVerbose(`Found ato bin using workspace: ${workspace.uri.fsPath}`);
            return { settings, atoBin };
        }
    }

    // Fall back to default project root
    const projectRoot = await getProjectRoot();
    const settings = await getWorkspaceSettings(projectRoot);
    const atoBin = await getAtoBin(settings);
    if (!atoBin) {
        return null;
    }
    return { settings, atoBin };
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

    // Don't show terminal for build commands - user will see output in atopile Logs panel
    const isBuildCommand = subcommand[0] === 'build';
    if (!isBuildCommand) {
        terminal.show();
    }

    return terminal;
}


export async function initAtoBin(context: ExtensionContext): Promise<void> {
    g_uv_path_local = getExtensionManagedUvPath(context);

    context.subscriptions.push(
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
