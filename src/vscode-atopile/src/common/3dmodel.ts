import * as vscode from 'vscode';
import * as path from 'path';
import { getBuildTarget } from '../common/target';
import { Build } from './manifest';
import * as fs from 'fs';
import { FileResource, FileResourceWatcher } from './file-resource-watcher';
import { getCurrentPcb } from './pcb';
import { traceInfo, traceWarn } from './log/logging';
import { build3DModelGLB, optimizeGLB } from './kicad';

export interface ThreeDModel extends FileResource {}

export type ThreeDModelStatus =
    | { state: 'idle' }
    | { state: 'building' }
    | { state: 'failed'; message: string }
    | { state: 'raw_ready'; rawPath: string }
    | { state: 'optimizing'; rawPath: string }
    | { state: 'optimized'; rawPath: string; optimizedPath: string };

let modelStatus: ThreeDModelStatus = { state: 'idle' };
const modelStatusEvent = new vscode.EventEmitter<ThreeDModelStatus>();
export const onThreeDModelStatusChanged = modelStatusEvent.event;
let buildStatusTimer: NodeJS.Timeout | undefined;

// Track current optimization operation so we can cancel it if a new build starts
let currentOptimizationAbortController: AbortController | undefined;

// Track when we've successfully processed a build to ignore late failure messages
// This is reset when a new build starts
let hasProcessedSuccessForCurrentBuild = false;

export function getThreeDModelStatus(): ThreeDModelStatus {
    return modelStatus;
}

function setThreeDModelStatus(status: ThreeDModelStatus) {
    const currentState = modelStatus.state;

    // Prevent going from optimization-related states back to failed
    // This handles race conditions where stale failure messages arrive after success
    if (status.state === 'failed' &&
        (currentState === 'raw_ready' || currentState === 'optimizing' || currentState === 'optimized')) {
        traceInfo(`3dmodel: BLOCKING state transition from ${currentState} to failed: ${(status as { message?: string }).message}`);
        return;
    }

    traceInfo(`3dmodel: State transition: ${currentState} -> ${status.state}`);
    modelStatus = status;
    modelStatusEvent.fire(status);
}

/**
 * Get the optimized GLB path from the raw GLB path.
 * Raw: {target}.pcba.glb → Optimized: {target}.pcba.optimized.glb
 */
export function getOptimizedPath(rawPath: string): string {
    return rawPath.replace(/\.glb$/, '.optimized.glb');
}

/**
 * Exposed for the model viewer to set status.
 */
export function setThreeDModelStatusFromViewer(status: ThreeDModelStatus) {
    setThreeDModelStatus(status);
}

/**
 * Cancel any running optimization operation.
 */
function cancelOptimization() {
    if (currentOptimizationAbortController) {
        currentOptimizationAbortController.abort();
        currentOptimizationAbortController = undefined;
    }
}

/**
 * Exposed for the model viewer to start optimization.
 */
export function startOptimizationFromViewer(rawPath: string) {
    startOptimization(rawPath);
}

/**
 * Start background optimization of a raw GLB file.
 * Sets status to 'optimizing' and then 'optimized' when complete.
 * On failure, logs the error and continues with raw GLB (graceful degradation).
 */
