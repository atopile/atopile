import * as vscode from 'vscode';
import { getBuildTarget } from '../common/target';
import { Build } from './manifest';
import * as fs from 'fs';
import * as path from 'path';
import { FileResource, FileResourceWatcher } from './file-resource-watcher';

export interface PowerTree extends FileResource {}

class PowerTreeWatcher extends FileResourceWatcher<PowerTree> {
    constructor() {
        super('Power Tree');
    }

    protected getResourceForBuild(build: Build | undefined): PowerTree | undefined {
        if (!build?.entry) {
            return undefined;
        }

        const jsonPath = path.join(build.root, 'build', 'builds', build.name, build.name + '.power_tree.json');
        return { path: jsonPath, exists: fs.existsSync(jsonPath) };
    }
}

const powerTreeWatcher = new PowerTreeWatcher();

export const onPowerTreeChanged = powerTreeWatcher.onChanged;

export function getCurrentPowerTree(): PowerTree | undefined {
    return powerTreeWatcher.getCurrent();
}

export function getPowerTreeForBuild(buildTarget?: Build | undefined): PowerTree | undefined {
    const build = buildTarget || getBuildTarget();
    return powerTreeWatcher['getResourceForBuild'](build);
}

export async function activate(context: vscode.ExtensionContext) {
    await powerTreeWatcher.activate(context);
}

export function deactivate() {
    powerTreeWatcher.deactivate();
}
