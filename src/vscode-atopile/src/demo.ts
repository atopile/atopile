import * as path from 'path';
import * as vscode from 'vscode';
import { traceInfo } from './common/log/logging';
import { backendServer } from './common/backendServer';
import { getResourcesPath, loadResource } from './common/resources';
import { getBuildTarget, getProjectRoot, onProjectRootChanged, onBuildTargetChanged } from './common/target';
import { Build, getBuilds } from './common/manifest';
import { isWebIdeUi } from './common/environment';

const QUICKSTART_URL = 'https://docs.atopile.io/atopile-0.14.x/quickstart/1-installation';

function openWelcomeTab(): vscode.WebviewPanel {
    const resourcesUri = vscode.Uri.file(getResourcesPath());
    const panel = vscode.window.createWebviewPanel(
        'atopile.welcome',
        'Welcome to atopile',
        vscode.ViewColumn.One,
        { enableScripts: false, retainContextWhenHidden: true, localResourceRoots: [resourcesUri] },
    );

    const iconPath = vscode.Uri.file(path.join(getResourcesPath(), 'atopile-icon.svg'));
    panel.iconPath = { light: iconPath, dark: iconPath };

    const logoUri = panel.webview.asWebviewUri(
        vscode.Uri.file(path.join(getResourcesPath(), 'atopile-icon.svg')),
    );
    let html = loadResource('welcome.html');
    html = html.replace(/\{\{logoUri\}\}/g, logoUri.toString());
    html = html.replace(/\{\{quickstartUrl\}\}/g, QUICKSTART_URL);
    panel.webview.html = html;

    return panel;
}

function entryFileForTarget(target: Build): string {
    const filePart = target.entry.split(':')[0];
    return path.join(target.root, filePart);
}

/**
 * Resolve the build target for demo mode.
 * Needs getProjectRoot() to be set so we can filter builds.
 */
function resolveBuildTarget(): Build | undefined {
    const selected = getBuildTarget();
    if (selected) {
        return selected;
    }

    const builds = getBuilds();
    const projectRoot = getProjectRoot();
    if (projectRoot) {
        return builds.find(b => b.root === projectRoot);
    }

    // Single-project workspace: safe to pick the first
    const roots = new Set(builds.map(b => b.root));
    if (roots.size === 1) {
        return builds[0];
    }

    return undefined;
}

/**
 * Wait for the project root to be set (sidebar sends selectionChanged).
 * Returns immediately if already set.
 */
function waitForProjectRoot(timeoutMs = 30000): Promise<string | undefined> {
    const current = getProjectRoot();
    if (current) {
        return Promise.resolve(current);
    }
    return new Promise<string | undefined>((resolve) => {
        const timer = setTimeout(() => {
            d.dispose();
            traceInfo('[demo] Timed out waiting for project root');
            resolve(undefined);
        }, timeoutMs);
        const d = onProjectRootChanged((root) => {
            clearTimeout(timer);
            d.dispose();
            traceInfo(`[demo] Project root received: ${root}`);
            resolve(root);
        });
    });
}

/**
 * Wait for the build target to be set (sidebar sends selectionChanged → setSelectedTargets).
 * Returns immediately if already set.
 */
function waitForBuildTarget(timeoutMs = 30000): Promise<Build | undefined> {
    const current = getBuildTarget();
    if (current) {
        return Promise.resolve(current);
    }
    return new Promise<Build | undefined>((resolve) => {
        const timer = setTimeout(() => {
            d.dispose();
            traceInfo('[demo] Timed out waiting for build target');
            resolve(undefined);
        }, timeoutMs);
        const d = onBuildTargetChanged((target) => {
            clearTimeout(timer);
            d.dispose();
            traceInfo(`[demo] Build target received: ${target?.entry ?? 'undefined'}`);
            resolve(target);
        });
    });
}

/**
 * Wait for the backend to be connected. Returns immediately if already connected.
 */
function waitForBackend(timeoutMs = 30000): Promise<boolean> {
    if (backendServer.isConnected) {
        return Promise.resolve(true);
    }
    return new Promise<boolean>((resolve) => {
        const timer = setTimeout(() => {
            d.dispose();
            traceInfo('[demo] Timed out waiting for backend connection');
            resolve(false);
        }, timeoutMs);
        const d = backendServer.onStatusChange((connected) => {
            if (connected) {
                clearTimeout(timer);
                d.dispose();
                resolve(true);
            }
        });
    });
}

