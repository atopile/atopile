import * as vscode from 'vscode';
import { Build } from './manifest';
import * as fs from 'fs';
import { FileResource, FileResourceWatcher } from './file-resource-watcher';
import { traceInfo, traceWarn } from './log/logging';
import { optimizeGLB } from './kicad';

/**
 * 3D Model Viewer State - focuses on what the viewer should display:
 * - `loading`: No model available, show spinner
 * - `showing`: Displaying a model (may be rebuilding/optimizing in background)
 * - `failed`: Error occurred, show message
 */
export type ThreeDViewerState =
    | { state: 'loading' }
    | { state: 'showing'; modelPath: string; isOptimized: boolean; isBuilding: boolean; isOptimizing: boolean }
    | { state: 'failed'; message: string };

let viewerState: ThreeDViewerState = { state: 'loading' };
const viewerStateEmitter = new vscode.EventEmitter<ThreeDViewerState>();
export const onThreeDViewerStateChanged = viewerStateEmitter.event;

let optimizationAbortController: AbortController | undefined;
let buildTimeoutTimer: NodeJS.Timeout | undefined;

export function getThreeDViewerState(): ThreeDViewerState {
    return viewerState;
}

function setViewerState(newState: ThreeDViewerState) {
    const oldState = viewerState.state;
    if (newState.state === 'showing') {
        traceInfo(`3dmodel: ${oldState} -> showing (building=${newState.isBuilding}, optimizing=${newState.isOptimizing})`);
    } else {
        traceInfo(`3dmodel: ${oldState} -> ${newState.state}`);
    }
    viewerState = newState;
    viewerStateEmitter.fire(newState);
}

function getOptimizedPath(rawPath: string): string {
    return rawPath.replace(/\.glb$/, '.optimized.glb');
}

function findBestGlbPath(rawPath: string): { path: string; isOptimized: boolean } | null {
    const optimizedPath = getOptimizedPath(rawPath);
    const rawExists = fs.existsSync(rawPath);
    const optimizedExists = fs.existsSync(optimizedPath);

    // Prefer optimized if it's newer than raw
    if (optimizedExists && rawExists) {
        const rawMtime = fs.statSync(rawPath).mtimeMs;
        const optimizedMtime = fs.statSync(optimizedPath).mtimeMs;
        if (optimizedMtime >= rawMtime) {
            return { path: optimizedPath, isOptimized: true };
        }
    }

    if (rawExists) {
        return { path: rawPath, isOptimized: false };
    }

    if (optimizedExists) {
        return { path: optimizedPath, isOptimized: true };
    }

    return null;
}

function cancelOptimization() {
    if (optimizationAbortController) {
        optimizationAbortController.abort();
        optimizationAbortController = undefined;
    }
}

function clearBuildTimeout() {
    if (buildTimeoutTimer) {
        clearTimeout(buildTimeoutTimer);
        buildTimeoutTimer = undefined;
    }
}

async function runOptimization(rawPath: string) {
    cancelOptimization();

    const optimizedPath = getOptimizedPath(rawPath);

    if (viewerState.state === 'showing') {
        setViewerState({ ...viewerState, isOptimizing: true });
    }

    optimizationAbortController = new AbortController();
    const signal = optimizationAbortController.signal;

    try {
        await optimizeGLB(rawPath, optimizedPath, signal);

        if (signal.aborted) {
            return;
        }

        if (fs.existsSync(optimizedPath)) {
            traceInfo(`3dmodel: Optimization complete: ${optimizedPath}`);
            if (viewerState.state === 'showing') {
                setViewerState({
                    state: 'showing',
                    modelPath: optimizedPath,
                    isOptimized: true,
                    isBuilding: viewerState.isBuilding,
                    isOptimizing: false,
                });
            }
        } else {
            traceWarn('3dmodel: Optimized file was not created');
            if (viewerState.state === 'showing') {
                setViewerState({ ...viewerState, isOptimizing: false });
            }
        }
    } catch (error) {
        if (signal.aborted) {
            return;
        }
        traceWarn(`3dmodel: GLB optimization failed: ${error}`);
        if (viewerState.state === 'showing') {
            setViewerState({ ...viewerState, isOptimizing: false });
        }
    } finally {
        if (optimizationAbortController?.signal === signal) {
            optimizationAbortController = undefined;
        }
    }
}

// ============================================================================
// File Watcher
// ============================================================================

interface ThreeDModel extends FileResource {}

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

const modelWatcher = new ThreeDModelWatcher();

// ============================================================================
// Main API
// ============================================================================

/**
 * Prepare the 3D viewer for a build target. Handles three scenarios:
 * 1. Existing GLB → Show immediately, rebuild in background
 * 2. No GLB exists → Show loading spinner, wait for build
 * 3. After build completes → Optimize GLB in background
 */
