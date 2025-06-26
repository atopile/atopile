import * as vscode from 'vscode';
import { getBuildTarget, onBuildTargetChanged } from '../common/target';
import { traceInfo } from './log/logging';
import { Build } from './manifest';
import * as fs from 'fs';

export interface FileResource {
    path: string;
    exists: boolean;
}

export abstract class FileResourceWatcher<T extends FileResource> {
    private watcher: vscode.FileSystemWatcher | undefined;
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

    private setupWatcher(resource: T | undefined): void {
        this.disposeWatcher();

        if (!resource) {
            return;
        }

        this.watcher = vscode.workspace.createFileSystemWatcher(resource.path);

        const onChange = () => {
            traceInfo(`${this.resourceName} watcher triggered for ${resource.path}`);
            this.notifyChange(resource);
        };

        const onCreateDelete = () => {
            this.setCurrent(this.getResourceForBuild(getBuildTarget()));
        };

        this.watcher.onDidChange(onChange);
        this.watcher.onDidCreate(onCreateDelete);
        this.watcher.onDidDelete(onCreateDelete);
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