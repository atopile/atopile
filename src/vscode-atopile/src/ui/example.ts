import * as vscode from 'vscode';
import * as github from '../common/github';
import { promises as fsPromises } from 'fs';
import * as path from 'path';
import { traceInfo } from '../common/log/logging';
import * as buttons from './buttons';
import { captureEvent } from '../common/telemetry';

const REPO = 'atopile/atopile';
const REF = null;

interface Example {
    name: string;
    description: string;
    path: string;
}

export async function example_flow() {
    /**
     * This function is called by setup if we just installed the extension
     * or by a command.
     *
     * It will:
     *  - require the user to choose a destination folder
     *  - throw error if destination folder is not empty
     *  - download zip of atopile/atopile on github
     *  - extract examples/project into the chosen folder
     *  */
    // Notes:
    // - use github.ts to download and extract the zip
    //

    captureEvent('vsce:example_start');

    const examples: Example[] = [
        ...(await github.listDirectoriesInRepoSubfolder(REPO, REF, 'examples')).map((e) => ({
            name: e,
            description: 'Example project',
            path: `examples/${e}`,
        })),
    ];

    const example = await vscode.window.showQuickPick(
        examples.map((e) => ({ label: e.name, description: e.description })),
        {
            placeHolder: 'Select an example',
        },
    );

    if (example) {
        captureEvent('vsce:example_select', {
            example: example.label,
        });
    } else {
        captureEvent('vsce:example_select_cancel');
        return;
    }

    const examplePath = examples.find((e) => e.name === example.label)?.path;
    if (!examplePath) {
        vscode.window.showErrorMessage('Invalid example selected');
        return;
    }

    await vscode.window.withProgress(
        {
            location: vscode.ProgressLocation.Notification,
            title: 'Setting up atopile Example Project',
            cancellable: false,
        },
        async (progress) => {
            try {
                progress.report({ message: 'Checking workspace...' });
                const workspaceFolders = vscode.workspace.workspaceFolders;

                let destinationRoot: string | undefined;
                if (workspaceFolders && workspaceFolders.length > 0) {
                    destinationRoot = workspaceFolders[0].uri.fsPath;
                } else {
                    progress.report({ message: 'Choose destination folder...' });
                    const selected = await vscode.window.showOpenDialog({
                        canSelectFiles: false,
                        canSelectFolders: true,
                        canSelectMany: false,
                        openLabel: 'Use This Folder',
                    });
                    destinationRoot = selected?.[0]?.fsPath;
                }

                if (!destinationRoot) {
                    vscode.window.showInformationMessage('Example setup canceled: no destination folder selected.');
                    return;
                }

                progress.report({ message: 'Checking if destination folder is empty...' });
                const filesInWorkspace = await fsPromises.readdir(destinationRoot);
                const ignoredItems = ['.git', '.vscode', '.idea', 'node_modules', '.DS_Store', 'Thumbs.db'];
                const significantFiles = filesInWorkspace.filter(
                    (file) => !ignoredItems.includes(path.basename(file)),
                );

                if (significantFiles.length > 0) {
                    vscode.window.showErrorMessage(
                        'Destination folder is not empty. Choose an empty folder to load an example project.',
                    );
                    return;
                }

                progress.report({ message: 'Downloading and extracting example files...' });
                await github.downloadAndExtractRepoSubfolder(
                    REPO,
                    REF,
                    examplePath,
                    destinationRoot,
                );
                vscode.window.showInformationMessage(
                    `Example project loaded into: ${destinationRoot}`,
                );
                captureEvent('vsce:example_success');

                if (!workspaceFolders || workspaceFolders.length === 0) {
                    await vscode.commands.executeCommand('vscode.openFolder', vscode.Uri.file(destinationRoot), {
                        forceNewWindow: false,
                    });
                }

                await buttons.forceReloadButtons();
            } catch (error: any) {
                console.error('Failed to setup example project:', error);
                const message = error instanceof Error ? error.message : String(error);
                vscode.window.showErrorMessage(`Failed to load example project: ${message}`);
                captureEvent('vsce:example_fail', {
                    error: message,
                });
            }
        },
    );
}

export async function activate(context: vscode.ExtensionContext) {
    context.subscriptions.push(
        vscode.commands.registerCommand('atopile.example', () => {
            example_flow();
        }),
    );
}

export function deactivate() {
    // nothing to do
}
