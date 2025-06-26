import * as vscode from 'vscode';
import { getBuildTarget } from '../common/target';
import { Build } from './manifest';
import * as fs from 'fs';
import { FileResource, FileResourceWatcher } from './file-resource-watcher';

export interface ThreeDModel extends FileResource {
    path: string;
    exists: boolean;
}

class ThreeDModelWatcher extends FileResourceWatcher<ThreeDModel> {
    constructor() {
        super('3D Model');
    }

    protected getResourceForBuild(build: Build | undefined): ThreeDModel | undefined {
        if (!build?.entry) {
            return undefined;
        }

        return { path: build.model_path, exists: fs.existsSync(build.model_path) };
    }
}

// Singleton instance
const modelWatcher = new ThreeDModelWatcher();

export const onThreeDModelChanged = modelWatcher.onChanged;
export const onThreeDModelChangedEvent = { fire: (_: ThreeDModel | undefined) => { } }; // Deprecated

export function getCurrentThreeDModel(): ThreeDModel | undefined {
    return modelWatcher.getCurrent();
}

export function getThreeDModelForBuild(buildTarget?: Build | undefined): ThreeDModel | undefined {
    const build = buildTarget || getBuildTarget();
    return modelWatcher['getResourceForBuild'](build);
}

export function setCurrentThreeDModel(model: ThreeDModel | undefined) {
    modelWatcher.setCurrent(model);
}

export function eqThreeDModel(a: ThreeDModel | undefined, b: ThreeDModel | undefined) {
    return modelWatcher['equals'](a, b);
}

export async function activate(context: vscode.ExtensionContext) {
    await modelWatcher.activate(context);
}

export function deactivate() {
    modelWatcher.deactivate();
}