import * as vscode from 'vscode';
import { getBuildTarget } from '../common/target';
import { Build } from './manifest';
import * as fs from 'fs';
import { FileResource, FileResourceWatcher } from './file-resource-watcher';
import { getCurrentPcb, onPcbChanged } from './pcb';
import { traceInfo, traceWarn } from './log/logging';
import { build3DModelGLB } from './kicad';

export interface ThreeDModel extends FileResource {}

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
export const onThreeDModelChangedEvent = { fire: (_: ThreeDModel | undefined) => {} }; // Deprecated

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

async function rebuild3DModel() {
    const pcb = getCurrentPcb();
    if (!pcb || !pcb.exists) {
        return;
    }

    const model = getThreeDModelForBuild();
    if (!model) {
        return;
    }
    // check model newer than pcb
    if (model && model.exists && fs.statSync(model.path).mtimeMs >= fs.statSync(pcb.path).mtimeMs) {
        traceInfo(`3dmodel: rebuild3DModel: Model is up to date: ${model.path}`);
        return;
    }

    // build model
    await vscode.window.withProgress(
        {
            location: vscode.ProgressLocation.Notification,
            title: 'atopile: Building 3D model...',
            cancellable: false,
        },
        async (progress) => {
            progress.report({});
            await build3DModelGLB(pcb.path, model.path);
        },
    );
    modelWatcher.forceNotify();
}

export async function activate(context: vscode.ExtensionContext) {
    await modelWatcher.activate(context);

    context.subscriptions.push(
        onPcbChanged((_) => {
            try {
                rebuild3DModel();
            } catch (e) {
                traceWarn(`3dmodel: onPcbChanged: Failed to rebuild 3D model: ${e}`);
            }
        }),
    );
}

export function deactivate() {
    modelWatcher.deactivate();
}
