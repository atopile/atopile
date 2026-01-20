/**
 * VS Code Panel Providers - Webview setup and action routing.
 *
 * NO STATE HERE. All state lives in appStateManager.
 * Panels receive state via onStateChange and send actions back.
 */

import * as vscode from 'vscode';
import * as path from 'path';
import { traceInfo, traceError } from '../common/log/logging';
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

// --- Atopile Version Management ---

/**
 * Fetch available atopile versions from PyPI.
 */
async function fetchAtopileVersions(): Promise<void> {
    try {
        const https = require('https');
        const data = await new Promise<string>((resolve, reject) => {
            https.get('https://pypi.org/pypi/atopile/json', (res: any) => {
                let data = '';
                res.on('data', (chunk: string) => { data += chunk; });
                res.on('end', () => resolve(data));
            }).on('error', reject);
        });

        const json = JSON.parse(data);
        const versions = Object.keys(json.releases || {})
            .filter(v => !v.includes('dev') && !v.includes('rc') && !v.includes('alpha') && !v.includes('beta'))
            .sort((a, b) => {
                const partsA = a.split('.').map(Number);
                const partsB = b.split('.').map(Number);
                for (let i = 0; i < Math.max(partsA.length, partsB.length); i++) {
                    const numA = partsA[i] || 0;
                    const numB = partsB[i] || 0;
                    if (numA !== numB) return numB - numA;
                }
                return 0;
            })
            .slice(0, 20);

        appStateManager.setAtopileAvailableVersions(versions);
        traceInfo(`Fetched ${versions.length} atopile versions from PyPI`);
    } catch (error) {
        traceError(`Failed to fetch atopile versions: ${error}`);
    }
}

/**
 * Initialize the atopile state from VS Code settings.
 */
function initializeAtopileState(): void {
    const config = vscode.workspace.getConfiguration('atopile');
    const atoPath = config.get<string>('ato');
    const fromSetting = config.get<string>('from', 'atopile');

    // Determine source and version from settings
    if (atoPath) {
        // Using local path
        appStateManager.setAtopileSource('local');
        appStateManager.setAtopileLocalPath(atoPath);
        appStateManager.setAtopileVersion('local');
        traceInfo('Atopile state initialized: source=local');
    } else if (fromSetting && fromSetting.includes('git+')) {
        // Using git branch (e.g., "git+https://github.com/atopile/atopile.git@main")
        appStateManager.setAtopileSource('branch');
        appStateManager.setAtopileLocalPath(null);

        // Extract branch name from the URL (after @)
        const branchMatch = fromSetting.match(/@([^/\s]+)$/);
        const branch = branchMatch ? branchMatch[1] : 'main';
        appStateManager.setAtopieBranch(branch);
        appStateManager.setAtopileVersion(`git@${branch}`);
        traceInfo(`Atopile state initialized: source=branch, branch=${branch}`);
    } else {
        // Using release version via uv
        appStateManager.setAtopileSource('release');
        appStateManager.setAtopileLocalPath(null);
        appStateManager.setAtopieBranch(null);

        // Parse version from "from" setting (e.g., "atopile==0.14.0" or "atopile@0.14.0")
        let version = 'latest';
        if (fromSetting && fromSetting.includes('==')) {
            version = fromSetting.split('==')[1];
        } else if (fromSetting && fromSetting.includes('@')) {
            version = fromSetting.split('@')[1];
        }
        appStateManager.setAtopileVersion(version);
        traceInfo(`Atopile state initialized: source=release, version=${version}`);
    }
}

/**
 * Set the atopile version and trigger installation via uv.
 */
