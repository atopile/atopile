/**
 * File operations for the sidebar webview.
 *
 * Handles rename, delete, create, duplicate, open-in-terminal,
 * list files, and load directory requests from the webview.
 */

import * as vscode from 'vscode';
import * as path from 'path';
import { traceInfo, traceError } from '../../common/log/logging';

export interface FileNode {
  name: string;
  path: string;
  type: 'file' | 'folder';
  extension?: string;
  children?: FileNode[];
  lazyLoad?: boolean;
}

export interface SidebarFileOperationsOptions {
  postToWebview: (msg: Record<string, unknown>) => void;
  notifyFilesChanged: () => void;
}

export class SidebarFileOperations {
  private readonly _postToWebview: (msg: Record<string, unknown>) => void;
  private readonly _notifyFilesChanged: () => void;

  constructor(opts: SidebarFileOperationsOptions) {
    this._postToWebview = opts.postToWebview;
    this._notifyFilesChanged = opts.notifyFilesChanged;
  }

  renameFile(oldPath: string, newPath: string): void {
    const oldUri = vscode.Uri.file(oldPath);
    const newUri = vscode.Uri.file(newPath);
    vscode.workspace.fs.rename(oldUri, newUri).then(
      () => {
        traceInfo(`[SidebarFileOps] Renamed ${oldPath} to ${newPath}`);
        this._notifyFilesChanged();
      },
      (err) => {
        traceError(`[SidebarFileOps] Failed to rename file: ${err}`);
        vscode.window.showErrorMessage(`Failed to rename: ${err.message || err}`);
      }
    );
  }

  deleteFile(filePath: string): void {
    const deleteUri = vscode.Uri.file(filePath);
    const fileName = path.basename(filePath);
    vscode.window.showWarningMessage(
      `Are you sure you want to delete "${fileName}"?`,
      { modal: true },
      'Delete'
    ).then((choice) => {
      if (choice === 'Delete') {
        vscode.workspace.fs.delete(deleteUri, { recursive: true, useTrash: true }).then(
          () => {
            traceInfo(`[SidebarFileOps] Deleted ${filePath}`);
            this._notifyFilesChanged();
          },
          (err) => {
            traceError(`[SidebarFileOps] Failed to delete file: ${err}`);
            vscode.window.showErrorMessage(`Failed to delete: ${err.message || err}`);
          }
        );
      }
    });
  }

  createFile(dirPath: string): void {
    vscode.window.showInputBox({
      prompt: 'Enter the file name',
      placeHolder: 'filename.ato',
      validateInput: (value) => {
        if (!value || !value.trim()) {
          return 'File name cannot be empty';
        }
        if (value.includes('/') || value.includes('\\')) {
          return 'File name cannot contain path separators';
        }
        return null;
      }
    }).then((fileName) => {
      if (fileName) {
        const newFilePath = path.join(dirPath, fileName);
        const newUri = vscode.Uri.file(newFilePath);
        vscode.workspace.fs.writeFile(newUri, new Uint8Array()).then(
          () => {
            traceInfo(`[SidebarFileOps] Created file ${newFilePath}`);
            this._notifyFilesChanged();
            // Open the new file
            vscode.workspace.openTextDocument(newUri).then((doc) => {
              vscode.window.showTextDocument(doc);
            });
          },
          (err) => {
            traceError(`[SidebarFileOps] Failed to create file: ${err}`);
            vscode.window.showErrorMessage(`Failed to create file: ${err.message || err}`);
          }
        );
      }
    });
  }

