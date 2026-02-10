import * as vscode from 'vscode';
import { getBuildTarget } from '../common/target';
import { Build } from './manifest';
import * as fs from 'fs';
import * as path from 'path';
import { FileResource, FileResourceWatcher } from './file-resource-watcher';

export interface I2CTree extends FileResource {}

class I2CTreeWatcher extends FileResourceWatcher<I2CTree> {
    constructor() {
        super('I2C Tree');
    }

    protected getResourceForBuild(build: Build | undefined): I2CTree | undefined {
        if (!build?.entry) {
            return undefined;
        }

        const jsonPath = path.join(build.root, 'build', 'builds', build.name, build.name + '.i2c_tree.json');
        return { path: jsonPath, exists: fs.existsSync(jsonPath) };
    }
}

const i2cTreeWatcher = new I2CTreeWatcher();

export const onI2CTreeChanged = i2cTreeWatcher.onChanged;

export function getCurrentI2CTree(): I2CTree | undefined {
    return i2cTreeWatcher.getCurrent();
}

export function getI2CTreeForBuild(buildTarget?: Build | undefined): I2CTree | undefined {
    const build = buildTarget || getBuildTarget();
    return i2cTreeWatcher['getResourceForBuild'](build);
}

export async function activate(context: vscode.ExtensionContext) {
    await i2cTreeWatcher.activate(context);
}

export function deactivate() {
    i2cTreeWatcher.deactivate();
}
