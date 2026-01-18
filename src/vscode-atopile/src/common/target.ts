import * as vscode from 'vscode';
import { Build, eqBuilds } from './manifest';

export const onBuildTargetsChangedEvent = new vscode.EventEmitter<Build[]>();
export const onBuildTargetsChanged: vscode.Event<Build[]> = onBuildTargetsChangedEvent.event;

// Legacy single-target event for backwards compatibility
const onBuildTargetChangedEvent = new vscode.EventEmitter<Build | undefined>();
export const onBuildTargetChanged: vscode.Event<Build | undefined> = onBuildTargetChangedEvent.event;

// Selected build targets (can be multiple)
let g_selectedTargets: Build[] = [];

// Current project root (for running commands)
let g_projectRoot: string | undefined;

export function setSelectedTargets(targets: Build[]) {
    const changed = !arraysEqual(g_selectedTargets, targets);
    g_selectedTargets = [...targets];
    if (changed) {
        onBuildTargetsChangedEvent.fire(g_selectedTargets);
        // Fire legacy event with first target
        onBuildTargetChangedEvent.fire(g_selectedTargets[0]);
    }
}

export function getSelectedTargets(): Build[] {
    return [...g_selectedTargets];
}

export function isTargetSelected(target: Build): boolean {
    return g_selectedTargets.some(t => eqBuilds(t, target));
}

export function toggleTarget(target: Build): void {
    if (isTargetSelected(target)) {
        g_selectedTargets = g_selectedTargets.filter(t => !eqBuilds(t, target));
    } else {
        g_selectedTargets = [...g_selectedTargets, target];
    }
    onBuildTargetsChangedEvent.fire(g_selectedTargets);
    // Fire legacy event with first target
    onBuildTargetChangedEvent.fire(g_selectedTargets[0]);
}

export function setProjectRoot(root: string | undefined) {
    g_projectRoot = root;
}

export function getProjectRoot(): string | undefined {
    return g_projectRoot;
}

function arraysEqual(a: Build[], b: Build[]): boolean {
    if (a.length !== b.length) return false;
    return a.every((build, i) => eqBuilds(build, b[i]));
}

// Legacy single-target API for backwards compatibility
export function setBuildTarget(target: Build | undefined) {
    if (target) {
        setSelectedTargets([target]);
    } else {
        setSelectedTargets([]);
    }
}

export function getBuildTarget(): Build | undefined {
    return g_selectedTargets[0];
}
