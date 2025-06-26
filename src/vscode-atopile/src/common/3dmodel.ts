import * as vscode from 'vscode';
import { getBuildTarget, onBuildTargetChanged } from '../common/target';
import { traceInfo } from './log/logging';
import { Build } from './manifest';
import * as fs from 'fs';

export const onThreeDModelChangedEvent = new vscode.EventEmitter<ThreeDModel | undefined>();
export const onThreeDModelChanged: vscode.Event<ThreeDModel | undefined> = onThreeDModelChangedEvent.event;

export interface ThreeDModel {
    path: string;
    exists: boolean;
}

let watcher: vscode.FileSystemWatcher | undefined;
let currentThreeDModel: ThreeDModel | undefined;

export function eqThreeDModel(a: ThreeDModel | undefined, b: ThreeDModel | undefined) {
    if ((a === undefined) !== (b === undefined)) {
        return false;
    }
    if (a === undefined || b === undefined) {
        return true;
    }
    return a.path == b.path && a.exists == b.exists;
}

export function getCurrentThreeDModel(): ThreeDModel | undefined {
    const build = getBuildTarget();
    if (!build) {
        return undefined;
    }
    return getThreeDModelForBuild(build);
}

export function getThreeDModelForBuild(buildTarget?: Build | undefined): ThreeDModel | undefined {
    const build = buildTarget || getBuildTarget();

    if (!build?.entry) {
        return undefined;
    }

    return { path: build.model_path, exists: fs.existsSync(build.model_path) };
}

function notifyChange(modelInfo: ThreeDModel | undefined) {
    onThreeDModelChangedEvent.fire(modelInfo);
}

export function setCurrentThreeDModel(model: ThreeDModel | undefined) {
    if (eqThreeDModel(currentThreeDModel, model)) {
        return;
    }

    currentThreeDModel = model;
    setupWatcher(model);
    notifyChange(model);
}

function setupWatcher(model: ThreeDModel | undefined) {
    disposeWatcher();

    if (!model) {
        return;
    }

    watcher = vscode.workspace.createFileSystemWatcher(model.path);

    const onChange = () => {
        traceInfo(`3D Model watcher triggered for ${model.path}`);
        notifyChange(model);
    };

    const onCreateDelete = () => {
        setCurrentThreeDModel(getThreeDModelForBuild(getBuildTarget()));
    };

    watcher.onDidChange(onChange);
    watcher.onDidCreate(onCreateDelete);
    watcher.onDidDelete(onCreateDelete);
}

function disposeWatcher() {
    if (watcher) {
        watcher.dispose();
        watcher = undefined;
    }
}

export async function activate(context: vscode.ExtensionContext) {
    context.subscriptions.push(
        onBuildTargetChanged(async (target: Build | undefined) => {
            setCurrentThreeDModel(getThreeDModelForBuild(target));
        }),
    );
    setCurrentThreeDModel(getThreeDModelForBuild());
}

export function deactivate() {
    disposeWatcher();
}