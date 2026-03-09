/**
 * File operations for the sidebar webview.
 *
 * Handles rename, delete, create, duplicate, and open-in-terminal
 * requests from the webview.
 */

import * as vscode from 'vscode';
import * as path from 'path';
import { traceInfo, traceError } from '../../common/log/logging';

export interface SidebarFileOperationsOptions {
  postToWebview: (msg: Record<string, unknown>) => void;
}

export class SidebarFileOperations {
  private readonly _postToWebview: (msg: Record<string, unknown>) => void;

  constructor(opts: SidebarFileOperationsOptions) {
    this._postToWebview = opts.postToWebview;
  }

  renameFile(oldPath: string, newPath: string): void {
    const oldUri = vscode.Uri.file(oldPath);
    const newUri = vscode.Uri.file(newPath);
    vscode.workspace.fs.rename(oldUri, newUri).then(
      () => {
        traceInfo(`[SidebarFileOps] Renamed ${oldPath} to ${newPath}`);
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
}
