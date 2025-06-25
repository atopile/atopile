import * as vscode from 'vscode';
import * as setup from './setup';
import * as buttons from './buttons';
import * as example from './example';
import * as kicanvas from './kicanvas';
import * as projectViewer from './projectview';
import * as pcb from '../common/pcb';

export async function activate(context: vscode.ExtensionContext) {
    await setup.activate(context);
    await buttons.activate(context);
    await example.activate(context);
    await kicanvas.activate(context);
    await projectViewer.activate(context);
    await pcb.activate(context);
}

export function deactivate() {
    setup.deactivate();
    buttons.deactivate();
    example.deactivate();
    kicanvas.deactivate();
    projectViewer.deactivate();
    pcb.deactivate();
}
