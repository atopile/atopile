import * as vscode from 'vscode';
import * as path from 'path';

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
        // If no project is open, show the welcome view by returning no children.
        if (!vscode.workspace.workspaceFolders || vscode.workspace.workspaceFolders.length === 0) {
            return [];
        }

        const items: vscode.TreeItem[] = [];
        
        // Add button to open packages view
        const openPackagesBtn = new vscode.TreeItem('Open Packages');
        openPackagesBtn.command = {
            command: 'atopile.package_explorer',
            title: 'Open Package Explorer'
        };
        openPackagesBtn.iconPath = new vscode.ThemeIcon('package');
        items.push(openPackagesBtn);

        // TODO: Add your project tree items here
        // Example:
        // if (vscode.workspace.workspaceFolders) {
        //     // Add project files and folders
        // }

        return items;
    }
}

// Exported activate/deactivate so ui.ts can uniformly load modules
export function activate(context: vscode.ExtensionContext) {
    activateProjectView(context);
}

export function deactivate() {
    // Nothing to clean up currently
}

export function activateProjectView(context: vscode.ExtensionContext) {
    const projectViewProvider = new ProjectViewProvider();
    context.subscriptions.push(
        vscode.window.registerTreeDataProvider('atopile.project', projectViewProvider)
    );

    // Refresh when workspace changes
    vscode.workspace.onDidChangeWorkspaceFolders(() => {
        projectViewProvider.refresh();
    });
}