async function startOptimization(rawPath: string) {
    // Cancel any existing optimization
    cancelOptimization();

    // Also clear any pending build timeout (safety measure)
    if (buildStatusTimer) {
        clearTimeout(buildStatusTimer);
        buildStatusTimer = undefined;
    }

    const optimizedPath = getOptimizedPath(rawPath);
    setThreeDModelStatus({ state: 'optimizing', rawPath });

    // Create new abort controller for this optimization
    currentOptimizationAbortController = new AbortController();
    const signal = currentOptimizationAbortController.signal;

    try {
        await optimizeGLB(rawPath, optimizedPath, signal);

        // Check if we were cancelled during optimization
        if (signal.aborted) {
            return;
        }

        // Verify the optimized file was created
        if (fs.existsSync(optimizedPath)) {
            traceInfo(`3dmodel: Optimization complete. Raw: ${rawPath}, Optimized: ${optimizedPath}`);
            setThreeDModelStatus({ state: 'optimized', rawPath, optimizedPath });
        } else {
            // File not created - fall back to raw
            traceWarn('3dmodel: Optimized file was not created, using raw GLB');
            setThreeDModelStatus({ state: 'raw_ready', rawPath });
        }
    } catch (error) {
        // Check if this was a cancellation
        if (signal.aborted) {
            traceInfo('3dmodel: Optimization was cancelled');
            return;
        }

        // Log error and gracefully degrade to raw GLB
        traceWarn(`3dmodel: GLB optimization failed, using raw GLB: ${error}`);
        setThreeDModelStatus({ state: 'raw_ready', rawPath });
    } finally {
        // Clean up abort controller if it's still ours
        if (currentOptimizationAbortController?.signal === signal) {
            currentOptimizationAbortController = undefined;
        }
    }
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

            // Check if we have an up-to-date optimized version
            const optimizedPath = getOptimizedPath(model.path);
            if (fs.existsSync(optimizedPath)) {
                const optimizedMtime = fs.statSync(optimizedPath).mtimeMs;
                if (optimizedMtime >= modelMtime) {
                    setThreeDModelStatus({ state: 'optimized', rawPath: model.path, optimizedPath });
                    return model;
                }
            }

            // Model exists but needs optimization - show raw and start optimization
            setThreeDModelStatus({ state: 'raw_ready', rawPath: model.path });
            startOptimization(model.path);
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

    // Start optimization after successful build
    setThreeDModelStatus({ state: 'raw_ready', rawPath: model.path });
    startOptimization(model.path);
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

    // Cancel any ongoing optimization when a new build starts
    cancelOptimization();

    // Reset the success flag for the new build
    hasProcessedSuccessForCurrentBuild = false;

    setThreeDModelStatus({ state: 'building' });

    const timeoutMs = options?.timeoutMs ?? 300000; // 5 minutes for complex boards
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

/**
 * Handle the result of a 3D model build from the webview.
 * Called when the build completes, fails, or is cancelled.
 * On success, immediately shows the raw GLB and starts background optimization.
 */
export function handleThreeDModelBuildResult(success: boolean, error?: string | null) {
    const currentState = modelStatus.state;

    // Clear any pending timeout since we have a definitive result
    if (buildStatusTimer) {
        clearTimeout(buildStatusTimer);
        buildStatusTimer = undefined;
    }

    // Special case: Always ignore "Build was interrupted" messages
    // These come from stale build history and should never override a successful build
    if (!success && error && error.includes('interrupted')) {
        return;
    }

    // If we've already processed a success for this build, ignore any failure messages.
    // This handles race conditions where success and failure messages arrive out of order
    // or where stale "interrupted" status is reported from build history.
    if (!success && hasProcessedSuccessForCurrentBuild) {
        return;
    }

    // Also check state-based protection as a backup
    if (!success && (currentState === 'raw_ready' || currentState === 'optimizing' || currentState === 'optimized')) {
        return;
    }

    if (success) {
        // Mark that we've processed a success for this build
        hasProcessedSuccessForCurrentBuild = true;

        // Success - check if file exists and update status
        const model = getThreeDModelForBuild();
        if (model?.path && fs.existsSync(model.path)) {
            // File exists - update the watcher and show raw GLB immediately
            modelWatcher.setCurrent({ path: model.path, exists: true });
            modelWatcher.forceNotify();

            // Check if we already have an optimized version that's newer than the raw
            const optimizedPath = getOptimizedPath(model.path);
            if (fs.existsSync(optimizedPath)) {
                const rawMtime = fs.statSync(model.path).mtimeMs;
                const optimizedMtime = fs.statSync(optimizedPath).mtimeMs;
                if (optimizedMtime >= rawMtime) {
                    // Optimized version is up to date, use it directly
                    setThreeDModelStatus({ state: 'optimized', rawPath: model.path, optimizedPath });
                    return;
                }
            }

            // Set raw_ready and start background optimization after a short delay
            // to ensure the viewer has time to load the raw GLB first
            setThreeDModelStatus({ state: 'raw_ready', rawPath: model.path });
            // Start optimization in background after delay (don't await)
            setTimeout(() => {
                // Only start optimization if we're still in raw_ready state
                if (modelStatus.state === 'raw_ready') {
                    startOptimization(model.path);
                }
            }, 2000);
        } else {
            // File doesn't exist yet - wait a bit and retry
            // This handles cases where the build completed but file write is delayed
            setTimeout(() => {
                const retryModel = getThreeDModelForBuild();
                if (retryModel?.path && fs.existsSync(retryModel.path)) {
                    modelWatcher.setCurrent({ path: retryModel.path, exists: true });
                    modelWatcher.forceNotify();

                    // Check for existing optimized version
                    const optimizedPath = getOptimizedPath(retryModel.path);
                    if (fs.existsSync(optimizedPath)) {
                        const rawMtime = fs.statSync(retryModel.path).mtimeMs;
                        const optimizedMtime = fs.statSync(optimizedPath).mtimeMs;
                        if (optimizedMtime >= rawMtime) {
                            setThreeDModelStatus({ state: 'optimized', rawPath: retryModel.path, optimizedPath });
                            return;
                        }
                    }

                    // Set raw_ready and start optimization after delay
                    setThreeDModelStatus({ state: 'raw_ready', rawPath: retryModel.path });
                    setTimeout(() => {
                        if (modelStatus.state === 'raw_ready') {
                            startOptimization(retryModel.path);
                        }
                    }, 2000);
                } else {
                    // Still no file - show failure
                    setThreeDModelStatus({
                        state: 'failed',
                        message: 'Build completed but 3D model file was not created.',
                    });
                }
            }, 1000);
        }
    } else {
        // Build failed or was cancelled - show the error
        setThreeDModelStatus({
            state: 'failed',
            message: error || 'Build failed or was cancelled.',
        });
    }
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
                // Only reset to idle if we're not in an optimization-related state
                // This prevents the watcher from overriding our optimization flow
                const currentState = modelStatus.state;
                if (currentState !== 'raw_ready' && currentState !== 'optimizing' && currentState !== 'optimized') {
                    setThreeDModelStatus({ state: 'idle' });
                }
            }
        }),
    );
}

export function deactivate() {
    modelWatcher.deactivate();
}
