import * as vscode from 'vscode';

export class WelcomeViewProvider implements vscode.TreeDataProvider<vscode.TreeItem> {
    private _onDidChangeTreeData = new vscode.EventEmitter<vscode.TreeItem | undefined | null | void>();
    readonly onDidChangeTreeData = this._onDidChangeTreeData.event;

    refresh(): void {
        this._onDidChangeTreeData.fire();
    }

    getTreeItem(element: vscode.TreeItem): vscode.TreeItem {
        return element;
    }

    async getChildren(_element?: vscode.TreeItem): Promise<vscode.TreeItem[]> {
        // Return empty array to show the welcome content
        return [];
    }
}

export function activateWelcomeView(context: vscode.ExtensionContext) {
    const welcomeViewProvider = new WelcomeViewProvider();
    context.subscriptions.push(
        vscode.window.registerTreeDataProvider('atopile.welcome', welcomeViewProvider)
    );
}