async function setAtopileVersionSetting(version: string): Promise<void> {
    try {
        // Update progress
        appStateManager.setAtopileInstalling(true, { message: 'Updating configuration...', percent: 10 });

        // Update the VS Code setting (atopile.from)
        const config = vscode.workspace.getConfiguration('atopile');
        const fromValue = `atopile==${version}`;

        appStateManager.setAtopileInstalling(true, { message: 'Installing atopile...', percent: 30 });

        // Clear the ato path (use uv-managed version)
        await config.update('ato', undefined, vscode.ConfigurationTarget.Global);
        await config.update('from', fromValue, vscode.ConfigurationTarget.Global);

        appStateManager.setAtopileInstalling(true, { message: 'Verifying installation...', percent: 70 });

        // The extension's findbin.ts will pick up the new setting and use uv to run the specified version
        // We need to trigger a re-check of the atopile binary
        // This is done automatically when the configuration changes

        // Wait a moment for uv to potentially download the version
        await new Promise(resolve => setTimeout(resolve, 2000));

        appStateManager.setAtopileInstalling(true, { message: 'Completing...', percent: 95 });

        // Update state
        appStateManager.setAtopileVersion(version);
        appStateManager.setAtopileInstalling(false);

        traceInfo(`Atopile version set to ${version}`);
        vscode.window.showInformationMessage(`Atopile version set to ${version}`);
    } catch (error) {
        traceError(`Failed to set atopile version: ${error}`);
        appStateManager.setAtopileError(`Failed to set version: ${error}`);
    }
}

/**
 * Fetch available atopile branches from the dashboard API.
 * The dashboard handles caching to avoid GitHub rate limits.
 */
async function fetchAtopieBranches(): Promise<void> {
    const config = vscode.workspace.getConfiguration('atopile');
    const apiUrl = config.get<string>('dashboardApiUrl', 'http://localhost:8501');

    try {
        const axios = require('axios');
        const response = await axios.get(`${apiUrl}/api/atopile/branches`, { timeout: 15000 });

        const branches = response.data.branches || [];
        appStateManager.setAtopileAvailableBranches(branches);

        const cached = response.data.cached ? ' (cached)' : '';
        traceInfo(`Fetched ${branches.length} atopile branches from dashboard${cached}`);
    } catch (error) {
        traceError(`Failed to fetch atopile branches from dashboard: ${error}`);
        // Fall back to common branches
        appStateManager.setAtopileAvailableBranches(['main', 'develop']);
    }
}

/**
 * Set the atopile branch and trigger installation via uv from git.
 */
