import * as vscode from 'vscode';
import * as setup from './setup';
import * as buttons from './buttons';
import * as example from './example';
import * as kicanvas from './kicanvas';
import * as modelviewer from './modelviewer';
import * as treeVisualizer from './tree-visualizer';
import * as pinoutExplorer from './pinout-explorer';
import * as pcb from '../common/pcb';
import * as threeDModel from '../common/3dmodel';
import * as powerTree from '../common/power-tree';
import * as i2cTree from '../common/i2c-tree';
import * as pinout from '../common/pinout';
import { traceInfo } from '../common/log/logging';

export async function activate(context: vscode.ExtensionContext) {
    // Note: SidebarProvider and LogViewerProvider are registered in extension.ts
    // at the very start of activation so webviews load immediately
    traceInfo('UI: Activating UI components');

    // Register command to focus log viewer
    context.subscriptions.push(
        vscode.commands.registerCommand('atopile.showBuildLogs', () => {
            vscode.commands.executeCommand('atopile.logViewer.focus');
        })
    );

    // Activate other UI components in parallel
    await Promise.all([
        setup.activate(context),
        buttons.activate(context),
        example.activate(context),
        kicanvas.activate(context),
        modelviewer.activate(context),
        treeVisualizer.activate(context),
        pinoutExplorer.activate(context),
        pcb.activate(context),
        threeDModel.activate(context),
        powerTree.activate(context),
        i2cTree.activate(context),
        pinout.activate(context),
    ]);
}

export function deactivate() {
    setup.deactivate();
    buttons.deactivate();
    example.deactivate();
    kicanvas.deactivate();
    modelviewer.deactivate();
    treeVisualizer.deactivate();
    pinoutExplorer.deactivate();
    pcb.deactivate();
    threeDModel.deactivate();
    powerTree.deactivate();
    i2cTree.deactivate();
    pinout.deactivate();
}
