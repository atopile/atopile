import * as vscode from 'vscode';
import { getExtension } from './vscodeapi';

export function getLogoUri() {
    return vscode.Uri.joinPath(getExtension().extensionUri, 'ato_logo_256x256.png');
}