export function prepareThreeDViewer(rawGlbPath: string, triggerBuild: () => void): void {
    cancelOptimization();
    clearBuildTimeout();
    modelWatcher.setCurrent({ path: rawGlbPath, exists: fs.existsSync(rawGlbPath) });

    const bestGlb = findBestGlbPath(rawGlbPath);

    if (bestGlb) {
        setViewerState({
            state: 'showing',
            modelPath: bestGlb.path,
            isOptimized: bestGlb.isOptimized,
            isBuilding: true,
            isOptimizing: false,
        });
        triggerBuild();
        setupBuildTimeout(rawGlbPath);
    } else {
        setViewerState({ state: 'loading' });
        triggerBuild();
        setupBuildTimeout(rawGlbPath);
    }
}

/**
 * Show an existing GLB in the viewer without triggering a build.
 * Used as a fallback when we cannot resolve a build target from UI state.
 */
export function showThreeDModel(rawGlbPath: string): void {
    cancelOptimization();
    clearBuildTimeout();

    let isFile = false;
    try {
        isFile = fs.existsSync(rawGlbPath) && fs.statSync(rawGlbPath).isFile();
    } catch {
        isFile = false;
    }

    modelWatcher.setCurrent({ path: rawGlbPath, exists: isFile });

    if (!isFile) {
        setViewerState({
            state: 'failed',
            message: '3D model file not found. Run a build to generate it.',
        });
        return;
    }

    const bestGlb = findBestGlbPath(rawGlbPath);
    if (!bestGlb) {
        setViewerState({
            state: 'failed',
            message: '3D model file not found. Run a build to generate it.',
        });
        return;
    }

    setViewerState({
        state: 'showing',
        modelPath: bestGlb.path,
        isOptimized: bestGlb.isOptimized,
        isBuilding: false,
        isOptimizing: false,
    });

    if (!bestGlb.isOptimized) {
        setTimeout(() => runOptimization(rawGlbPath), 1000);
    }
}

function setupBuildTimeout(rawGlbPath: string) {
    clearBuildTimeout();

    buildTimeoutTimer = setTimeout(() => {
        if (fs.existsSync(rawGlbPath)) {
            return;
        }

        if (viewerState.state === 'loading') {
            setViewerState({
                state: 'failed',
                message: '3D model build timed out. Try building again.',
            });
        } else if (viewerState.state === 'showing') {
            setViewerState({ ...viewerState, isBuilding: false });
        }
    }, 300000); // 5 minutes
}

/** Called when webview reports build completion */
export function handleThreeDModelBuildResult(success: boolean, error?: string | null) {
    clearBuildTimeout();

    // "interrupted" errors are stale results from cancelled builds
    if (!success && error?.includes('interrupted')) {
        return;
    }

    const model = modelWatcher.getCurrent();
    if (!model?.path) {
        traceWarn('3dmodel: Build result received but no model path configured');
        return;
    }

    if (success) {
        setTimeout(() => onBuildSuccess(model.path), 500);
    } else {
        onBuildFailure(error || 'Build failed');
    }
}

function onBuildSuccess(rawGlbPath: string) {
    // Already showing this model and not waiting for a build
    if (viewerState.state === 'showing' && !viewerState.isBuilding && viewerState.modelPath.includes(rawGlbPath.replace('.glb', ''))) {
        return;
    }

    // File might not be written yet, retry
    if (!fs.existsSync(rawGlbPath)) {
        setTimeout(() => {
            if (fs.existsSync(rawGlbPath)) {
                onBuildSuccess(rawGlbPath);
            } else {
                onBuildFailure('Build completed but file was not created');
            }
        }, 1000);
        return;
    }

    modelWatcher.setCurrent({ path: rawGlbPath, exists: true });

    // If already showing an optimized model, keep showing it while we optimize the new build
    if (viewerState.state === 'showing' && viewerState.isOptimized) {
        setViewerState({ ...viewerState, isBuilding: false, isOptimizing: true });
        runOptimization(rawGlbPath);
        return;
    }

    // Otherwise show the best available GLB
    const bestGlb = findBestGlbPath(rawGlbPath);

    if (bestGlb) {
        setViewerState({
            state: 'showing',
            modelPath: bestGlb.path,
            isOptimized: bestGlb.isOptimized,
            isBuilding: false,
            isOptimizing: false,
        });

        if (!bestGlb.isOptimized) {
            setTimeout(() => runOptimization(rawGlbPath), 1000);
        }
    } else {
        onBuildFailure('File disappeared after build');
    }
}

function onBuildFailure(message: string) {
    traceWarn(`3dmodel: Build failed: ${message}`);

    if (viewerState.state === 'showing') {
        setViewerState({ ...viewerState, isBuilding: false });
    } else {
        setViewerState({ state: 'failed', message });
    }
}

// ============================================================================
// Activation / Deactivation
// ============================================================================

export async function activate(context: vscode.ExtensionContext) {
    await modelWatcher.activate(context);

    // When file watcher detects GLB created, update viewer
    context.subscriptions.push(
        modelWatcher.onChanged((model) => {
            if (!model?.path || !model.exists) {
                return;
            }
            if (viewerState.state === 'loading' || (viewerState.state === 'showing' && viewerState.isBuilding)) {
                onBuildSuccess(model.path);
            }
        }),
    );
}

export function deactivate() {
    cancelOptimization();
    clearBuildTimeout();
    modelWatcher.deactivate();
}
