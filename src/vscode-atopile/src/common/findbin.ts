import { ConfigurationChangeEvent, Disposable, Event, EventEmitter } from 'vscode';
import { onDidChangePythonInterpreter, IInterpreterDetails, initializePython } from './python';
import { onDidChangeConfiguration } from './vscodeapi';
import * as fs from 'fs';
import { ISettings } from './settings';
import { traceInfo, traceVerbose } from './log/logging';

export interface AtoBinInfo {
    init: boolean;
}

const onDidChangeAtoBinInfoEvent = new EventEmitter<AtoBinInfo>();
export const onDidChangeAtoBinInfo: Event<AtoBinInfo> = onDidChangeAtoBinInfoEvent.event;

let g_pyAtoBin: string | undefined = undefined;

export function getAtoBin(settings?: ISettings): string | undefined {
    if (settings && settings.ato) {
        return settings.ato;
    }
    return g_pyAtoBin;
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
}