  createFolder(dirPath: string): void {
    vscode.window.showInputBox({
      prompt: 'Enter the folder name',
      placeHolder: 'new-folder',
      validateInput: (value) => {
        if (!value || !value.trim()) {
          return 'Folder name cannot be empty';
        }
        if (value.includes('/') || value.includes('\\')) {
          return 'Folder name cannot contain path separators';
        }
        return null;
      }
    }).then((folderName) => {
      if (folderName) {
        const newFolderPath = path.join(dirPath, folderName);
        const newUri = vscode.Uri.file(newFolderPath);
        vscode.workspace.fs.createDirectory(newUri).then(
          () => {
            traceInfo(`[SidebarFileOps] Created folder ${newFolderPath}`);
            this._notifyFilesChanged();
          },
          (err) => {
            traceError(`[SidebarFileOps] Failed to create folder: ${err}`);
            vscode.window.showErrorMessage(`Failed to create folder: ${err.message || err}`);
          }
        );
      }
    });
  }

  duplicateFile(sourcePath: string, destPath: string, newRelativePath: string): void {
    const sourceUri = vscode.Uri.file(sourcePath);
    const destUri = vscode.Uri.file(destPath);
    vscode.workspace.fs.copy(sourceUri, destUri, { overwrite: false }).then(
      () => {
        traceInfo(`[SidebarFileOps] Duplicated ${sourcePath} to ${destPath}`);
        this._notifyFilesChanged();
        // Notify webview to start rename mode on the new file
        this._postToWebview({
          type: 'fileDuplicated',
          newRelativePath,
        });
      },
      (err) => {
        traceError(`[SidebarFileOps] Failed to duplicate: ${err}`);
        vscode.window.showErrorMessage(`Failed to duplicate: ${err.message || err}`);
      }
    );
  }

  openInTerminal(dirPath: string): void {
    const terminal = vscode.window.createTerminal({
      cwd: dirPath,
      name: `Terminal: ${path.basename(dirPath)}`,
    });
    terminal.show();
    traceInfo(`[SidebarFileOps] Opened terminal at ${dirPath}`);
  }

  revealInFinder(filePath: string): void {
    void vscode.commands.executeCommand('revealFileInOS', vscode.Uri.file(filePath));
  }

  async listFiles(projectRoot: string, includeAll: boolean): Promise<void> {
    traceInfo(`[SidebarFileOps] Listing files for: ${projectRoot}, includeAll: ${includeAll}`);

    // Directories to completely exclude (not even show)
    const excludedDirs = new Set([
      '__pycache__',
      'node_modules',
      '.pytest_cache',
      '.mypy_cache',
      'dist',
      'egg-info',
    ]);

    // Hidden directories to show but lazy load (don't recurse into by default)
    const lazyLoadDirs = new Set([
      '.git',
      '.venv',
      '.ato',
      'build',
      'venv',
    ]);

    const buildFileTree = async (dirUri: vscode.Uri, basePath: string): Promise<FileNode[]> => {
      const nodes: FileNode[] = [];

      try {
        const entries = await vscode.workspace.fs.readDirectory(dirUri);

        // Sort: directories first, then alphabetically
        entries.sort((a, b) => {
          const aIsDir = (a[1] & vscode.FileType.Directory) !== 0;
          const bIsDir = (b[1] & vscode.FileType.Directory) !== 0;
          if (aIsDir !== bIsDir) return aIsDir ? -1 : 1;
          return a[0].toLowerCase().localeCompare(b[0].toLowerCase());
        });

        for (const [name, fileType] of entries) {
          // Skip completely excluded directories
          if (excludedDirs.has(name)) continue;
          if (name.endsWith('.egg-info')) continue;

          const relativePath = basePath ? `${basePath}/${name}` : name;
          const itemUri = vscode.Uri.joinPath(dirUri, name);
          const isHidden = name.startsWith('.');

          if ((fileType & vscode.FileType.Directory) !== 0) {
            // Check if this directory should be lazy loaded
            const shouldLazyLoad = lazyLoadDirs.has(name) || (isHidden && !includeAll);

            if (shouldLazyLoad) {
              // Show the directory but mark it for lazy loading
              nodes.push({
                name,
                path: relativePath,
                type: 'folder',
                children: [],
                lazyLoad: true,
              });
            } else {
              const children = await buildFileTree(itemUri, relativePath);
              // Skip empty directories unless includeAll
              if (children.length > 0 || includeAll) {
                nodes.push({
                  name,
                  path: relativePath,
                  type: 'folder',
                  children,
                });
              }
            }
          } else if ((fileType & vscode.FileType.File) !== 0) {
            // Skip hidden files unless includeAll
            if (isHidden && !includeAll) continue;

            // If not includeAll, only include .ato and .py files
            if (!includeAll) {
              const ext = name.split('.').pop()?.toLowerCase();
              if (ext !== 'ato' && ext !== 'py') continue;
            }

            const ext = name.includes('.') ? name.split('.').pop()?.toLowerCase() : undefined;
            nodes.push({
              name,
              path: relativePath,
              type: 'file',
              extension: ext,
            });
          }
        }
      } catch (err) {
        traceError(`[SidebarFileOps] Error reading directory ${dirUri.fsPath}: ${err}`);
      }

      return nodes;
    };

    try {
      const rootUri = vscode.Uri.file(projectRoot);
      const files = await buildFileTree(rootUri, '');

      // Count total files (excluding lazy-loaded directories)
      const countFiles = (nodes: FileNode[]): number => {
        let count = 0;
        for (const node of nodes) {
          if (node.type === 'file') {
            count++;
          } else if (node.children && !node.lazyLoad) {
            count += countFiles(node.children);
          }
        }
        return count;
      };

      const total = countFiles(files);

      this._postToWebview({
        type: 'filesListed',
        projectRoot,
        files,
        total,
      });

      traceInfo(`[SidebarFileOps] Listed ${total} files for ${projectRoot}`);
    } catch (err) {
      traceError(`[SidebarFileOps] Failed to list files: ${err}`);
      this._postToWebview({
        type: 'filesListed',
        projectRoot,
        files: [],
        total: 0,
        error: err instanceof Error ? err.message : String(err),
      });
    }
  }

