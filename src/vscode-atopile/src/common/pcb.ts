import * as vscode from 'vscode';
import * as fs from 'fs';
import { backendServer } from './backendServer';
import { getBuildTarget, onBuildTargetChanged } from '../common/target';
import { Build } from './manifest';

interface PCB {
    path: string;
    exists: boolean;
}

let current: PCB | undefined;
const onChangedEvent = new vscode.EventEmitter<PCB | undefined>();
export const onPcbChanged = onChangedEvent.event;
export const onPcbChangedEvent = { fire: (_: PCB | undefined) => {} }; // Deprecated

function getResourceForBuild(build: Build | undefined): PCB | undefined {
    if (!build?.entry) {
        return undefined;
    }

    return {
        path: build.pcb_path,
        exists: fs.existsSync(build.pcb_path),
    };
}

function equals(a: PCB | undefined, b: PCB | undefined): boolean {
    if ((a === undefined) !== (b === undefined)) {
        return false;
    }
    if (a === undefined || b === undefined) {
        return true;
    }
    return a.path === b.path && a.exists === b.exists;
}

function setCurrent(pcb: PCB | undefined): void {
    if (equals(current, pcb)) {
        return;
    }
    current = pcb;
    onChangedEvent.fire(pcb);
}

function syncCurrentFromBuild(build: Build | undefined): void {
    const pcb = getResourceForBuild(build);
    setCurrent(pcb);

    if (!pcb || !build?.root) {
        backendServer.sendBackendAction('watchResourceFile', { resourceType: 'pcb', path: null });
        return;
    }

    backendServer.sendBackendAction('watchResourceFile', {
        resourceType: 'pcb',
        projectRoot: build.root,
        path: pcb.path,
    });
}

export function getCurrentPcb(): PCB | undefined {
    return current;
}

export function getPcbForBuild(buildTarget?: Build | undefined): PCB | undefined {
    return getResourceForBuild(buildTarget || getBuildTarget());
}

export function setCurrentPCB(pcb: PCB | undefined) {
    setCurrent(pcb);
}

export function eqPcb(a: PCB | undefined, b: PCB | undefined) {
    return equals(a, b);
}

export async function activate(context: vscode.ExtensionContext) {
    context.subscriptions.push(
        onBuildTargetChanged((target: Build | undefined) => {
            syncCurrentFromBuild(target);
        }),
        backendServer.onBackendEvent((message) => {
            if (message.event === 'backend_socket_connected') {
                syncCurrentFromBuild(getBuildTarget());
                return;
            }
            if (message.event !== 'resource_file_changed') {
                return;
            }
            if (message.data.resourceType !== 'pcb') {
                return;
            }
            const path = typeof message.data.path === 'string' ? message.data.path : undefined;
            if (!path) {
                return;
            }
            if (!current || current.path !== path) {
                return;
            }
            setCurrent({
                path,
                exists: Boolean(message.data.exists),
            });
        }),
    );

    syncCurrentFromBuild(getBuildTarget());
}

export function deactivate() {
    backendServer.sendBackendAction('watchResourceFile', { resourceType: 'pcb', path: null });
}
