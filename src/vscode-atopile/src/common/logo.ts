import * as vscode from 'vscode';

let g_extensionContext: vscode.ExtensionContext;

export function getLogoUri() {
    return vscode.Uri.joinPath(g_extensionContext.extensionUri, 'ato_logo_256x256.png');
}

export function activate(context: vscode.ExtensionContext) {
    g_extensionContext = context;
}