  async loadDirectory(projectRoot: string, directoryPath: string): Promise<void> {
    traceInfo(`[SidebarFileOps] Loading directory: ${directoryPath} in ${projectRoot}`);

    try {
      const dirUri = vscode.Uri.file(path.join(projectRoot, directoryPath));
      const entries = await vscode.workspace.fs.readDirectory(dirUri);
      const nodes: FileNode[] = [];

      // Sort: directories first, then alphabetically
      entries.sort((a, b) => {
        const aIsDir = (a[1] & vscode.FileType.Directory) !== 0;
        const bIsDir = (b[1] & vscode.FileType.Directory) !== 0;
        if (aIsDir !== bIsDir) return aIsDir ? -1 : 1;
        return a[0].toLowerCase().localeCompare(b[0].toLowerCase());
      });

      for (const [name, fileType] of entries) {
        const relativePath = `${directoryPath}/${name}`;

        if ((fileType & vscode.FileType.Directory) !== 0) {
          nodes.push({
            name,
            path: relativePath,
            type: 'folder',
            children: [],
            lazyLoad: true,
          });
        } else if ((fileType & vscode.FileType.File) !== 0) {
          const ext = name.includes('.') ? name.split('.').pop()?.toLowerCase() : undefined;
          nodes.push({
            name,
            path: relativePath,
            type: 'file',
            extension: ext,
          });
        }
      }

      this._postToWebview({
        type: 'directoryLoaded',
        projectRoot,
        directoryPath,
        children: nodes,
      });

      traceInfo(`[SidebarFileOps] Loaded ${nodes.length} items in ${directoryPath}`);
    } catch (err) {
      traceError(`[SidebarFileOps] Failed to load directory: ${err}`);
      this._postToWebview({
        type: 'directoryLoaded',
        projectRoot,
        directoryPath,
        children: [],
        error: err instanceof Error ? err.message : String(err),
      });
    }
  }
}
