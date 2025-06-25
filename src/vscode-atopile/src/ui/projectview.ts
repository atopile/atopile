import * as vscode from 'vscode';
import { getButtons } from './buttons';
import { getManifests } from '../common/manifest';

export class ProjectViewProvider implements vscode.TreeDataProvider<vscode.TreeItem> {
    private _onDidChangeTreeData = new vscode.EventEmitter<vscode.TreeItem | undefined | null | void>();
    readonly onDidChangeTreeData = this._onDidChangeTreeData.event;

    refresh(): void {
        this._onDidChangeTreeData.fire();
    }

    getTreeItem(element: vscode.TreeItem): vscode.TreeItem {
        return element;
    }

    async getChildren(_element?: vscode.TreeItem): Promise<vscode.TreeItem[]> {
        // If the workspace contains no `ato.yaml`, do not show any buttons (let the project view take over).
        const manifests = getManifests();
        if (manifests.length == 0) {
            return [];
        }

        const items: vscode.TreeItem[] = [];

        // Show toolbar buttons
        for (const button of getButtons()) {
            const item = new vscode.TreeItem(button.description);
            item.command = { command: button.command.getCommandName(), title: button.description };
            item.iconPath = button.icon;
            item.tooltip = button.tooltip;
            items.push(item);
        }
        return items;
    }
}

// Exported activate/deactivate so ui.ts can uniformly load modules
export async function activate(context: vscode.ExtensionContext) {
    const projectViewProvider = new ProjectViewProvider();
    context.subscriptions.push(vscode.window.registerTreeDataProvider('atopile.project', projectViewProvider));

    // Refresh when workspace changes
    vscode.workspace.onDidChangeWorkspaceFolders(() => {
        projectViewProvider.refresh();
    });
}

export function deactivate() {
    // Nothing to clean up currently
}
