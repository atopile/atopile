import * as vscode from 'vscode';
import * as github from '../common/github';
import { promises as fsPromises } from 'fs';
import * as path from 'path';
import * as os from 'os';
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
     *  - throw error if workspace is open and not empty
     *  - download zip of atopile/atopile on github
     *  - extract examples/project into either
     *    a) the cwd if no workspace is open and switch to the folder in vscode
     *    b) the first folder in the workspace if a workspace is open and empty
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
            title: 'Setting up Atopile Example Project',
            cancellable: false,
        },
        async (progress) => {
            try {
                progress.report({ message: 'Checking workspace...' });
                const workspaceFolders = vscode.workspace.workspaceFolders;

                if (!workspaceFolders || workspaceFolders.length === 0) {
                    // No workspace is open
                    progress.report({ message: 'Creating temporary directory for project...' });

                    const tempBaseDir = await fsPromises.mkdtemp(path.join(os.tmpdir(), 'atopile-eg-'));
                    const projectPath = path.join(tempBaseDir, 'atopile-example-project');
                    // Ensure the specific project path exists for extraction
                    await fsPromises.mkdir(projectPath, { recursive: true });

                    progress.report({ message: 'Downloading and extracting example files...' });
                    await github.downloadAndExtractRepoSubfolder(REPO, REF, examplePath, projectPath);

                    vscode.window.showInformationMessage(`Example project downloaded. Opening: ${projectPath}`);
                    // Open the extracted project in the current window or a new one
                    await vscode.commands.executeCommand('vscode.openFolder', vscode.Uri.file(projectPath), {
                        forceNewWindow: false, // Try to open in current window
                    });
                } else {
                    // A workspace is open
                    const workspaceRoot = workspaceFolders[0].uri.fsPath;

                    progress.report({ message: 'Checking if workspace is empty...' });
                    const filesInWorkspace = await fsPromises.readdir(workspaceRoot);
                    const ignoredItems = ['.git', '.vscode', '.idea', 'node_modules', '.DS_Store', 'Thumbs.db'];
                    const significantFiles = filesInWorkspace.filter(
                        (file) => !ignoredItems.includes(path.basename(file)),
                    );

                    if (significantFiles.length > 0) {
                        vscode.window.showErrorMessage(
                            'Current workspace is not empty. Please use an empty folder or close the current workspace to load the example project.',
                        );
                        return; // Exit early
                    }

                    // Workspace is open and empty, extract here
                    progress.report({ message: 'Downloading and extracting example into workspace...' });
                    await github.downloadAndExtractRepoSubfolder(
                        REPO,
                        REF,
                        examplePath,
                        workspaceRoot, // Extract directly into the workspace root
                    );
                    vscode.window.showInformationMessage(
                        `Example project loaded into current workspace: ${workspaceRoot}`,
                    );

                    captureEvent('vsce:example_success');
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