async function setAtopieBranchSetting(branch: string): Promise<void> {
    try {
        // Update progress
        appStateManager.setAtopileInstalling(true, { message: `Cloning branch ${branch}...`, percent: 10 });

        // Update the VS Code setting (atopile.from)
        const config = vscode.workspace.getConfiguration('atopile');
        const fromValue = `git+https://github.com/atopile/atopile.git@${branch}`;

        appStateManager.setAtopileInstalling(true, { message: 'Installing from git...', percent: 30 });

        // Clear the ato path (use uv-managed version)
        await config.update('ato', undefined, vscode.ConfigurationTarget.Global);
        await config.update('from', fromValue, vscode.ConfigurationTarget.Global);

        appStateManager.setAtopileInstalling(true, { message: 'Building dependencies...', percent: 60 });

        // Wait for uv to download and build the branch
        await new Promise(resolve => setTimeout(resolve, 3000));

        appStateManager.setAtopileInstalling(true, { message: 'Completing...', percent: 95 });

        // Update state
        appStateManager.setAtopieBranch(branch);
        appStateManager.setAtopileVersion(`git@${branch}`);
        appStateManager.setAtopileInstalling(false);

        traceInfo(`Atopile branch set to ${branch}`);
        vscode.window.showInformationMessage(`Atopile branch set to ${branch}`);
    } catch (error) {
        traceError(`Failed to set atopile branch: ${error}`);
        appStateManager.setAtopileError(`Failed to set branch: ${error}`);
    }
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
                // Fetch BOM for the newly selected project
                await appStateManager.fetchBOM(project.root, 'default');
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

        // Log viewer UI
        case 'toggleLogLevel':
            await appStateManager.toggleLogLevel(message.level as LogLevel);
            break;

        case 'toggleStage':
            await appStateManager.toggleStage(message.stage);
            break;

        case 'selectAllStages':
            await appStateManager.selectAllStages();
            break;

        case 'clearAllStages':
            await appStateManager.clearAllStages();
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
        case 'build': {
            // Start build via API so the server tracks the build state
            const state = appStateManager.getState();
            const projectRoot = state.selectedProjectRoot;
            const targetNames = state.selectedTargetNames;

            if (projectRoot) {
                try {
                    const apiUrl = vscode.workspace.getConfiguration('atopile').get<string>('dashboardApiUrl', 'http://localhost:8501');
                    const axios = require('axios');
                    await axios.post(`${apiUrl}/api/build`, {
                        project_root: projectRoot,
                        targets: targetNames,
                        frozen: false,
                    }, { timeout: 5000 });
                    traceInfo(`Build started via API for ${projectRoot}`);
                } catch (error) {
                    // Fallback to terminal command if API is not available
                    traceInfo('API not available, falling back to terminal command');
                    await vscode.commands.executeCommand('atopile.build');
                }
            } else {
                // No project selected, use terminal command
                await vscode.commands.executeCommand('atopile.build');
            }
            break;
        }

        case 'buildTarget': {
            // Build a single target by name
            const builds = getBuilds();
            const target = builds.find(b => b.name === message.name);
            if (target) {
                await vscode.commands.executeCommand('atopile.build', [target]);
            }
            break;
        }

        case 'openPcbForTarget': {
            // Open PCB for a specific target by name
            const builds = getBuilds();
            const target = builds.find(b => b.name === message.name);
            if (target) {
                await vscode.commands.executeCommand('atopile.launch_kicad', target);
            }
            break;
        }

        case 'executeCommand':
            if (message.args) {
                await vscode.commands.executeCommand(message.command, message.args);
            } else {
                await vscode.commands.executeCommand(message.command);
            }
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

        // Standard Library
        case 'refreshStdlib':
            await appStateManager.fetchStdlib(true);
            break;

        // Package Management
        case 'refreshPackages':
            await appStateManager.fetchPackages(true);
            break;

        case 'installPackage': {
            const { packageId, projectRoot, version } = message;
            try {
                const apiUrl = vscode.workspace.getConfiguration('atopile').get<string>('dashboardApiUrl', 'http://localhost:8501');
                const axios = require('axios');
                await axios.post(`${apiUrl}/api/packages/install`, {
                    package_identifier: packageId,
                    project_root: projectRoot,
                    version: version || null,
                }, { timeout: 120000 });  // 2 minute timeout for package install
                traceInfo(`Package install started: ${packageId} -> ${projectRoot}`);
                // Refresh packages after install
                await appStateManager.fetchPackages(true);
            } catch (error) {
                traceError(`Package install failed: ${error}`);
                vscode.window.showErrorMessage(`Failed to install package ${packageId}`);
            }
            break;
        }

        case 'removePackage': {
            const { packageId, projectRoot } = message;
            try {
                const apiUrl = vscode.workspace.getConfiguration('atopile').get<string>('dashboardApiUrl', 'http://localhost:8501');
                const axios = require('axios');
                await axios.post(`${apiUrl}/api/packages/remove`, {
                    package_identifier: packageId,
                    project_root: projectRoot,
                }, { timeout: 60000 });
                traceInfo(`Package remove started: ${packageId} from ${projectRoot}`);
                // Refresh packages after remove
                await appStateManager.fetchPackages(true);
            } catch (error) {
                traceError(`Package remove failed: ${error}`);
                vscode.window.showErrorMessage(`Failed to remove package ${packageId}`);
            }
            break;
        }

        // BOM (Bill of Materials)
        case 'refreshBOM': {
            const { projectRoot, target } = message;
            await appStateManager.fetchBOM(projectRoot, target || 'default');
            break;
        }

        case 'clearBOM':
            appStateManager.clearBOM();
            break;

        // Package Details
        case 'getPackageDetails': {
            const { packageId } = message;
            await appStateManager.fetchPackageDetails(packageId);
            break;
        }

        case 'clearPackageDetails':
            appStateManager.clearPackageDetails();
            break;

        // Build Package (install if needed, then build)
        case 'buildPackage': {
            const { packageId, projectRoot, entry } = message;
            try {
                // First install the package if not already installed
                const apiUrl = vscode.workspace.getConfiguration('atopile').get<string>('dashboardApiUrl', 'http://localhost:8501');
                const axios = require('axios');

                // Check if already installed
                const state = appStateManager.getState();
                const pkg = state.packages.find((p: any) => p.identifier === packageId);
                const isInstalled = pkg?.installed && pkg.installed_in.some(
                    (path: string) => path === projectRoot || path.endsWith(`/${projectRoot}`) || projectRoot.endsWith(path)
                );

                if (!isInstalled) {
                    traceInfo(`Package ${packageId} not installed, installing first...`);
                    await axios.post(`${apiUrl}/api/packages/install`, {
                        package_identifier: packageId,
                        project_root: projectRoot,
                        version: null,
                    }, { timeout: 120000 });
                    // Refresh packages after install
                    await appStateManager.fetchPackages(true);
                }

                // Now trigger the build
                const parts = packageId.split('/');
                const pkgName = parts[parts.length - 1];
                const defaultEntry = entry || `${pkgName}.ato:${pkgName.replace(/-/g, '_')}`;

                traceInfo(`Building package with entry: ${defaultEntry}`);
                await axios.post(`${apiUrl}/api/build`, {
                    project_root: projectRoot,
                    targets: ['default'],
                    frozen: false,
                }, { timeout: 5000 });
                traceInfo(`Build started for package ${packageId}`);
            } catch (error) {
                traceError(`Build package failed: ${error}`);
                vscode.window.showErrorMessage(`Failed to build package ${packageId}`);
            }
            break;
        }

        // Problems
        case 'refreshProblems':
            await appStateManager.fetchProblems();
            break;

        case 'toggleProblemLevelFilter':
            appStateManager.toggleProblemLevelFilter(message.level);
            break;

        case 'clearProblemFilter':
            appStateManager.clearProblemFilter();
            break;

        // Project Modules (for entry point picker)
        case 'fetchModules': {
            const { projectRoot, forceRefresh } = message;
            if (projectRoot) {
                await appStateManager.fetchModules(projectRoot, forceRefresh || false);
            }
            break;
        }

        // Project Files (for file explorer)
        case 'fetchFiles': {
            const { projectRoot, forceRefresh } = message;
            if (projectRoot) {
                await appStateManager.fetchFiles(projectRoot, forceRefresh || false);
            }
            break;
        }

        // Variables (for VariablesPanel)
        case 'fetchVariables': {
            const { projectRoot, target } = message;
            if (projectRoot) {
                await appStateManager.fetchVariables(projectRoot, target || 'default');
            }
            break;
        }

        case 'openFile': {
            let { file, line, column } = message;

            // If the file looks like an atopile address (contains ::), resolve it first
            if (file && file.includes('::')) {
                try {
                    const apiUrl = vscode.workspace.getConfiguration('atopile').get<string>('dashboardApiUrl', 'http://localhost:8501');
                    const axios = require('axios');
                    const state = appStateManager.getState();
                    const projectRoot = state.selectedProjectRoot;

                    const params = new URLSearchParams({ address: file });
                    if (projectRoot) {
                        params.append('project_root', projectRoot);
                    }

                    const response = await axios.get(`${apiUrl}/api/resolve-location?${params}`, { timeout: 5000 });
                    if (response.data) {
                        file = response.data.file;
                        line = response.data.line || line;
                        column = response.data.column || column;
                        traceInfo(`Resolved address to: ${file}:${line}`);
                    }
                } catch (error) {
                    traceError(`Failed to resolve address: ${error}`);
                    // Continue with original file path as fallback
                }
            }

            try {
                const uri = vscode.Uri.file(file);
                const position = new vscode.Position((line || 1) - 1, (column || 1) - 1);
                const doc = await vscode.workspace.openTextDocument(uri);
                const editor = await vscode.window.showTextDocument(doc);
                editor.selection = new vscode.Selection(position, position);
                editor.revealRange(new vscode.Range(position, position));
            } catch (error) {
                traceError(`Failed to open file: ${error}`);
            }
            break;
        }

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

        // Atopile version management
        case 'setAtopileVersion': {
            const { version } = message;
            await setAtopileVersionSetting(version);
            break;
        }

        case 'setAtopileSource': {
            const { source } = message;
            appStateManager.setAtopileSource(source);
            const state = appStateManager.getState();

            // If switching to release, trigger version install
            if (source === 'release') {
                if (state.atopile.currentVersion && state.atopile.currentVersion !== 'local' && !state.atopile.currentVersion.startsWith('git@')) {
                    await setAtopileVersionSetting(state.atopile.currentVersion);
                } else if (state.atopile.availableVersions.length > 0) {
                    // Install latest version
                    await setAtopileVersionSetting(state.atopile.availableVersions[0]);
                }
            }
            // If switching to branch, trigger branch install
            else if (source === 'branch') {
                if (state.atopile.branch) {
                    await setAtopieBranchSetting(state.atopile.branch);
                } else if (state.atopile.availableBranches.length > 0) {
                    // Install main branch
                    await setAtopieBranchSetting(state.atopile.availableBranches[0]);
                }
            }
            break;
        }

        case 'setAtopileLocalPath': {
            const { path } = message;
            appStateManager.setAtopileLocalPath(path);
            // Update the VS Code setting
            const config = vscode.workspace.getConfiguration('atopile');
            await config.update('ato', path, vscode.ConfigurationTarget.Global);
            break;
        }

        case 'browseAtopilePath': {
            const result = await vscode.window.showOpenDialog({
                canSelectFolders: true,
                canSelectFiles: false,
                canSelectMany: false,
                title: 'Select Atopile Source Directory',
            });
            if (result && result[0]) {
                const localPath = result[0].fsPath;
                appStateManager.setAtopileLocalPath(localPath);
                // Update the VS Code setting
                const config = vscode.workspace.getConfiguration('atopile');
                await config.update('ato', localPath, vscode.ConfigurationTarget.Global);
            }
            break;
        }

        case 'refreshAtopileVersions':
            await fetchAtopileVersions();
            break;

        case 'setAtopieBranch': {
            const { branch } = message;
            await setAtopieBranchSetting(branch);
            break;
        }

        case 'refreshAtopieBranches':
            await fetchAtopieBranches();
            break;

        // Max Concurrent Builds Setting
        case 'getMaxConcurrentSetting': {
            try {
                const apiUrl = vscode.workspace.getConfiguration('atopile').get<string>('dashboardApiUrl', 'http://localhost:8501');
                const axios = require('axios');
                const response = await axios.get(`${apiUrl}/api/settings/max-concurrent`, { timeout: 5000 });
                // Send the setting back to the webview
                sidebarPanel?.postMessage('maxConcurrentSetting', response.data);
            } catch (error) {
                traceError(`Failed to get max concurrent setting: ${error}`);
            }
            break;
        }

        case 'setMaxConcurrentSetting': {
            const { useDefault, customValue } = message;
            try {
                const apiUrl = vscode.workspace.getConfiguration('atopile').get<string>('dashboardApiUrl', 'http://localhost:8501');
                const axios = require('axios');
                const response = await axios.post(`${apiUrl}/api/settings/max-concurrent`, {
                    use_default: useDefault,
                    custom_value: customValue,
                }, { timeout: 5000 });
                // Send the updated setting back to the webview
                sidebarPanel?.postMessage('maxConcurrentSetting', response.data);
                traceInfo(`Max concurrent builds set to ${response.data.current_value}`);
            } catch (error) {
                traceError(`Failed to set max concurrent setting: ${error}`);
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

    // Initialize atopile version state
    initializeAtopileState();

    // Fetch available versions from PyPI and branches from GitHub (in background)
    fetchAtopileVersions();
    fetchAtopieBranches();

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

    // Fetch stdlib, packages, and problems (non-blocking)
    // These load in the background since they can be slow
    appStateManager.fetchStdlib().catch(e => traceError(`Failed to fetch stdlib: ${e}`));
    appStateManager.fetchPackages().catch(e => traceError(`Failed to fetch packages: ${e}`));
    appStateManager.fetchProblems().catch(e => traceError(`Failed to fetch problems: ${e}`));

    // Fetch BOM for initially selected project
    const initialRoot = getProjectRoot();
    if (initialRoot) {
        appStateManager.fetchBOM(initialRoot, 'default').catch(e => traceError(`Failed to fetch BOM: ${e}`));
    }

    traceInfo('vscode-panels: activated sidebar and log viewer');
}

export function deactivate(): void {
    appStateManager.stopPolling();
    appStateManager.dispose();
}
