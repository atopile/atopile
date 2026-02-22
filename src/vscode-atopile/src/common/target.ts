import * as vscode from 'vscode';
import { Build, eqBuilds } from './manifest';

export const onBuildTargetsChangedEvent = new vscode.EventEmitter<Build[]>();
export const onBuildTargetsChanged: vscode.Event<Build[]> = onBuildTargetsChangedEvent.event;

export interface SelectionState {
    projectRoot: string | undefined;
    targetNames: string[];
}
export const onSelectionStateChangedEvent = new vscode.EventEmitter<SelectionState>();
export const onSelectionStateChanged: vscode.Event<SelectionState> = onSelectionStateChangedEvent.event;

// Legacy single-target event for backwards compatibility
const onBuildTargetChangedEvent = new vscode.EventEmitter<Build | undefined>();
export const onBuildTargetChanged: vscode.Event<Build | undefined> = onBuildTargetChangedEvent.event;

// Selected build targets (can be multiple)
let g_selectedTargets: Build[] = [];
let g_selectedTargetNames: string[] = [];

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

export function setSelectionState(selection: SelectionState): void {
    const nextProjectRoot = selection.projectRoot;
    const nextTargetNames = selection.targetNames;
    const changed =
        g_projectRoot !== nextProjectRoot ||
        !stringArraysEqual(g_selectedTargetNames, nextTargetNames);
    if (!changed) {
        return;
    }
    g_projectRoot = nextProjectRoot;
    g_selectedTargetNames = [...nextTargetNames];
    onSelectionStateChangedEvent.fire(getSelectionState());
}

export function syncSelectedTargets(builds: Build[]) {
    if (!g_projectRoot) {
        setSelectedTargets([]);
        return;
    }
    if (g_selectedTargetNames.length === 0) {
        setSelectedTargets([]);
        return;
    }
    const selectedBuilds = builds.filter(
        (build) => build.root === g_projectRoot && g_selectedTargetNames.includes(build.name)
    );
    setSelectedTargets(selectedBuilds);
}

export function isTargetSelected(target: Build): boolean {
    return g_selectedTargets.some(t => eqBuilds(t, target));
}

export function toggleTarget(target: Build): void {
    const next = isTargetSelected(target)
        ? g_selectedTargets.filter((t) => !eqBuilds(t, target))
        : [...g_selectedTargets, target];
    setSelectionState({
        projectRoot: g_projectRoot,
        targetNames: next.map((t) => t.name),
    });
    setSelectedTargets(next);
}

export function getProjectRoot(): string | undefined {
    return g_projectRoot;
}

export function getSelectionState(): SelectionState {
    return {
        projectRoot: g_projectRoot,
        targetNames: [...g_selectedTargetNames],
    };
}

function arraysEqual(a: Build[], b: Build[]): boolean {
    if (a.length !== b.length) return false;
    return a.every((build, i) => eqBuilds(build, b[i]));
}

function stringArraysEqual(a: string[], b: string[]): boolean {
    if (a.length !== b.length) return false;
    return a.every((value, i) => value === b[i]);
}

export function getBuildTarget(): Build | undefined {
    return g_selectedTargets[0];
}
