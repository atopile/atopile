/**
 * VS Code Panel Providers - Webview setup and action routing.
 *
 * NO STATE HERE. All state lives in appStateManager.
 * Panels receive state via onStateChange and send actions back.
 */

import * as vscode from 'vscode';
import * as path from 'path';
import { traceInfo } from '../common/log/logging';
import { appStateManager, Project, LogLevel } from '../common/appState';
import { getBuilds } from '../common/manifest';
import {
    getProjectRoot,
    setProjectRoot,
    getSelectedTargets,
    setSelectedTargets,
    toggleTarget as toggleTargetInConfig,
    onBuildTargetsChanged,
} from '../common/target';
import {
    findWebviewAssets,
    buildWebviewHtml,
    getWebviewLocalResourceRoots,
} from './webview-utils';

/**
 * Convert manifest builds to projects grouped by root directory.
 */
function getProjects(): Project[] {
    const builds = getBuilds();
    const projectMap = new Map<string, Project>();

    for (const build of builds) {
        if (!projectMap.has(build.root)) {
            projectMap.set(build.root, {
                root: build.root,
                name: path.basename(build.root),
                targets: [],
            });
        }
        projectMap.get(build.root)!.targets.push({
            name: build.name,
            entry: build.entry,
            root: build.root,
        });
    }

    return Array.from(projectMap.values());
}

/**
 * Sync projects from manifest to state manager.
 */
function syncProjectsToState(): void {
    const projects = getProjects();
    const selectedRoot = getProjectRoot();
    const selectedTargets = getSelectedTargets();

    appStateManager.setProjects(projects);
    appStateManager.setSelectedProjectRoot(selectedRoot || null);
    appStateManager.setSelectedTargetNames(selectedTargets.map(t => t.name));
}

/**
 * Generic webview panel that handles VS Code boilerplate.
 */
class WebviewPanel implements vscode.WebviewViewProvider {
    private _view?: vscode.WebviewView;
    private _onMessage?: (message: any) => Promise<void>;

    constructor(
        private readonly _extensionUri: vscode.Uri,
        private readonly _webviewName: string,
        private readonly _title: string,
    ) {}

    public resolveWebviewView(
        webviewView: vscode.WebviewView,
        _context: vscode.WebviewViewResolveContext,
        _token: vscode.CancellationToken
    ): void {
        this._view = webviewView;

        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: [
                ...getWebviewLocalResourceRoots(this._extensionUri),
                this._extensionUri,
            ],
        };

        const assets = findWebviewAssets(this._extensionUri.fsPath, this._webviewName);
        webviewView.webview.html = buildWebviewHtml({
            webview: webviewView.webview,
            assets,
            title: this._title,
        });

        webviewView.webview.onDidReceiveMessage(async (message) => {
            if (message.type === 'ready') {
                // Send initial state on ready
                this.postMessage('state', appStateManager.getState());
            } else if (message.type === 'action' && this._onMessage) {
                await this._onMessage(message);
            }
        });
    }

    postMessage(type: string, data: any): void {
        if (!this._view) return;
        this._view.webview.postMessage({ type, data });
    }

    getWebviewUri(filePath: string): string {
        if (!this._view) return '';
        return this._view.webview.asWebviewUri(vscode.Uri.file(filePath)).toString();
    }

    setOnMessage(handler: (message: any) => Promise<void>): void {
        this._onMessage = handler;
    }

    get isVisible(): boolean {
        return this._view?.visible ?? false;
    }
}

// Panel instances
let sidebarPanel: WebviewPanel | undefined;
let logViewerPanel: WebviewPanel | undefined;

/**
 * Broadcast state to all panels.
 */
function broadcastState(): void {
    const state = appStateManager.getState();
    sidebarPanel?.postMessage('state', state);
    logViewerPanel?.postMessage('state', state);
}

/**
 * Handle actions from webviews.
 */
