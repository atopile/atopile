import * as vscode from 'vscode';
import * as setup from './setup';
import * as buttons from './buttons';
import * as example from './example';
import * as kicanvas from './kicanvas';
import * as modelviewer from './modelviewer';
import * as sidebarPanel from './sidebarPanel';
import * as logViewerPanel from './logViewerPanel';
import * as pcb from '../common/pcb';
import * as threeDModel from '../common/3dmodel';

export async function activate(context: vscode.ExtensionContext) {
    await setup.activate(context);
    await buttons.activate(context);
    await example.activate(context);
    await kicanvas.activate(context);
    await modelviewer.activate(context);
    await sidebarPanel.activate(context);
    await logViewerPanel.activate(context);
    await pcb.activate(context);
    await threeDModel.activate(context);
}

export function deactivate() {
    setup.deactivate();
    buttons.deactivate();
    example.deactivate();
    kicanvas.deactivate();
    modelviewer.deactivate();
    sidebarPanel.deactivate();
    logViewerPanel.deactivate();
    pcb.deactivate();
    threeDModel.deactivate();
}
