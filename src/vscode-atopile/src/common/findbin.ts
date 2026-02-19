import { Event, EventEmitter, ExtensionContext, window } from 'vscode';
import { getExtensionVersion } from './vscodeapi';
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

export function setUvPathLocal(path: string | null): void {
    g_uv_path_local = path;
}

// Global failure tracking to prevent repeated failed attempts
const MAX_FAILED_ATTEMPTS = 3;
let g_failedAttempts = 0;
let g_lastFailureMessage: string | null = null;

/**
 * Reset the failure counter (e.g., when settings change or user requests retry).
 */
export function resetAtoBinFailures(): void {
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
 *
 * Single-quotes each part to protect against shell special characters.
 */
export async function getAtoCommand(settings?: ISettings, subcommand: string[] = []): Promise<string | null> {
    const atoBin = await getAtoBin(settings);
    if (!atoBin) {
        return null;
    }

    const commandParts = atoBin.command.map(c => `'${c}'`);
    if (subcommand.length > 0) {
        commandParts.push(...subcommand.map(c => `'${c}'`));
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
        traceError(`[findbin] No local uv path configured`);
        return null;
    }
    const uvBinLocal = await which(g_uv_path_local, { nothrow: true });
    if (uvBinLocal) {
        const defaultFrom = getDefaultAtoFrom();
        return {
            command: [uvBinLocal, 'tool', 'run', '-p', '3.14', '--from', defaultFrom, 'ato'],
            source: 'default',
        };
    }
    traceError(`[findbin] uv binary not found at ${g_uv_path_local}`);
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
        if (fs.existsSync(normalizedPath)) {
            return {
                command: [normalizedPath],
                source: 'explicit-path',
            };
        }
        traceError(`[findbin] Explicit path does not exist: ${normalizedPath}`);
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
        traceError(`[findbin] from="${settings.from}" but no local uv path configured`);
        return null;
    }
    const uvBinLocal = await which(g_uv_path_local, { nothrow: true });
    if (uvBinLocal) {
        return {
            command: [uvBinLocal, 'tool', 'run', '-p', '3.14', '--from', settings.from, 'ato'],
            source: 'from-setting',
        };
    }
    traceError(`[findbin] uv binary not found at ${g_uv_path_local}`);
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
        const now = Date.now();

        const result = await execFileAsync(bin, args, { timeout: timeout_ms })
            .then(({ stdout, stderr }) => {
                return { err: null, stderr, stdout, elapsed: Date.now() - now };
            })
            .catch((err: any) => {
                return { err, stderr: err.stderr, stdout: err.stdout, elapsed: Date.now() - now };
            });

        if (!result.err) {
            traceVerbose(`[findbin] self-check passed in ${result.elapsed}ms`);
            return true;
        }

        const timed_out = result.elapsed > timeout_ms;
        if (timed_out) {
            traceError(`[findbin] self-check timed out after ${(result.elapsed / 1000).toFixed(1)}s`);
        } else {
            traceError(`[findbin] self-check failed after ${result.elapsed}ms`);
            if (result.err.exitCode !== undefined) {
                traceError(`[findbin] exit code: ${result.err.exitCode}`);
            }
            if (result.stderr) {
                traceError(`[findbin] stderr: ${result.stderr}`);
            }
        }
        return false;
    } catch (error) {
        traceError(`[findbin] self-check error: ${error}`);
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
        traceError(`[findbin] Skipping - already failed ${g_failedAttempts} times: ${g_lastFailureMessage}`);
        return null;
    }

    if (!settings) {
        settings = await getWorkspaceSettings(await getProjectRoot());
    }

    const _timeout_ms = timeout_ms ?? 120_000;
    const hasExplicitPath = !!(settings?.ato && settings.ato !== '');
    const hasFromSetting = !!(settings?.from && settings.from !== '');

    // 1. If user configured explicit path (atopile.ato), use ONLY that - no fallback
    if (hasExplicitPath) {
        const explicitBin = await _getExplicitAtoBin(settings);
        if (!explicitBin) {
            g_lastFailureMessage = `path "${settings.ato}" does not exist`;
            g_failedAttempts++;
            traceError(`[findbin] FATAL: atopile.ato="${settings.ato}" does not exist`);
            window.showErrorMessage(`ato binary not found at configured path. Check atopile.ato in settings.`);
            return null;
        }

        if (await _runSelfCheck(explicitBin, _timeout_ms)) {
            traceInfo(`[findbin] OK: ${explicitBin.command[0]} (${explicitBin.source})`);
            return explicitBin;
        }

        g_lastFailureMessage = `path "${settings.ato}" failed self-check`;
        g_failedAttempts++;
        traceError(`[findbin] FATAL: atopile.ato="${settings.ato}" failed self-check`);
        window.showErrorMessage(`ato binary at configured path is not working. Check atopile.ato in settings.`);
        return null;
    }

    // 2. If user configured from setting (atopile.from), use ONLY that - no fallback
    if (hasFromSetting) {
        const fromSettingBin = await _getFromSettingAtoBin(settings);
        if (!fromSettingBin) {
            g_lastFailureMessage = `atopile.from set but uv is not available`;
            g_failedAttempts++;
            traceError(`[findbin] FATAL: atopile.from="${settings.from}" but uv is not available`);
            window.showErrorMessage(`Unable to connect to atopile backend.`);
            return null;
        }

        traceInfo(`[findbin] Installing from "${settings.from}" (this may download atopile)...`);
        if (await _runSelfCheck(fromSettingBin, _timeout_ms)) {
            traceInfo(`[findbin] OK: ${fromSettingBin.command.join(' ')} (${fromSettingBin.source})`);
            return fromSettingBin;
        }

        g_lastFailureMessage = `"${settings.from}" failed to install or run`;
        g_failedAttempts++;
        traceError(`[findbin] FATAL: atopile.from="${settings.from}" failed to install or run`);
        window.showErrorMessage(`Unable to connect to atopile backend.`);
        return null;
    }

    // 3. No user configuration - try ato on PATH first (e.g. Docker with pre-installed ato)
    traceInfo(`[findbin] No user configuration, checking PATH for ato...`);
    const atoOnPath = await which('ato', { nothrow: true });
    if (atoOnPath) {
        traceInfo(`[findbin] Found ato on PATH: ${atoOnPath}`);
        const pathBin: AtoBinLocator = { command: [atoOnPath], source: 'system-path' };
        const pathWorks = await _runSelfCheck(pathBin, _timeout_ms);
        if (pathWorks) {
            traceInfo(`[findbin] SUCCESS: Using ato from PATH: ${atoOnPath}`);
            traceInfo(`[findbin] ========== Search complete ==========`);
            return pathBin;
        }
        traceInfo(`[findbin] ato on PATH failed self-check, falling back to default`);
    }

    // 4. Fall back to extension-managed uv installation
    const defaultFrom = getDefaultAtoFrom();
    traceInfo(`[findbin] Using default mode (extension-managed)`);
    traceInfo(`[findbin] Default source: ${defaultFrom}`);


    const defaultBin = await _getDefaultAtoBin();
    if (!defaultBin) {
        g_lastFailureMessage = `uv is not available for default installation`;
        g_failedAttempts++;
        traceError(`[findbin] FATAL: Cannot install ${defaultFrom} - uv is not available`);
        window.showErrorMessage(`Unable to connect to atopile backend.`);
        return null;
    }

    traceInfo(`[findbin] Installing ${defaultFrom} (this may download atopile)...`);
    if (await _runSelfCheck(defaultBin, _timeout_ms)) {
        traceInfo(`[findbin] OK: ${defaultBin.command.join(' ')} (${defaultBin.source})`);
        return defaultBin;
    }

    g_lastFailureMessage = `Default installation (${defaultFrom}) failed`;
    g_failedAttempts++;
    traceError(`[findbin] FATAL: Default installation of ${defaultFrom} failed`);
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
 * In web-ide mode, the user shell is set to restricted-shell.sh which blocks
 * interactive use.  Force /bin/bash so programmatic terminal commands work.
 * On other platforms, omit shellPath so VS Code uses the user's default shell.
 */
export function getTerminalShellPath(): string | undefined {
    const isWebIde =
        process.env.WEB_IDE_MODE === '1' ||
        Boolean(process.env.OPENVSCODE_SERVER_ROOT);
    return isWebIde ? '/bin/bash' : undefined;
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
        shellPath: getTerminalShellPath(),
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
                shellPath: getTerminalShellPath(),
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
