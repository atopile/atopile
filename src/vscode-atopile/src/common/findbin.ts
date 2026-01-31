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

// Global failure tracking to prevent repeated failed attempts
const MAX_FAILED_ATTEMPTS = 3;
let g_failedAttempts = 0;
let g_lastFailureMessage: string | null = null;

/**
 * Reset the failure counter (e.g., when settings change or user requests retry).
 */
export function resetAtoBinFailures(): void {
    traceInfo(`[findbin] Resetting failure counter (was ${g_failedAttempts})`);
    g_failedAttempts = 0;
    g_lastFailureMessage = null;
}

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
 * Normalize a path to be absolute.
 * Handles common mistakes like forgetting the leading / on macOS/Linux.
 */
function normalizePath(inputPath: string): string {
    // Already absolute on Unix
    if (inputPath.startsWith('/')) {
        return inputPath;
    }
    // Already absolute on Windows (e.g., C:\...)
    if (/^[a-zA-Z]:/.test(inputPath)) {
        return inputPath;
    }
    // Common mistake: path looks like it should be absolute but missing leading /
    // e.g., "Users/..." should be "/Users/..."
    if (inputPath.startsWith('Users/') || inputPath.startsWith('home/') || inputPath.startsWith('opt/')) {
        traceInfo(`[findbin] Path "${inputPath}" appears to be missing leading /, adding it`);
        return '/' + inputPath;
    }
    // Return as-is for other cases (truly relative paths, ~, etc.)
    return inputPath;
}

/**
 * Get the atopile binary from explicit settings path (atopile.ato).
 * Returns null if not configured or path doesn't exist.
 */
