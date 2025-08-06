import * as vscode from 'vscode';
import { getBuildTarget, onBuildTargetChanged } from '../common/target';
import { traceVerbose, traceInfo } from './log/logging';
import { Build } from './manifest';
import * as fs from 'fs';

export interface FileResource {
    path: string;
    exists: boolean;
}

enum FileEventType {
    Change = 'change',
    Create = 'create',
    Delete = 'delete',
    Unchanged = 'unchanged',
}

class FileWatcher implements vscode.Disposable {
    private watcher: vscode.FileSystemWatcher;
    private subscriptions: ((type: FileEventType) => void)[] = [];
    private timer: NodeJS.Timeout;

    constructor(
        private file_path: string,
        callback: ((type: FileEventType) => void) | undefined,
    ) {
        if (fs.existsSync(this.file_path)) {
            this.last_mtime = fs.statSync(this.file_path).mtimeMs;
        }
        if (callback) {
            this.subscriptions.push(callback);
        }

        this.watcher = vscode.workspace.createFileSystemWatcher(this.file_path);

        this.watcher.onDidChange((_) => {
            traceVerbose(`vscode: ${this.file_path} changed`);
            this.handle();
        });
        this.watcher.onDidCreate((_) => {
            traceVerbose(`vscode: ${this.file_path} created`);
            this.handle();
        });
        this.watcher.onDidDelete((_) => {
            traceVerbose(`vscode: ${this.file_path} deleted`);
            this.handle();
        });

        // setup timer to check if the file has been modified
        this.timer = setInterval(() => {
            this.handle();
        }, 1000);
    }

    private last_mtime: number | undefined;
    private checkForChangesAndSave(): FileEventType {
        // TODO handle mTime missing
        const mtime = fs.statSync(this.file_path).mtimeMs;
        if (mtime === this.last_mtime) {
            return FileEventType.Unchanged;
        }
        traceVerbose(`${this.file_path} mtime: ${mtime}, last_mtime: ${this.last_mtime}`);
        const existed_before = this.last_mtime !== undefined;
        const exists_now = mtime !== undefined;
        this.last_mtime = mtime;
        if (existed_before && !exists_now) {
            return FileEventType.Delete;
        }
        if (!existed_before && exists_now) {
            return FileEventType.Create;
        }
        return FileEventType.Change;
    }

    private handle(): void {
        const file_event = this.checkForChangesAndSave();
        if (file_event === FileEventType.Unchanged) {
            return;
        }
        this.subscriptions.forEach((callback) => callback(file_event));
    }

    public subscribe(callback: (type: FileEventType) => void): void {
        this.subscriptions.push(callback);
    }

    public dispose(): void {
        this.watcher.dispose();
        clearInterval(this.timer);
    }
}

export abstract class FileResourceWatcher<T extends FileResource> {
    private watcher: FileWatcher | undefined;
    private current: T | undefined;
    private onChangedEvent: vscode.EventEmitter<T | undefined>;
    public readonly onChanged: vscode.Event<T | undefined>;

    constructor(private resourceName: string) {
        this.onChangedEvent = new vscode.EventEmitter<T | undefined>();
        this.onChanged = this.onChangedEvent.event;
    }

    protected abstract getResourceForBuild(build: Build | undefined): T | undefined;

    public getCurrent(): T | undefined {
        const build = getBuildTarget();
        if (!build) {
            return undefined;
        }
        return this.getResourceForBuild(build);
    }

    public setCurrent(resource: T | undefined): void {
        if (this.equals(this.current, resource)) {
            return;
        }

        this.current = resource;
        this.setupWatcher(resource);
        this.notifyChange(resource);
    }

    protected equals(a: T | undefined, b: T | undefined): boolean {
        if ((a === undefined) !== (b === undefined)) {
            return false;
        }
        if (a === undefined || b === undefined) {
            return true;
        }
        return a.path === b.path && a.exists === b.exists;
    }

    private notifyChange(resource: T | undefined): void {
        this.onChangedEvent.fire(resource);
    }

    public forceNotify(): void {
        this.notifyChange(this.current);
    }

    private setupWatcher(resource: T | undefined): void {
        this.disposeWatcher();

        if (!resource) {
            return;
        }

        traceInfo(`Setting up watcher for ${resource.path}`);
        this.watcher = new FileWatcher(resource.path, (type) => {
            traceInfo(`${this.resourceName} watcher triggered by ${type} for ${resource.path}`);
            if (type === FileEventType.Change) {
                this.notifyChange(resource);
            } else {
                this.setCurrent(this.getResourceForBuild(getBuildTarget()));
            }
        });
    }

    private disposeWatcher(): void {
        if (this.watcher) {
            this.watcher.dispose();
            this.watcher = undefined;
        }
    }

    public async activate(context: vscode.ExtensionContext): Promise<void> {
        context.subscriptions.push(
            onBuildTargetChanged(async (target: Build | undefined) => {
                this.setCurrent(this.getResourceForBuild(target));
            }),
        );
        this.setCurrent(this.getResourceForBuild(getBuildTarget()));
    }

    public deactivate(): void {
        this.disposeWatcher();
    }

    public dispose(): void {
        this.disposeWatcher();
        this.onChangedEvent.dispose();
    }
}