/**
 * Runs the demo-mode sequence: show welcome page, open the entry .ato file,
 * and open the layout viewer beside the welcome tab.
 */
async function runDemoMode(): Promise<void> {
    traceInfo('[demo] runDemoMode starting');

    // Auto-focus the atopile sidebar
    vscode.commands.executeCommand('workbench.view.extension.atopile-explorer');

    // Close any open editors (e.g. the "Setup VS Code Web" walkthrough tab)
    await vscode.commands.executeCommand('workbench.action.closeAllEditors');

    // Close chat sidebar — may not exist in all VS Code flavours, so fail silently
    try {
        await vscode.commands.executeCommand('workbench.action.closeAuxiliaryBar');
    } catch {
        // Not available (e.g. local VS Code without auxiliary bar)
    }

    // Show welcome tab immediately
    openWelcomeTab();
    traceInfo('[demo] Welcome tab opened');

    // Wait for project root and build target (sidebar restores persisted selection asynchronously)
    traceInfo(`[demo] getProjectRoot(): ${getProjectRoot() ?? 'undefined'}, getBuildTarget(): ${getBuildTarget()?.entry ?? 'undefined'}, getBuilds().length: ${getBuilds().length}`);
    const projectRoot = await waitForProjectRoot();
    traceInfo(`[demo] After waitForProjectRoot — getProjectRoot(): ${getProjectRoot() ?? 'undefined'}, getBuildTarget(): ${getBuildTarget()?.entry ?? 'undefined'}`);

    // Wait for build target (setSelectedTargets fires shortly after setProjectRoot in handleSelectionChanged)
    await waitForBuildTarget();
    traceInfo(`[demo] After waitForBuildTarget — getBuildTarget(): ${getBuildTarget()?.entry ?? 'undefined'}`);

    // Resolve and open entry file below welcome tab (vertical split)
    const target = resolveBuildTarget();
    traceInfo(`[demo] resolveBuildTarget(): ${target ? `${target.entry} (root: ${target.root})` : 'undefined'}`);
    if (target) {
        const entryPath = entryFileForTarget(target);
        traceInfo(`[demo] Opening entry file: ${entryPath}`);
        try {
            // Set a two-row layout: welcome on top, entry file on bottom
            await vscode.commands.executeCommand('vscode.setEditorLayout', {
                orientation: 1, // vertical (top/bottom)
                groups: [{ size: 0.5 }, { size: 0.5 }],
            });
            await vscode.window.showTextDocument(vscode.Uri.file(entryPath), {
                preview: false,
                viewColumn: vscode.ViewColumn.Two,
                preserveFocus: true,
            });
            traceInfo('[demo] Entry file opened');
        } catch (e) {
            traceInfo(`[demo] Failed to open entry file: ${e}`);
        }
    } else {
        traceInfo('[demo] No build target resolved, skipping entry file');
    }

    // Open layout viewer beside
    traceInfo(`[demo] backendServer.isConnected=${backendServer.isConnected}`);
    const connected = await waitForBackend();
    if (!connected) {
        traceInfo('[demo] Backend not connected, skipping layout');
        return;
    }

    const layoutRoot = projectRoot ?? vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
    traceInfo(`[demo] openLayout: root=${layoutRoot ?? 'undefined'}`);
    if (!layoutRoot) {
        traceInfo('[demo] No root for layout, skipping');
        return;
    }

    traceInfo('[demo] Calling backendServer.loadLayout...');
    const ready = await backendServer.loadLayout(layoutRoot);
    traceInfo(`[demo] loadLayout returned ${ready}`);
    if (ready) {
        traceInfo('[demo] Executing atopile.kicanvas_preview');
        await vscode.commands.executeCommand('atopile.kicanvas_preview');
    } else {
        traceInfo('[demo] Layout model not ready, skipping');
    }

    traceInfo('[demo] runDemoMode done');
}

export function activate(context: vscode.ExtensionContext): void {
    context.subscriptions.push(
        vscode.commands.registerCommand('atopile.demo-mode', () => runDemoMode()),
    );

    // Web-ide sessions should always open in demo mode on activation.
    if (isWebIdeUi()) {
        vscode.commands.executeCommand('atopile.demo-mode');
    }
}
