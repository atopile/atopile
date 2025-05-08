import * as vscode from 'vscode';
import * as setup from './setup';
import * as buttons from './buttons';

export async function activate(context: vscode.ExtensionContext) {
    await setup.activate(context);
    await buttons.activate(context);
}

export function deactivate() {
    setup.deactivate();
    buttons.deactivate();
}
