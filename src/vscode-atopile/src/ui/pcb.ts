import * as vscode from 'vscode';
import { glob } from 'glob';
import * as path from 'path';
import * as fs from 'fs';
import { getCurrentBuild } from './buttons';
import { traceInfo } from '../common/log/logging';

/**
 * Attempt to locate a KiCad PCB inside the workspace or from the active editor.
 * Returns a vscode.Uri or undefined.
 */
export async function findPcbUri(): Promise<vscode.Uri | undefined> {
    const active = vscode.window.activeTextEditor?.document.uri;
    if (active && active.fsPath.endsWith('.kicad_pcb')) {
        return active;
    }

    const results = await glob('**/*.kicad_pcb', {
        cwd: vscode.workspace.workspaceFolders?.[0].uri.fsPath ?? '.',
        absolute: true,
    });

    if (results.length === 0) {
        return undefined;
    }
    if (results.length === 1) {
        return vscode.Uri.file(results[0]);
    }
    return undefined;
}

export class PcbManager {
    private watcher?: vscode.FileSystemWatcher;
    private currentPcbPath?: string;
    private changeListeners: ((uri: vscode.Uri) => void)[] = [];

    getPcbForBuild(buildTarget?: any): vscode.Uri | undefined {
        const build = buildTarget || getCurrentBuild();
        traceInfo(`getPcbForBuild called with build: ${build?.entry || 'undefined'}`);

        if (!build?.entry) {
            traceInfo('No build entry found');
            return undefined;
        }

        if (fs.existsSync(build.entry)) {
            traceInfo(`PCB file exists at: ${build.entry}`);
            return vscode.Uri.file(build.entry);
        }

        // Try resolving via layoutDir if provided
        if (build.layoutDir) {
            const absLayoutDir = path.resolve(build.root, build.layoutDir);
            const matches = glob.sync('*.kicad_pcb', { cwd: absLayoutDir, absolute: true });
            if (matches.length > 0) {
                return vscode.Uri.file(matches[0]);
            }
        }
        // Last resort: search project for a PCB matching build name
        const searchBase = build.layoutDir ? path.resolve(build.root, build.layoutDir) : build.root;
        const pattern = `**/${build.name}.kicad_pcb`;
        const found = glob.sync(pattern, { cwd: searchBase, absolute: true });
        if (found.length > 0) {
            return vscode.Uri.file(found[0]);
        }
        traceInfo(`PCB file not found after fallback search for pattern ${pattern} in ${searchBase}`);
        return undefined;
    }

    setPcbPath(pcbPath: string) {
        if (this.currentPcbPath === pcbPath) {
            return;
        }

        this.disposeWatcher();
        this.currentPcbPath = pcbPath;
        this.setupWatcher(pcbPath);
        this.notifyChange(vscode.Uri.file(pcbPath));
    }

    onPcbChanged(listener: (uri: vscode.Uri) => void): vscode.Disposable {
        this.changeListeners.push(listener);
        return {
            dispose: () => {
                const index = this.changeListeners.indexOf(listener);
                if (index >= 0) {
                    this.changeListeners.splice(index, 1);
                }
            },
        };
    }

    private notifyChange(uri: vscode.Uri) {
        this.changeListeners.forEach((listener) => listener(uri));
    }

    private setupWatcher(pcbPath: string) {
        this.watcher = vscode.workspace.createFileSystemWatcher(
            new vscode.RelativePattern(path.dirname(pcbPath), '*.kicad_pcb'),
        );

        const onChange = () => {
            traceInfo(`PCB watcher triggered for ${pcbPath}`);
            this.notifyChange(vscode.Uri.file(pcbPath));
        };

        this.watcher.onDidChange(onChange);
        this.watcher.onDidCreate(onChange);
        this.watcher.onDidDelete(onChange);
    }

    disposeWatcher() {
        if (this.watcher) {
            this.watcher.dispose();
            this.watcher = undefined;
        }
    }

    dispose() {
        this.disposeWatcher();
        this.changeListeners = [];
    }
}

export const pcbManager = new PcbManager();

export function watchPcb(pcbPath: string, onChange: () => void): vscode.FileSystemWatcher {
    const watcher = vscode.workspace.createFileSystemWatcher(
        new vscode.RelativePattern(path.dirname(pcbPath), '*.kicad_pcb'),
    );
    watcher.onDidChange(onChange);
    watcher.onDidCreate(onChange);
    watcher.onDidDelete(onChange);
    return watcher;
}
