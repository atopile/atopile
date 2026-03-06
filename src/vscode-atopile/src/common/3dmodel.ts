import * as vscode from 'vscode';
import * as fs from 'fs';
import { backendServer } from './backendServer';
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

interface ThreeDModel {
    path: string;
    exists: boolean;
}

let viewerState: ThreeDViewerState = { state: 'loading' };
const viewerStateEmitter = new vscode.EventEmitter<ThreeDViewerState>();
export const onThreeDViewerStateChanged = viewerStateEmitter.event;

let optimizationAbortController: AbortController | undefined;
let buildTimeoutTimer: NodeJS.Timeout | undefined;
let currentModel: ThreeDModel | undefined;
let currentProjectRoot: string | undefined;

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

function setCurrentModel(model: ThreeDModel | undefined): void {
    currentModel = model;
}

function watchCurrentModel(projectRoot: string | undefined, rawGlbPath: string | undefined): void {
    backendServer.sendBackendAction('watchResourceFile', {
        resourceType: 'model',
        projectRoot: projectRoot ?? null,
        path: rawGlbPath ?? null,
    });
}

function getOptimizedPath(rawPath: string): string {
    return rawPath.replace(/\.glb$/, '.optimized.glb');
}

function findBestGlbPath(rawPath: string): { path: string; isOptimized: boolean } | null {
    const optimizedPath = getOptimizedPath(rawPath);
    const rawExists = fs.existsSync(rawPath);
    const optimizedExists = fs.existsSync(optimizedPath);

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
        } else if (viewerState.state === 'showing') {
            traceWarn('3dmodel: Optimized file was not created');
            setViewerState({ ...viewerState, isOptimizing: false });
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

/**
 * Prepare the 3D viewer for a build target. Handles three scenarios:
 * 1. Existing GLB → Show immediately, rebuild in background
 * 2. No GLB exists → Show loading spinner, wait for build
 * 3. After build completes → Optimize GLB in background
 */
export function prepareThreeDViewer(rawGlbPath: string, projectRoot: string, triggerBuild: () => void): void {
    cancelOptimization();
    clearBuildTimeout();
    currentProjectRoot = projectRoot;
    setCurrentModel({ path: rawGlbPath, exists: fs.existsSync(rawGlbPath) });
    watchCurrentModel(projectRoot, rawGlbPath);

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
    }, 300000);
}

export function handleThreeDModelBuildResult(success: boolean, error?: string | null) {
    clearBuildTimeout();

    if (!success && error?.includes('interrupted')) {
        return;
    }

    if (!currentModel?.path) {
        traceWarn('3dmodel: Build result received but no model path configured');
        return;
    }

    if (success) {
        const modelPath = currentModel.path;
        setTimeout(() => onBuildSuccess(modelPath), 500);
    } else {
        onBuildFailure(error || 'Build failed');
    }
}

function onBuildSuccess(rawGlbPath: string) {
    if (viewerState.state === 'showing' && !viewerState.isBuilding && viewerState.modelPath.includes(rawGlbPath.replace('.glb', ''))) {
        return;
    }

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

    setCurrentModel({ path: rawGlbPath, exists: true });

    if (viewerState.state === 'showing' && viewerState.isOptimized) {
        setViewerState({ ...viewerState, isBuilding: false, isOptimizing: true });
        runOptimization(rawGlbPath);
        return;
    }

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

export async function activate(context: vscode.ExtensionContext) {
    context.subscriptions.push(
        backendServer.onBackendEvent((message) => {
            if (message.event === 'backend_socket_connected') {
                if (currentModel?.path) {
                    watchCurrentModel(currentProjectRoot, currentModel.path);
                }
                return;
            }
            if (message.event !== 'resource_file_changed') {
                return;
            }
            if (message.data.resourceType !== 'model') {
                return;
            }
            const path = typeof message.data.path === 'string' ? message.data.path : undefined;
            if (!path || !currentModel || currentModel.path !== path) {
                return;
            }

            currentModel = {
                path,
                exists: Boolean(message.data.exists),
            };

            if (!currentModel.exists) {
                return;
            }

            if (viewerState.state === 'loading' || (viewerState.state === 'showing' && viewerState.isBuilding)) {
                onBuildSuccess(currentModel.path);
            }
        }),
    );
}

export function deactivate() {
    cancelOptimization();
    clearBuildTimeout();
    currentProjectRoot = undefined;
    watchCurrentModel(undefined, undefined);
}
