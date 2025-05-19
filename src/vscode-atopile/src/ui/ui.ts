import * as vscode from 'vscode';
import * as setup from './setup';
import * as buttons from './buttons';
import * as example from './example';

export async function activate(context: vscode.ExtensionContext) {
    await setup.activate(context);
    await buttons.activate(context);
    await example.activate(context);
}

export function deactivate() {
    setup.deactivate();
    buttons.deactivate();
    example.deactivate();
}
