import { ConfigurationChangeEvent, Disposable, Event, EventEmitter } from 'vscode';
import { onDidChangePythonInterpreter, IInterpreterDetails, initializePython } from './python';
import { onDidChangeConfiguration } from './vscodeapi';
import * as fs from 'fs';
import { ISettings } from './settings';
import { traceInfo, traceVerbose } from './log/logging';
const which = require('which');

export interface AtoBinInfo {
    init: boolean;
}

const onDidChangeAtoBinInfoEvent = new EventEmitter<AtoBinInfo>();
export const onDidChangeAtoBinInfo: Event<AtoBinInfo> = onDidChangeAtoBinInfoEvent.event;

let g_pyAtoBin: string | undefined = undefined;
let g_sysAtoBin: string | undefined = undefined;

export function getAtoBin(settings?: ISettings): string | undefined {
    if (settings && settings.ato) {
        traceInfo(`Using ato bin from settings: ${settings.ato}`);
        return settings.ato;
    }
    if (g_pyAtoBin) {
        traceInfo(`Using ato bin from venv: ${g_pyAtoBin}`);
        return g_pyAtoBin;
    }
    if (g_sysAtoBin) {
        traceInfo(`Using ato bin from system PATH: ${g_sysAtoBin}`);
        return g_sysAtoBin;
    }
    traceVerbose(`No ato bin found.`);
    return undefined;
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
                traceVerbose(`Ato bin not found in venv: ${g_pyAtoBin}`);
                return;
            }
            traceInfo(`Ato bin found in venv: ${g_pyAtoBin}`);
            onDidChangeAtoBinInfoEvent.fire({ init: e.init });
        }),
        onDidChangeConfiguration(async (e: ConfigurationChangeEvent) => {
            if (e.affectsConfiguration(`atopile.ato`)) {
                onDidChangeAtoBinInfoEvent.fire({ init: false });
            }
        }),
    );

    await initializePython(disposables);

    // check if ato in system path
    g_sysAtoBin = await which('ato', { nothrow: true });
    if (g_sysAtoBin) {
        traceInfo(`Ato bin found in system PATH: ${g_sysAtoBin}`);
        onDidChangeAtoBinInfoEvent.fire({ init: true });
    } else {
        traceVerbose(`Ato bin not found in system PATH.`);
    }
}
