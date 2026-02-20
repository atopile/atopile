/**
 * File system watcher for the sidebar.
 *
 * Watches a project root directory and notifies the webview when files
 * are created or deleted (renames appear as delete + create).
 */

import * as vscode from 'vscode';
import { traceInfo } from '../../common/log/logging';

export interface SidebarFileWatcherOptions {
  postToWebview: (msg: Record<string, unknown>) => void;
  debounceMs?: number;
}

export class SidebarFileWatcher {
  private readonly _postToWebview: (msg: Record<string, unknown>) => void;
  private readonly _debounceMs: number;

  private _fileWatcher?: vscode.FileSystemWatcher;
  private _watchedProjectRoot: string | null = null;
  private _fileChangeDebounce: NodeJS.Timeout | null = null;

  constructor(opts: SidebarFileWatcherOptions) {
    this._postToWebview = opts.postToWebview;
    this._debounceMs = opts.debounceMs ?? 300;
  }

  get watchedProjectRoot(): string | null {
    return this._watchedProjectRoot;
  }

  /**
   * Set up a file watcher for the given project root.
   * Notifies the webview when files change so it can refresh.
   */
  watch(projectRoot: string): void {
    // Skip if already watching this project
    if (this._watchedProjectRoot === projectRoot && this._fileWatcher) {
      return;
    }

    // Dispose existing watcher
    this.unwatch();
    this._watchedProjectRoot = projectRoot;

    // Watch all files in the project
    const pattern = new vscode.RelativePattern(projectRoot, '**/*');
    this._fileWatcher = vscode.workspace.createFileSystemWatcher(pattern);

    // Debounced notification to avoid flooding on bulk operations
    const notifyChange = (uri: vscode.Uri) => {
      // Ignore changes in .git directory
      const relativePath = uri.fsPath.substring(projectRoot.length);
      if (relativePath.includes('/.git/') || relativePath.includes('\\.git\\')) {
        return;
      }

      if (this._fileChangeDebounce) {
        clearTimeout(this._fileChangeDebounce);
      }
      this._fileChangeDebounce = setTimeout(() => {
        traceInfo(`[SidebarFileWatcher] Files changed in ${projectRoot}`);
        this._postToWebview({
          type: 'filesChanged',
          projectRoot,
        });
      }, this._debounceMs);
    };

    this._fileWatcher.onDidCreate(notifyChange);
    this._fileWatcher.onDidDelete(notifyChange);
    this._fileWatcher.onDidChange(() => {
      // Don't notify on content changes, only create/delete/rename
      // Renames appear as delete + create, so they're covered
    });

    traceInfo(`[SidebarFileWatcher] File watcher set up for ${projectRoot}`);
  }

  /**
   * Dispose the current file watcher and clear debounce timer.
   */
  unwatch(): void {
    if (this._fileWatcher) {
      this._fileWatcher.dispose();
      this._fileWatcher = undefined;
    }
    if (this._fileChangeDebounce) {
      clearTimeout(this._fileChangeDebounce);
      this._fileChangeDebounce = null;
    }
    this._watchedProjectRoot = null;
  }

  /**
   * Notify the webview that files have changed so it refreshes the file explorer.
   * Called after file operations to avoid relying solely on FileSystemWatcher
   * (which can silently fail in Docker/containerized environments due to inotify limits).
   */
  notifyFilesChanged(): void {
    if (this._watchedProjectRoot) {
      // Debounce to coalesce rapid operations (e.g. bulk delete)
      if (this._fileChangeDebounce) {
        clearTimeout(this._fileChangeDebounce);
      }
      this._fileChangeDebounce = setTimeout(() => {
        traceInfo(`[SidebarFileWatcher] Notifying webview of file changes in ${this._watchedProjectRoot}`);
        this._postToWebview({
          type: 'filesChanged',
          projectRoot: this._watchedProjectRoot,
        });
      }, this._debounceMs);
    }
  }

  dispose(): void {
    this.unwatch();
  }
}
