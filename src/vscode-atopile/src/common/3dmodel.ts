import * as vscode from 'vscode';
import * as path from 'path';
import { getBuildTarget } from '../common/target';
import { Build } from './manifest';
import * as fs from 'fs';
import { FileResource, FileResourceWatcher } from './file-resource-watcher';
import { getCurrentPcb } from './pcb';
import { traceInfo, traceWarn } from './log/logging';
import { build3DModelGLB } from './kicad';

export interface ThreeDModel extends FileResource {}

export type ThreeDModelStatus =
    | { state: 'idle' }
    | { state: 'building' }
    | { state: 'failed'; message: string };

let modelStatus: ThreeDModelStatus = { state: 'idle' };
const modelStatusEvent = new vscode.EventEmitter<ThreeDModelStatus>();
export const onThreeDModelStatusChanged = modelStatusEvent.event;
let buildStatusTimer: NodeJS.Timeout | undefined;

export function getThreeDModelStatus(): ThreeDModelStatus {
    return modelStatus;
}

function setThreeDModelStatus(status: ThreeDModelStatus) {
    modelStatus = status;
    modelStatusEvent.fire(status);
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
            fs.mkdirSync(path.dirname(model.path), { recursive: true });
            await build3DModelGLB(pcb.path, model.path);
        },
    );
    modelWatcher.forceNotify();
}

export async function ensureThreeDModel(options?: { showProgress?: boolean }) {
    const pcb = getCurrentPcb();
    if (!pcb || !pcb.exists) {
        traceWarn('3dmodel: ensureThreeDModel: PCB not available.');
        setThreeDModelStatus({ state: 'failed', message: 'PCB not available yet.' });
        return undefined;
    }

    const model = getThreeDModelForBuild();
    if (!model) {
        traceWarn('3dmodel: ensureThreeDModel: No build target selected.');
        setThreeDModelStatus({ state: 'failed', message: 'No build target selected.' });
        return undefined;
    }

    const modelExists = fs.existsSync(model.path);
    if (modelExists) {
        const pcbMtime = fs.statSync(pcb.path).mtimeMs;
        const modelMtime = fs.statSync(model.path).mtimeMs;
        if (modelMtime >= pcbMtime) {
            modelWatcher.setCurrent({ path: model.path, exists: true });
            setThreeDModelStatus({ state: 'idle' });
            return model;
        }
    }

    const showProgress = options?.showProgress !== false;
    const build = async () => {
        fs.mkdirSync(path.dirname(model.path), { recursive: true });
        await build3DModelGLB(pcb.path, model.path);
    };

    setThreeDModelStatus({ state: 'building' });

    const attemptBuild = async (attemptLabel: string) => {
        try {
            if (showProgress) {
                await vscode.window.withProgress(
                    {
                        location: vscode.ProgressLocation.Notification,
                        title: `atopile: Building 3D model${attemptLabel}`,
                        cancellable: false,
                    },
                    async (progress) => {
                        progress.report({});
                        await build();
                    },
                );
            } else {
                await build();
            }
            return true;
        } catch (error) {
            traceWarn(`3dmodel: ensureThreeDModel: ${attemptLabel} failed: ${error}`);
            return false;
        }
    };

    const firstOk = await attemptBuild('');
    if (!firstOk) {
        const retryOk = await attemptBuild(' (retry)');
        if (!retryOk) {
            setThreeDModelStatus({
                state: 'failed',
                message: 'KiCad failed to export the 3D model. Try again.',
            });
            return undefined;
        }
    }

    const updated = { path: model.path, exists: fs.existsSync(model.path) };
    modelWatcher.setCurrent(updated);
    modelWatcher.forceNotify();
    setThreeDModelStatus({ state: 'idle' });
    return updated;
}

export function startThreeDModelBuild(options?: {
    timeoutMs?: number;
    retryAttempts?: number;
    onRetry?: () => void;
    retryDelayMs?: number;
}) {
    if (buildStatusTimer) {
        clearTimeout(buildStatusTimer);
        buildStatusTimer = undefined;
    }

    setThreeDModelStatus({ state: 'building' });

    const timeoutMs = options?.timeoutMs ?? 60000;
    let remainingRetries = options?.retryAttempts ?? 0;

    const scheduleTimeout = () => {
        buildStatusTimer = setTimeout(() => {
            const model = getThreeDModelForBuild();
            const exists = model?.path ? fs.existsSync(model.path) : false;
            if (exists) {
                return;
            }

            if (remainingRetries > 0 && options?.onRetry) {
                remainingRetries -= 1;
                const delay = options?.retryDelayMs ?? 1500;
                setTimeout(() => {
                    options.onRetry?.();
                    scheduleTimeout();
                }, delay);
                return;
            }

            setThreeDModelStatus({
                state: 'failed',
                message: '3D model did not generate. Try again after the build finishes.',
            });
        }, timeoutMs);
    };

    scheduleTimeout();
}

export async function activate(context: vscode.ExtensionContext) {
    await modelWatcher.activate(context);

    context.subscriptions.push(
        onThreeDModelChanged((model) => {
            if (model?.exists) {
                if (buildStatusTimer) {
                    clearTimeout(buildStatusTimer);
                    buildStatusTimer = undefined;
                }
                setThreeDModelStatus({ state: 'idle' });
            }
        }),
    );
}

export function deactivate() {
    modelWatcher.deactivate();
}
