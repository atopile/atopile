import * as vscode from 'vscode';
import * as setup from './setup';
import * as buttons from './buttons';
import * as example from './example';
import * as packageViewer from './packageViewer';
import * as projectViewer from './projectView';

export async function activate(context: vscode.ExtensionContext) {
    await setup.activate(context);
    await buttons.activate(context);
    await example.activate(context);
    await packageViewer.activate(context);
    await projectViewer.activate(context);
}

export function deactivate() {
    setup.deactivate();
    buttons.deactivate();
    example.deactivate();
    packageViewer.deactivate();
    projectViewer.deactivate();
}
