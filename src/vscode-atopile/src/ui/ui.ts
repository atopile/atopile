import * as vscode from 'vscode';
import * as setup from './setup';
import * as buttons from './buttons';
import * as example from './example';
import * as kicanvas from './kicanvas';
import * as modelviewer from './modelviewer';
import * as pcb from '../common/pcb';
import * as threeDModel from '../common/3dmodel';
import { SidebarProvider, LogViewerProvider } from '../providers';
import { traceInfo } from '../common/log/logging';

export async function activate(context: vscode.ExtensionContext) {
    await setup.activate(context);
    await buttons.activate(context);
    await example.activate(context);
    await kicanvas.activate(context);
    await modelviewer.activate(context);

    // NEW ARCHITECTURE: Stateless providers that load React app
    // React app talks directly to Python backend (no extension state)
    traceInfo('UI: Using stateless webview providers');

    // Register stateless sidebar provider
    const sidebarProvider = new SidebarProvider(context.extensionUri);
    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider(
            SidebarProvider.viewType,
            sidebarProvider
        )
    );

    // Register stateless log viewer provider
    const logViewerProvider = new LogViewerProvider(context.extensionUri);
    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider(
            LogViewerProvider.viewType,
            logViewerProvider
        )
    );

    // Register command to focus log viewer
    context.subscriptions.push(
        vscode.commands.registerCommand('atopile.showBuildLogs', () => {
            vscode.commands.executeCommand('atopile.logViewer.focus');
        })
    );

    await pcb.activate(context);
    await threeDModel.activate(context);
}

export function deactivate() {
    setup.deactivate();
    buttons.deactivate();
    example.deactivate();
    kicanvas.deactivate();
    modelviewer.deactivate();
    pcb.deactivate();
    threeDModel.deactivate();
}
