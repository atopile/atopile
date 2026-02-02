import * as vscode from 'vscode';
import * as path from 'path';
import { getBuildTarget } from '../common/target';
import { Build } from './manifest';
import * as fs from 'fs';
import { FileResource, FileResourceWatcher } from './file-resource-watcher';
import { traceInfo, traceWarn } from './log/logging';
import { optimizeGLB } from './kicad';

export interface ThreeDModel extends FileResource {}

/**
 * Simplified 3D Model Viewer State
 *
 * The state focuses on WHAT THE VIEWER SHOULD SHOW, not what's happening in the background.
 * - `loading`: No model available yet, show a spinner
 * - `showing`: A model is being displayed (may be rebuilding in background)
 * - `failed`: An error occurred and no model can be shown
 */
export type ThreeDViewerState =
    | { state: 'loading' }
    | { state: 'showing'; modelPath: string; isOptimized: boolean; isBuilding: boolean; isOptimizing: boolean }
    | { state: 'failed'; message: string };

let viewerState: ThreeDViewerState = { state: 'loading' };
const viewerStateEvent = new vscode.EventEmitter<ThreeDViewerState>();
export const onThreeDViewerStateChanged = viewerStateEvent.event;

// Track current optimization operation so we can cancel it if a new build starts
let currentOptimizationAbortController: AbortController | undefined;

// Build timeout timer
let buildTimeoutTimer: NodeJS.Timeout | undefined;

export function getThreeDViewerState(): ThreeDViewerState {
    return viewerState;
}

function setViewerState(newState: ThreeDViewerState) {
    const oldState = viewerState.state;
    const newStateName = newState.state;

    // Log state transitions for debugging
    if (newState.state === 'showing') {
        traceInfo(`3dmodel: State: ${oldState} -> showing (building=${newState.isBuilding}, optimizing=${newState.isOptimizing}, optimized=${newState.isOptimized})`);
    } else {
        traceInfo(`3dmodel: State: ${oldState} -> ${newStateName}`);
    }

    viewerState = newState;
    viewerStateEvent.fire(newState);
}

/**
 * Get the optimized GLB path from the raw GLB path.
 * Raw: {target}.pcba.glb → Optimized: {target}.pcba.optimized.glb
 */
export function getOptimizedPath(rawPath: string): string {
    return rawPath.replace(/\.glb$/, '.optimized.glb');
}

/**
 * Find the best available GLB file for display.
 * Returns the optimized version if it exists and is up-to-date, otherwise the raw version.
 */
function findBestGlbPath(rawPath: string): { path: string; isOptimized: boolean } | null {
    const optimizedPath = getOptimizedPath(rawPath);
    traceInfo(`3dmodel: findBestGlbPath - raw: ${rawPath}, optimized: ${optimizedPath}`);

    const rawExists = fs.existsSync(rawPath);
    const optimizedExists = fs.existsSync(optimizedPath);
    traceInfo(`3dmodel: findBestGlbPath - rawExists: ${rawExists}, optimizedExists: ${optimizedExists}`);

    // Check if optimized version exists and is up-to-date
    if (optimizedExists && rawExists) {
        const rawMtime = fs.statSync(rawPath).mtimeMs;
        const optimizedMtime = fs.statSync(optimizedPath).mtimeMs;
        traceInfo(`3dmodel: findBestGlbPath - rawMtime: ${rawMtime}, optimizedMtime: ${optimizedMtime}`);
        if (optimizedMtime >= rawMtime) {
            traceInfo(`3dmodel: findBestGlbPath - using optimized (up-to-date)`);
            return { path: optimizedPath, isOptimized: true };
        } else {
            traceInfo(`3dmodel: findBestGlbPath - optimized is stale, using raw`);
        }
    }

    // Fall back to raw if it exists
    if (rawExists) {
        traceInfo(`3dmodel: findBestGlbPath - using raw`);
        return { path: rawPath, isOptimized: false };
    }

    // Check if only optimized exists (edge case)
    if (optimizedExists) {
        traceInfo(`3dmodel: findBestGlbPath - only optimized exists, using it`);
        return { path: optimizedPath, isOptimized: true };
    }

    traceInfo(`3dmodel: findBestGlbPath - no GLB found`);
    return null;
}

/**
 * Cancel any running optimization operation.
 */
function cancelOptimization() {
    if (currentOptimizationAbortController) {
        traceInfo('3dmodel: Cancelling optimization');
        currentOptimizationAbortController.abort();
        currentOptimizationAbortController = undefined;
    }
}

/**
 * Clear any pending build timeout.
 */
function clearBuildTimeout() {
    if (buildTimeoutTimer) {
        clearTimeout(buildTimeoutTimer);
        buildTimeoutTimer = undefined;
    }
}

