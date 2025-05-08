import * as vscode from 'vscode';
import * as buttons from './buttons';

export async function activate(context: vscode.ExtensionContext) {
    buttons.activate(context);
}

export function deactivate() {}
