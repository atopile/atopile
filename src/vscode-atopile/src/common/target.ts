import * as vscode from 'vscode';
import { Build, eqBuilds } from './manifest';

export const onBuildTargetChangedEvent = new vscode.EventEmitter<Build | undefined>();
export const onBuildTargetChanged: vscode.Event<Build | undefined> = onBuildTargetChangedEvent.event;

let g_currentTarget: Build | undefined;

export function setBuildTarget(target: Build | undefined) {
    const has_changed = g_currentTarget && !eqBuilds(g_currentTarget, target);
    g_currentTarget = target;
    if (has_changed) {
        onBuildTargetChangedEvent.fire(target);
    }
}

export function getBuildTarget(): Build | undefined {
    return g_currentTarget;
}