/**
 * Start background optimization of a raw GLB file.
 * Updates viewer state to show optimization progress, then updates when complete.
 */
async function startOptimization(rawPath: string) {
    traceInfo(`3dmodel: startOptimization called for ${rawPath}`);

    // Cancel any existing optimization
    cancelOptimization();

    const optimizedPath = getOptimizedPath(rawPath);
    traceInfo(`3dmodel: Will optimize to ${optimizedPath}`);

    // Update state to show we're optimizing (keep showing current model)
    if (viewerState.state === 'showing') {
        setViewerState({
            ...viewerState,
            isOptimizing: true,
        });
    }

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
            traceInfo(`3dmodel: Optimization complete: ${optimizedPath}`);

            // Update to show the optimized model
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
            // File not created - just clear optimizing flag
            traceWarn('3dmodel: Optimized file was not created');
            if (viewerState.state === 'showing') {
                setViewerState({
                    ...viewerState,
                    isOptimizing: false,
                });
            }
        }
    } catch (error) {
        // Check if this was a cancellation
        if (signal.aborted) {
            traceInfo('3dmodel: Optimization was cancelled');
            return;
        }

        // Log error and continue with raw GLB (graceful degradation)
        traceWarn(`3dmodel: GLB optimization failed: ${error}`);
        if (viewerState.state === 'showing') {
            setViewerState({
                ...viewerState,
                isOptimizing: false,
            });
        }
    } finally {
        // Clean up abort controller if it's still ours
        if (currentOptimizationAbortController?.signal === signal) {
            currentOptimizationAbortController = undefined;
        }
    }
}

// ============================================================================
// File Resource Watcher (for detecting file changes)
// ============================================================================

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

export const onThreeDModelChanged = modelWatcher.onChanged;

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

// ============================================================================
// Main API: Unified entry point for opening 3D viewer
// ============================================================================

/**
 * Prepare the 3D viewer for a build target.
 *
 * This is the SINGLE entry point for all 3D viewer operations.
 * It handles all three starting conditions:
 * 1. Existing optimized GLB → Show immediately, build in background
 * 2. Existing raw GLB → Show immediately, build + optimize in background
 * 3. No GLB exists → Show loading, wait for build
 *
 * @param rawGlbPath Path where the raw GLB should be (may not exist yet)
 * @param triggerBuild Function to trigger the backend build
 */
export function prepareThreeDViewer(
    rawGlbPath: string,
    triggerBuild: () => void,
): void {
    traceInfo(`3dmodel: prepareThreeDViewer called with path: ${rawGlbPath}`);

    // Cancel any ongoing operations
    cancelOptimization();
    clearBuildTimeout();

    // Update the model watcher
    const exists = fs.existsSync(rawGlbPath);
    traceInfo(`3dmodel: File exists: ${exists}`);
    setCurrentThreeDModel({ path: rawGlbPath, exists });

    // Check what we have available to show
    const bestGlb = findBestGlbPath(rawGlbPath);
    traceInfo(`3dmodel: Best GLB found: ${bestGlb?.path ?? 'none'} (optimized=${bestGlb?.isOptimized ?? false})`);

    if (bestGlb) {
        // We have something to show immediately
        traceInfo(`3dmodel: Showing existing GLB: ${bestGlb.path} (optimized=${bestGlb.isOptimized})`);

        setViewerState({
            state: 'showing',
            modelPath: bestGlb.path,
            isOptimized: bestGlb.isOptimized,
            isBuilding: true, // Build will run in background
            isOptimizing: false,
        });

        // Trigger build in background
        triggerBuild();

        // Set up timeout for build failure
        setupBuildTimeout(rawGlbPath);
    } else {
        // No GLB available - show loading state
        traceInfo('3dmodel: No existing GLB, showing loading state');

        setViewerState({ state: 'loading' });

        // Trigger build
        triggerBuild();

        // Set up timeout for build failure
        setupBuildTimeout(rawGlbPath);
    }
}

/**
 * Set up a timeout to detect if the build never completes.
 */
function setupBuildTimeout(rawGlbPath: string) {
    clearBuildTimeout();

    buildTimeoutTimer = setTimeout(() => {
        // Check if file appeared
        if (fs.existsSync(rawGlbPath)) {
            return; // File exists, build succeeded
        }

        // Only show failure if we're still in loading state
        // (if we're showing something, keep showing it)
        if (viewerState.state === 'loading') {
            setViewerState({
                state: 'failed',
                message: '3D model build timed out. Try building again.',
            });
        } else if (viewerState.state === 'showing') {
            // Just clear the building flag
            setViewerState({
                ...viewerState,
                isBuilding: false,
            });
        }
    }, 300000); // 5 minute timeout
}

