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

        /**
         * Helper to create a button-like TreeItem
         */
        const pushButton = (label: string, command: string, icon: string, tooltip?: string) => {
            const item = new vscode.TreeItem(label);
            item.command = { command, title: label };
            item.iconPath = new vscode.ThemeIcon(icon);
            if (tooltip) {
                item.tooltip = tooltip;
            }
            items.push(item);
        };

        // Map of status-bar actions we mirror here
        pushButton('ATO Shell', 'atopile.shell', 'terminal', 'Open ato shell');
        pushButton('Create Project', 'atopile.create_project', 'new-file', 'Create new project');
        pushButton('Add Part', 'atopile.add_part', 'file-binary', 'Add part to project');
        pushButton('Add Package', 'atopile.add_package', 'package', 'Add package dependency');
        pushButton('Remove Package', 'atopile.remove_package', 'trash', 'Remove package dependency');
        pushButton('Build', 'atopile.build', 'play', 'Build project');
        pushButton('Launch KiCad', 'atopile.launch_kicad', 'circuit-board', 'Open board in KiCad');
        pushButton('Open Package Explorer', 'atopile.package_explorer', 'package', 'Open Package Explorer');
        pushButton('Choose Build Target', 'atopile.choose_build', 'gear', 'Select active build target');

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