async function _getExplicitAtoBin(settings?: ISettings): Promise<AtoBinLocator | null> {
    if (settings?.ato && settings.ato !== '') {
        const normalizedPath = normalizePath(settings.ato);
        traceInfo(`[findbin] Explicit: Configured path is "${settings.ato}"${normalizedPath !== settings.ato ? ` (normalized to "${normalizedPath}")` : ''}`);
        if (fs.existsSync(normalizedPath)) {
            traceInfo(`[findbin] Explicit: Path exists`);
            return {
                command: [normalizedPath],
                source: 'explicit-path',
            };
        }
        traceError(`[findbin] Explicit: Path does not exist: ${normalizedPath}`);
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

/**
 * Get the atopile binary to use.
 *
 * STRICT BEHAVIOR - No silent fallbacks:
 * - If user configured atopile.ato and it fails → ERROR (no fallback)
 * - If user configured atopile.from and it fails → ERROR (no fallback)
 * - Only use default if nothing is explicitly configured
 * - If default fails → ERROR
 *
 * This ensures users know immediately when their configuration is broken,
 * rather than silently using a different version.
 */
export async function getAtoBin(settings?: ISettings, timeout_ms?: number): Promise<AtoBinLocator | null> {
    // Check if we've already failed too many times
    if (g_failedAttempts >= MAX_FAILED_ATTEMPTS) {
        traceError(`[findbin] Skipping search - already failed ${g_failedAttempts} times. Last error: ${g_lastFailureMessage}`);
        return null;
    }

    if (!settings) {
        settings = await getWorkspaceSettings(await getProjectRoot());
    }

    // Longer timeout for initial install (uv may need to download)
    const _timeout_ms = timeout_ms ?? 120_000;

    traceInfo(`[findbin] ========== Starting ato binary search (attempt ${g_failedAttempts + 1}/${MAX_FAILED_ATTEMPTS}) ==========`);
    traceInfo(`[findbin] Timeout: ${_timeout_ms / 1000}s`);

    // Check what the user has configured
    const hasExplicitPath = !!(settings?.ato && settings.ato !== '');
    const hasFromSetting = !!(settings?.from && settings.from !== '');

    traceInfo(`[findbin] User configuration: ato=${hasExplicitPath ? settings.ato : '(not set)'}, from=${hasFromSetting ? settings.from : '(not set)'}`);

    // 1. If user configured explicit path (atopile.ato), use ONLY that - no fallback
    if (hasExplicitPath) {
        traceInfo(`[findbin] Using explicit path mode (atopile.ato is set)`);
        const explicitBin = await _getExplicitAtoBin(settings);
        if (!explicitBin) {
            g_lastFailureMessage = `atopile.ato path "${settings.ato}" does not exist`;
            g_failedAttempts++;
            traceError(`[findbin] FATAL: atopile.ato is set to "${settings.ato}" but path does not exist`);
            traceError(`[findbin] Please check your atopile.ato setting or clear it to use the default`);
            window.showErrorMessage(`ato binary not found at configured path. Check atopile.ato in settings.`);
            return null;
        }

        traceInfo(`[findbin] Found explicit path: ${explicitBin.command.join(' ')}`);
        traceInfo(`[findbin] Running self-check...`);
        const explicitWorks = await _runSelfCheck(explicitBin, _timeout_ms);
        if (explicitWorks) {
            traceInfo(`[findbin] SUCCESS: Using explicit ato binary from settings`);
            traceInfo(`[findbin] ========== Search complete ==========`);
            return explicitBin;
        }

        g_lastFailureMessage = `atopile.ato binary "${settings.ato}" failed self-check`;
        g_failedAttempts++;
        traceError(`[findbin] FATAL: atopile.ato path "${settings.ato}" failed self-check`);
        traceError(`[findbin] The configured binary is not working. Please check your atopile.ato setting.`);
        window.showErrorMessage(`ato binary at configured path is not working. Check atopile.ato in settings.`);
        return null;
    }

    // 2. If user configured from setting (atopile.from), use ONLY that - no fallback
    if (hasFromSetting) {
        traceInfo(`[findbin] Using from-setting mode (atopile.from is set to "${settings.from}")`);
        const fromSettingBin = await _getFromSettingAtoBin(settings);
        if (!fromSettingBin) {
            g_lastFailureMessage = `atopile.from set but uv is not available`;
            g_failedAttempts++;
            traceError(`[findbin] FATAL: atopile.from is set but uv is not available`);
            traceError(`[findbin] Please ensure uv is installed or clear atopile.from to use the default`);
            window.showErrorMessage(`Unable to connect to atopile backend.`);
            return null;
        }

        traceInfo(`[findbin] Will install: ${settings.from}`);
        traceInfo(`[findbin] Command: ${fromSettingBin.command.join(' ')}`);
        traceInfo(`[findbin] Running self-check (this may download/install atopile)...`);
        const fromWorks = await _runSelfCheck(fromSettingBin, _timeout_ms);
        if (fromWorks) {
            traceInfo(`[findbin] SUCCESS: Using ato from atopile.from setting: ${settings.from}`);
            traceInfo(`[findbin] ========== Search complete ==========`);
            return fromSettingBin;
        }

        g_lastFailureMessage = `atopile.from "${settings.from}" failed to install or run`;
        g_failedAttempts++;
        traceError(`[findbin] FATAL: atopile.from "${settings.from}" failed to install or run`);
        traceError(`[findbin] Please check your atopile.from setting or clear it to use the default`);
        window.showErrorMessage(`Unable to connect to atopile backend.`);
        return null;
    }

    // 3. No user configuration - use default (extension-managed)
    const defaultFrom = getDefaultAtoFrom();
    traceInfo(`[findbin] Using default mode (no user configuration)`);
    traceInfo(`[findbin] Default source: ${defaultFrom}`);

    const defaultBin = await _getDefaultAtoBin();
    if (!defaultBin) {
        g_lastFailureMessage = `uv is not available for default installation`;
        g_failedAttempts++;
        traceError(`[findbin] FATAL: Cannot create default ato binary - uv is not available`);
        traceError(`[findbin] The extension requires uv to be installed. Please restart the extension.`);
        window.showErrorMessage(`Unable to connect to atopile backend.`);
        return null;
    }

    traceInfo(`[findbin] Command: ${defaultBin.command.join(' ')}`);
    traceInfo(`[findbin] Running self-check (this may download/install atopile)...`);
    const defaultWorks = await _runSelfCheck(defaultBin, _timeout_ms);
    if (defaultWorks) {
        traceInfo(`[findbin] SUCCESS: Using default ato installation: ${defaultFrom}`);
        traceInfo(`[findbin] ========== Search complete ==========`);
        return defaultBin;
    }

    g_lastFailureMessage = `Default atopile installation (${defaultFrom}) failed`;
    g_failedAttempts++;
    traceError(`[findbin] FATAL: Default atopile installation failed`);
    traceError(`[findbin] Failed to install/run ${defaultFrom}`);
    window.showErrorMessage(`Unable to connect to atopile backend.`);
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
                // Reset failure counter when settings change so we can retry
                resetAtoBinFailures();
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
