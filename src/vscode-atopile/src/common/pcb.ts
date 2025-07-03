import * as vscode from 'vscode';
import { getBuildTarget } from '../common/target';
import { Build } from './manifest';
import * as fs from 'fs';
import { FileResource, FileResourceWatcher } from './file-resource-watcher';

interface PCB extends FileResource {}

class PCBWatcher extends FileResourceWatcher<PCB> {
    constructor() {
        super('PCB');
    }

    protected getResourceForBuild(build: Build | undefined): PCB | undefined {
        if (!build?.entry) {
            return undefined;
        }

        return { path: build.pcb_path, exists: fs.existsSync(build.pcb_path) };
    }
}

// Singleton instance
const pcbWatcher = new PCBWatcher();

export const onPcbChanged = pcbWatcher.onChanged;
export const onPcbChangedEvent = { fire: (_: PCB | undefined) => {} }; // Deprecated

export function getCurrentPcb(): PCB | undefined {
    return pcbWatcher.getCurrent();
}

export function getPcbForBuild(buildTarget?: Build | undefined): PCB | undefined {
    const build = buildTarget || getBuildTarget();
    return pcbWatcher['getResourceForBuild'](build);
}

export function setCurrentPCB(pcb: PCB | undefined) {
    pcbWatcher.setCurrent(pcb);
}

export function eqPcb(a: PCB | undefined, b: PCB | undefined) {
    return pcbWatcher['equals'](a, b);
}

export async function activate(context: vscode.ExtensionContext) {
    await pcbWatcher.activate(context);
}

export function deactivate() {
    pcbWatcher.deactivate();
}
