import * as vscode from 'vscode';
import { getBuildTarget } from '../common/target';
import { Build } from './manifest';
import * as fs from 'fs';
import * as path from 'path';
import { FileResource, FileResourceWatcher } from './file-resource-watcher';

export interface Pinout extends FileResource {}

class PinoutWatcher extends FileResourceWatcher<Pinout> {
    constructor() {
        super('Pinout');
    }

    protected getResourceForBuild(build: Build | undefined): Pinout | undefined {
        if (!build?.entry) {
            return undefined;
        }

        const jsonPath = path.join(build.root, 'build', 'builds', build.name, build.name + '.pinout.json');
        return { path: jsonPath, exists: fs.existsSync(jsonPath) };
    }
}

const pinoutWatcher = new PinoutWatcher();

export const onPinoutChanged = pinoutWatcher.onChanged;

export function getCurrentPinout(): Pinout | undefined {
    return pinoutWatcher.getCurrent();
}

export function getPinoutForBuild(buildTarget?: Build | undefined): Pinout | undefined {
    const build = buildTarget || getBuildTarget();
    return pinoutWatcher['getResourceForBuild'](build);
}

export async function activate(context: vscode.ExtensionContext) {
    await pinoutWatcher.activate(context);
}

export function deactivate() {
    pinoutWatcher.deactivate();
}
