import * as vscode from 'vscode';
import { getBuildTarget, onBuildTargetChanged } from '../common/target';
import { traceInfo } from './log/logging';
import { Build } from './manifest';
import * as fs from 'fs';

export const onPcbChangedEvent = new vscode.EventEmitter<PCB | undefined>();
export const onPcbChanged: vscode.Event<PCB | undefined> = onPcbChangedEvent.event;

interface PCB {
    path: string;
    exists: boolean;
}

let watcher: vscode.FileSystemWatcher | undefined;
let currentPcb: PCB | undefined;

export function eqPcb(a: PCB | undefined, b: PCB | undefined) {
    if ((a === undefined) !== (b === undefined)) {
        return false;
    }
    if (a === undefined || b === undefined) {
        return true;
    }
    return a.path == b.path && a.exists == b.exists;
}

export function getCurrentPcb(): PCB | undefined {
    let build = getBuildTarget();
    if (!build) {
        return undefined;
    }
    return getPcbForBuild(build);
}

export function getPcbForBuild(buildTarget?: Build | undefined): PCB | undefined {
    const build = buildTarget || getBuildTarget();

    if (!build?.entry) {
        return undefined;
    }

    return { path: build.pcb_path, exists: fs.existsSync(build.pcb_path) };
}

function notifyChange(pcbInfo: PCB | undefined) {
    onPcbChangedEvent.fire(pcbInfo);
}

export function setCurrentPCB(pcb: PCB | undefined) {
    if (eqPcb(currentPcb, pcb)) {
        return;
    }

    currentPcb = pcb;
    setupWatcher(pcb);
    notifyChange(pcb);
}

function setupWatcher(pcb: PCB | undefined) {
    disposeWatcher();

    if (!pcb) {
        return;
    }

    watcher = vscode.workspace.createFileSystemWatcher(pcb.path);

    const onChange = () => {
        traceInfo(`PCB watcher triggered for ${pcb.path}`);
        notifyChange(pcb);
    };

    const onCreateDelete = () => {
        setCurrentPCB(getPcbForBuild(getBuildTarget()));
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
            setCurrentPCB(getPcbForBuild(target));
        }),
    );
    setCurrentPCB(getPcbForBuild());
}

export function deactivate() {
    disposeWatcher();
}