async function handleAction(message: any): Promise<void> {
    switch (message.action) {
        // Project/target selection
        case 'selectProject': {
            const projects = getProjects();
            const project = projects.find(p => p.root === message.root);
            if (project) {
                setProjectRoot(project.root);
                const builds = getBuilds().filter(b => b.root === project.root);
                setSelectedTargets(builds);
                syncProjectsToState();
            }
            break;
        }

        case 'toggleTarget': {
            const builds = getBuilds();
            const target = builds.find(b => b.name === message.name);
            if (target) {
                toggleTargetInConfig(target);
                syncProjectsToState();
            }
            break;
        }

        case 'toggleTargetExpanded':
            appStateManager.toggleTargetExpanded(message.name);
            break;

        // Build selection
        case 'selectBuild':
            await appStateManager.selectBuild(message.buildName);
            break;

        case 'toggleStageFilter':
            appStateManager.toggleStageFilter(message.stageId);
            break;

        case 'clearStageFilter':
            appStateManager.clearStageFilter();
            break;

        // Log viewer UI
        case 'toggleLogLevel':
            appStateManager.toggleLogLevel(message.level as LogLevel);
            break;

        case 'setLogSearchQuery':
            appStateManager.setLogSearchQuery(message.query);
            break;

        case 'toggleLogTimestampMode':
            appStateManager.toggleLogTimestampMode();
            break;

        case 'setLogAutoScroll':
            appStateManager.setLogAutoScroll(message.enabled);
            break;

        // Commands
        case 'build':
            await vscode.commands.executeCommand('atopile.build');
            break;

        case 'executeCommand':
            await vscode.commands.executeCommand(message.command);
            break;

        case 'copyLogPath': {
            // Logs are now in a central SQLite database
            // Copy the build_id for the selected build which can be used to query logs
            const state = appStateManager.getState();
            const selectedBuild = state.builds.find(b => b.display_name === state.selectedBuildName);
            if (selectedBuild?.build_id) {
                await vscode.env.clipboard.writeText(selectedBuild.build_id);
                vscode.window.showInformationMessage('Build ID copied to clipboard');
            }
            break;
        }

        case 'focusLogViewer':
            await vscode.commands.executeCommand('atopile.logViewer.focus');
            break;

        case 'showProjectPicker': {
            const projects = getProjects();
            if (projects.length === 0) {
                vscode.window.showInformationMessage('No ato projects found in workspace');
                break;
            }

            const items = projects.map(p => ({
                label: p.name,
                description: p.root,
                project: p,
            }));

            const selected = await vscode.window.showQuickPick(items, {
                placeHolder: 'Select a project',
                title: 'Atopile Projects',
            });

            if (selected) {
                setProjectRoot(selected.project.root);
                const builds = getBuilds().filter(b => b.root === selected.project.root);
                setSelectedTargets(builds);
                syncProjectsToState();
            }
            break;
        }
    }
}

export async function activate(context: vscode.ExtensionContext): Promise<void> {
    // Set extension info
    const version = vscode.extensions.getExtension('atopile.atopile')?.packageJSON?.version || 'dev';

    // Create sidebar panel
    sidebarPanel = new WebviewPanel(context.extensionUri, 'sidebar', 'Atopile');
    sidebarPanel.setOnMessage(handleAction);
    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider('atopile.project', sidebarPanel)
    );

    // Create log viewer panel
    logViewerPanel = new WebviewPanel(context.extensionUri, 'logViewer', 'Atopile Logs');
    logViewerPanel.setOnMessage(handleAction);
    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider('atopile.logViewer', logViewerPanel)
    );

    // Subscribe to state changes - broadcast to all panels
    context.subscriptions.push(
        appStateManager.onStateChange(() => {
            broadcastState();
        })
    );

    // Subscribe to manifest/target changes
    context.subscriptions.push(
        onBuildTargetsChanged(() => {
            syncProjectsToState();
        })
    );

    // Initial sync of projects to state
    syncProjectsToState();

    // Set extension info (logoUri will be set when sidebar resolves)
    // We need to defer this until the sidebar is ready to get the webview URI
    const originalResolve = sidebarPanel.resolveWebviewView.bind(sidebarPanel);
    sidebarPanel.resolveWebviewView = function(webviewView, resolveContext, token) {
        originalResolve(webviewView, resolveContext, token);
        const logoPath = path.join(context.extensionUri.fsPath, 'ato_logo_256x256.png');
        const logoUri = sidebarPanel!.getWebviewUri(logoPath);
        appStateManager.setExtensionInfo(version, logoUri);
    };

    // Reset log viewer to default location on first activation
    const logViewerLocationReset = context.globalState.get<boolean>('logViewerLocationReset_v2', false);
    if (!logViewerLocationReset) {
        try {
            await vscode.commands.executeCommand('atopile.logViewer.resetViewLocation');
            context.globalState.update('logViewerLocationReset_v2', true);
            traceInfo('vscode-panels: reset log viewer to default location');
        } catch (e) {
            traceInfo(`vscode-panels: could not reset log viewer location: ${e}`);
        }
    }

    // Start polling for build updates
    appStateManager.startPolling(500);

    traceInfo('vscode-panels: activated sidebar and log viewer');
}

export function deactivate(): void {
    appStateManager.stopPolling();
    appStateManager.dispose();
}