/**
 * Handle notification that a 3D model build completed.
 * Called by the webview when it receives build result from backend.
 */
export function handleThreeDModelBuildResult(success: boolean, error?: string | null) {
    traceInfo(`3dmodel: handleThreeDModelBuildResult called with success=${success}, error="${error}"`);
    clearBuildTimeout();

    // Ignore "interrupted" errors - these are stale
    if (!success && error?.includes('interrupted')) {
        traceInfo('3dmodel: Ignoring "interrupted" build result');
        return;
    }

    // Use the model we stored in prepareThreeDViewer
    const model = getCurrentThreeDModel();
    traceInfo(`3dmodel: Current model path: ${model?.path ?? 'undefined'}`);
    if (!model?.path) {
        traceWarn('3dmodel: Build result received but no model path configured');
        return;
    }

    if (success) {
        // Give filesystem a moment to sync
        traceInfo(`3dmodel: Build succeeded, will call handleBuildSuccess for ${model.path} in 500ms`);
        setTimeout(() => {
            handleBuildSuccess(model.path);
        }, 500);
    } else {
        handleBuildFailure(error || 'Build failed');
    }
}

function handleBuildSuccess(rawGlbPath: string) {
    traceInfo(`3dmodel: handleBuildSuccess called for ${rawGlbPath}`);

    // Skip if we're already showing this file and not building
    if (viewerState.state === 'showing' && !viewerState.isBuilding && viewerState.modelPath.includes(rawGlbPath.replace('.glb', ''))) {
        traceInfo(`3dmodel: Already showing this model, skipping`);
        return;
    }

    // Check if the file exists
    if (!fs.existsSync(rawGlbPath)) {
        traceInfo(`3dmodel: File ${rawGlbPath} does not exist yet, retrying in 1s`);
        // Retry after a short delay
        setTimeout(() => {
            if (fs.existsSync(rawGlbPath)) {
                handleBuildSuccess(rawGlbPath);
            } else {
                handleBuildFailure('Build completed but file was not created');
            }
        }, 1000);
        return;
    }

    traceInfo(`3dmodel: File ${rawGlbPath} exists`);

    // Update watcher
    modelWatcher.setCurrent({ path: rawGlbPath, exists: true });

    // Find best available GLB
    const bestGlb = findBestGlbPath(rawGlbPath);
    traceInfo(`3dmodel: Best GLB: ${bestGlb?.path ?? 'none'} (optimized=${bestGlb?.isOptimized ?? false})`);

    if (bestGlb) {
        traceInfo(`3dmodel: Build complete, showing: ${bestGlb.path}`);

        setViewerState({
            state: 'showing',
            modelPath: bestGlb.path,
            isOptimized: bestGlb.isOptimized,
            isBuilding: false,
            isOptimizing: false,
        });

        // Start optimization if showing raw GLB
        if (!bestGlb.isOptimized) {
            traceInfo(`3dmodel: Will start optimization for ${rawGlbPath} in 1s`);
            // Small delay to let viewer update first
            setTimeout(() => {
                startOptimization(rawGlbPath);
            }, 1000);
        }
    } else {
        // This shouldn't happen if fs.existsSync passed above
        handleBuildFailure('File disappeared after build');
    }
}

function handleBuildFailure(message: string) {
    traceWarn(`3dmodel: Build failed: ${message}`);

    // If we're already showing a model, just clear the building flag
    if (viewerState.state === 'showing') {
        setViewerState({
            ...viewerState,
            isBuilding: false,
        });
    } else {
        // Show error state
        setViewerState({
            state: 'failed',
            message,
        });
    }
}

// ============================================================================
// Activation / Deactivation
// ============================================================================

export async function activate(context: vscode.ExtensionContext) {
    await modelWatcher.activate(context);

    // Subscribe to file watcher changes - when GLB is created/changed, update the viewer
    context.subscriptions.push(
        onThreeDModelChanged((model) => {
            if (!model?.path) {
                return;
            }

            traceInfo(`3dmodel: File watcher detected change for ${model.path}, exists=${model.exists}`);

            // If we're in loading or building state and the file now exists, trigger success
            if (model.exists && (viewerState.state === 'loading' || (viewerState.state === 'showing' && viewerState.isBuilding))) {
                traceInfo(`3dmodel: File appeared while waiting for build, triggering handleBuildSuccess`);
                handleBuildSuccess(model.path);
            }
        }),
    );
}

export function deactivate() {
    cancelOptimization();
    clearBuildTimeout();
    modelWatcher.deactivate();
}
