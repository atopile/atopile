// Copyright (c) Microsoft Corporation. All rights reserved.
// Licensed under the MIT License.

/* eslint-disable @typescript-eslint/naming-convention */
import { Event, EventEmitter, ExtensionContext } from 'vscode';
import { traceInfo } from './log/logging';
// TODO make soft import so we can remove extension dependency
import { PythonExtension } from '@vscode/python-extension';

export interface IInterpreterDetails {
    bin_dir?: string;
    init: boolean;
}

const onDidChangePythonInterpreterEvent = new EventEmitter<IInterpreterDetails>();
export const onDidChangePythonInterpreter: Event<IInterpreterDetails> = onDidChangePythonInterpreterEvent.event;

let _api: PythonExtension | undefined;

async function g_apiSingleton(): Promise<PythonExtension | undefined> {
    if (_api) {
        return _api;
    }
    try {
        _api = await PythonExtension.api();
    } catch (error) {}
    return _api;
}

function _getBinDir(path: string): string | undefined {
    if (path.includes('/bin')) {
        return path.split('/bin')[0] + '/bin';
    }
    return undefined;
}

export async function initializePython(context: ExtensionContext): Promise<void> {
    // TODO: might want to wait for python extension to load if available
    const api = await g_apiSingleton();

    if (!api) {
        traceInfo('Python extension not found. Assuming ato is installed.');
        return;
    }

    context.subscriptions.push(
        api.environments.onDidChangeActiveEnvironmentPath((e) => {
            traceInfo(`Python venv changed to ${e.path}.`);
            onDidChangePythonInterpreterEvent.fire({ bin_dir: _getBinDir(e.path), init: false });
        }),
    );

    const path = api.environments.getActiveEnvironmentPath();
    traceInfo(`Python extension found at ${path.path}.`);
    const bin_dir = _getBinDir(path.path);
    if (bin_dir) {
        traceInfo(`Python venv bin found at ${bin_dir}.`);
        onDidChangePythonInterpreterEvent.fire({ bin_dir, init: true });
    }
}
