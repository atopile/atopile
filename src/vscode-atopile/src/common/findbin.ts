import { ConfigurationChangeEvent, Disposable, Event, EventEmitter } from 'vscode';
import { onDidChangePythonInterpreter, IInterpreterDetails, initializePython } from './python';
import { onDidChangeConfiguration } from './vscodeapi';
import * as fs from 'fs';
import { ISettings } from './settings';
import { traceError, traceInfo, traceVerbose } from './log/logging';
const which = require('which');

export interface AtoBinInfo {
    init: boolean;
}

const onDidChangeAtoBinInfoEvent = new EventEmitter<AtoBinInfo>();
export const onDidChangeAtoBinInfo: Event<AtoBinInfo> = onDidChangeAtoBinInfoEvent.event;

//TODO use vscode profile folder or something that is standard for extensions to use
const UVX_PATH_LOCAL = '/tmp/uvx';
const UVX_ATO_VERSION = 'git+https://github.com/atopile/atopile@feature/vsce_autoinstall';

let g_pyAtoBin: string | undefined = undefined;

export async function getAtoBin(settings?: ISettings): Promise<string[] | null> {
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

    // lazy load
    let sysAtoBin = await which('ato', { nothrow: true });
    if (sysAtoBin) {
        traceInfo(`Using ato bin from system PATH: ${sysAtoBin}`);
        return [sysAtoBin];
    }
    let uvxBin = await which('uvx', { nothrow: true });
    if (!uvxBin) {
        uvxBin = await which(UVX_PATH_LOCAL, { nothrow: true });
    }
    if (uvxBin) {
        traceInfo(`Using uvx to run ato: ${uvxBin}`);
        return [uvxBin, '--from', UVX_ATO_VERSION, 'ato'];
    }

    traceVerbose(`No ato bin found.`);
    return null;
}

export async function initAtoBin(disposables: Disposable[]): Promise<void> {
    disposables.push(
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

    await initializePython(disposables);

    let ato_bin = await getAtoBin();
    if (ato_bin) {
        onDidChangeAtoBinInfoEvent.fire({ init: true });
    }
}
