import { ConfigurationChangeEvent, Disposable, Event, EventEmitter, ExtensionContext } from 'vscode';
import { onDidChangePythonInterpreter, IInterpreterDetails, initializePython } from './python';
import { onDidChangeConfiguration } from './vscodeapi';
import * as fs from 'fs';
import { ISettings } from './settings';
import { traceError, traceInfo, traceVerbose } from './log/logging';
import * as os from 'os';
import * as path from 'path';
import { execFile } from 'child_process';
import { promisify } from 'util';
import * as which from 'which';

export interface AtoBinInfo {
    init: boolean;
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

async function _getAtoBin(settings?: ISettings): Promise<string[] | null> {
    // event based load
    if (settings?.ato) {
        if (fs.existsSync(settings.ato)) {
            traceInfo(`Using ato bin from settings: ${settings.ato}`);
            return [settings.ato];
        }
        traceError(`Invalid atopile.ato path in settings: ${settings.ato} not found.`);
    }

    // event based python && lazy ato
    if (g_pyAtoBin && fs.existsSync(g_pyAtoBin)) {
        traceInfo(`Using ato bin from venv: ${g_pyAtoBin}`);
        return [g_pyAtoBin];
    }

    // Check extension managed uv

    // lazy load
    let sysAtoBin = await which('ato', { nothrow: true });
    if (sysAtoBin) {
        traceInfo(`Using ato bin from system PATH: ${sysAtoBin}`);
        return [sysAtoBin];
    }
    let uvBin = await which('uv', { nothrow: true });
    if (!uvBin && g_uv_path_local) {
        uvBin = await which(g_uv_path_local, { nothrow: true });
    }
    if (uvBin) {
        traceInfo(`Using uv to run ato: ${uvBin}`);
        return [uvBin, 'tool', 'run', '--from', UV_ATO_VERSION, 'ato'];
    }

    traceVerbose(`No ato bin found.`);
    return null;
}

export async function getAtoBin(settings?: ISettings): Promise<string[] | null> {
    const atoBin = await _getAtoBin(settings);
    if (!atoBin) {
        return null;
    }

    // Check if ato is working by running the help command
    try {
        const execFileAsync = promisify(execFile);

        const command = atoBin[0];
        const args = [...atoBin.slice(1), '--help'];

        const result = await execFileAsync(command, args)
            .then(() => ({ exitCode: 0 }))
            .catch((err: any) => ({ exitCode: err.code || 1 }));

        if (result.exitCode !== 0) {
            traceError('Failed to run ato');
            return null;
        }
    } catch (error) {
        traceError(`Error running ato: ${error}`);
        return null;
    }

    return atoBin;
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
            traceInfo(`ato bin found in venv: ${g_pyAtoBin}`);
            onDidChangeAtoBinInfoEvent.fire({ init: e.init });
        }),
        onDidChangeConfiguration(async (e: ConfigurationChangeEvent) => {
            if (e.affectsConfiguration(`atopile.ato`)) {
                onDidChangeAtoBinInfoEvent.fire({ init: false });
            }
        }),
    );

    await initializePython(context);

    let ato_bin = await getAtoBin();
    if (ato_bin) {
        onDidChangeAtoBinInfoEvent.fire({ init: true });
    }
}
