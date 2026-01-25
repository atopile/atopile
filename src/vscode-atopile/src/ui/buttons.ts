/**
 * Command handlers for atopile actions.
 *
 * Registers VS Code commands that can be triggered from the sidebar
 * or command palette. No status bar items are created.
 */

import * as vscode from 'vscode';
import { window } from 'vscode';
import { Build, getBuilds, loadBuilds } from '../common/manifest';
import { getAtoBin, onDidChangeAtoBinInfo, runAtoCommandInTerminal } from '../common/findbin';
import { traceError, traceInfo } from '../common/log/logging';
import { openPcb } from '../common/kicad';
import { glob } from 'glob';
import * as path from 'path';
import { openPackageExplorer } from './packagexplorer';
import { captureEvent } from '../common/telemetry';
import * as kicanvas from './kicanvas';
import * as modelviewer from './modelviewer';
import {
    getBuildTarget,
    getSelectedTargets,
    setSelectedTargets,
    isTargetSelected,
    toggleTarget,
    getProjectRoot,
    setProjectRoot,
} from '../common/target';
import { disambiguatePaths } from '../common/utilities';
import { backendServer } from '../common/backendServer';

/**
 * Button metadata for the sidebar UI.
 */
export interface ButtonInfo {
    id: string;
    icon: string;
    label: string;
    tooltip: string;
    command: { getCommandName: () => string };
    description: string;
}

const commands: Array<{ handler: () => Promise<void>; name: string }> = [];
const buttonInfos: ButtonInfo[] = [];

function registerCommand(name: string, handler: () => Promise<void>) {
    commands.push({ name, handler });
    return { getCommandName: () => name };
}

function registerButton(icon: string, command: ReturnType<typeof registerCommand>, tooltip: string, label: string) {
    buttonInfos.push({
        id: command.getCommandName(),
        icon,
        label,
        tooltip,
        command,
        description: label,
    });
}

// Register commands
const cmdShell = registerCommand('atopile.shell', atoShell);
const cmdCreateProject = registerCommand('atopile.create_project', atoCreateProject);
const cmdAddPart = registerCommand('atopile.add_part', atoAddPart);
const cmdAddPackage = registerCommand('atopile.add_package', atoAddPackage);
const cmdRemovePackage = registerCommand('atopile.remove_package', atoRemovePackage);
const cmdBuild = registerCommand('atopile.build', atoBuild);
const cmdPackageExplorer = registerCommand('atopile.package_explorer', atoPackageExplorer);
const cmdChooseBuild = registerCommand('atopile.choose_build', atoChooseBuild);
const cmdChooseProject = registerCommand('atopile.choose_project', atoChooseProject);
const cmdLaunchKicad = registerCommand('atopile.launch_kicad', atoLaunchKicad);
const cmdKicanvasPreview = registerCommand('atopile.kicanvas_preview', atoKicanvasPreview);
const cmdModelViewerPreview = registerCommand('atopile.model_viewer_preview', atoModelViewerPreview);
const cmdExport = registerCommand('atopile.export', atoExport);
const cmdServe = registerCommand('atopile.serve', atoServe);

// Register buttons for sidebar display
registerButton('server-process', cmdServe, 'Start/show ato server', 'ato serve');
registerButton('terminal', cmdShell, 'Open ato shell', 'Open ato shell');
registerButton('new-file', cmdCreateProject, 'Create new project', 'Create new project');
registerButton('file-binary', cmdAddPart, 'Add part to project', 'Add part to project');
registerButton('package', cmdAddPackage, 'Add package dependency', 'Add package dependency');
registerButton('trash', cmdRemovePackage, 'Remove package dependency', 'Remove package dependency');
registerButton('play', cmdBuild, 'Build project', 'Build project');
registerButton('file-zip', cmdExport, 'Generate manufacturing data', 'Generate manufacturing data');
registerButton('circuit-board', cmdLaunchKicad, 'Open board in KiCad', 'Open board in KiCad');
registerButton('symbol-misc', cmdPackageExplorer, 'Open Package Explorer', 'Open Package Explorer');
registerButton('eye', cmdKicanvasPreview, 'Open Layout Preview', 'Open Layout Preview');
registerButton('symbol-constructor', cmdModelViewerPreview, 'Open 3D Model Preview', 'Open 3D Model Preview');
registerButton('checklist', cmdChooseBuild, 'Select build targets', 'Select build targets');
registerButton('folder', cmdChooseProject, 'Select project folder', 'Select project folder');

/**
 * Get button metadata for the sidebar.
 */
export function getButtons(): ButtonInfo[] {
    return buttonInfos;
}

function _getSelectedBuilds(): Build[] {
    const builds = getSelectedTargets();
    if (builds.length === 0) {
        throw new Error('No build targets selected');
    }
    return builds;
}

function _getBuildTarget(): Build {
    const build = getBuildTarget();
    if (!build) {
        throw new Error('No build target selected');
    }
    return build;
}

// Get unique project roots from all builds
function _getProjectRoots(): string[] {
    const builds = getBuilds();
    const roots = new Set<string>();
    for (const build of builds) {
        if (build.root) {
            roots.add(build.root);
        }
    }
    return Array.from(roots);
}

async function _autoSelectDefaultProject() {
    const builds = getBuilds();
    const selected = getSelectedTargets();

    // Auto-select first project and all its builds if nothing selected
    if (builds.length > 0 && selected.length === 0) {
        const roots = _getProjectRoots();
        if (roots.length > 0) {
            const firstRoot = roots[0];
            setProjectRoot(firstRoot);
            const projectBuilds = builds.filter(b => b.root === firstRoot);
            setSelectedTargets(projectBuilds);
        }
    }
    if (builds.length === 0) {
        setSelectedTargets([]);
        setProjectRoot(undefined);
    }
}

async function _reloadBuilds() {
    await loadBuilds();
    await _autoSelectDefaultProject();
    return getBuilds();
}

export async function forceReloadButtons() {
    await _reloadBuilds();
}

export async function activate(context: vscode.ExtensionContext) {
    // Register command handlers
    for (const cmd of commands) {
        context.subscriptions.push(
            vscode.commands.registerCommand(cmd.name, cmd.handler)
        );
    }

    await _reloadBuilds();

    context.subscriptions.push(
        onDidChangeAtoBinInfo(async () => {
            await _reloadBuilds();
        }),
        vscode.workspace.onDidSaveTextDocument(async (document) => {
            if (document.uri.fsPath.endsWith('ato.yaml')) {
                await _reloadBuilds();
            }
        }),
        vscode.workspace.onDidCreateFiles(async (event) => {
            if (event.files.some((file) => file.fsPath.endsWith('ato.yaml'))) {
                await _reloadBuilds();
            }
        }),
        vscode.workspace.onDidDeleteFiles(async (event) => {
            if (event.files.some((file) => file.fsPath.endsWith('ato.yaml'))) {
                await _reloadBuilds();
            }
        }),
    );
}

export function deactivate() {
    // Nothing to clean up - no status bar items
}

// Command handlers ----------------------------------------------------------------

async function _runInTerminal(name: string, cwd: string | undefined, subcommand: string[], hideFromUser: boolean) {
    try {
        return await runAtoCommandInTerminal(name, cwd, subcommand, hideFromUser);
    } catch (error) {
        traceError(`Buttons: Error running ato in terminal: ${error}`);
        return;
    }
}

async function _runInTerminalWithProjectRoot(name: string, subcommand: string[], hideFromUser: boolean) {
    const root = getProjectRoot();
    if (!root) {
        throw new Error('No project folder selected');
    }
    await _runInTerminal(name, root, subcommand, hideFromUser);
}

async function atoShell() {
    await _runInTerminal('shell', undefined, ['--help'], false);
}

async function atoBuild(buildsArg?: Build[]) {
    // Use passed builds or fall back to selected builds
    const builds = buildsArg && buildsArg.length > 0 ? buildsArg : _getSelectedBuilds();
    const root = builds[0]?.root || getProjectRoot();

    if (!root) {
        vscode.window.showErrorMessage('No project folder selected');
        return;
    }

    vscode.commands.executeCommand('atopile.logViewer.focus');

    const targetNames = builds.map(b => b.name);

    // Use the backend server API
    if (backendServer.isConnected) {
        try {
            traceInfo(`Building via API: ${targetNames.join(', ')} in ${root}`);
            await backendServer.build(root, targetNames);
            captureEvent('vsce:build_start', { targets: targetNames });
            return;
        } catch (error) {
            vscode.window.showErrorMessage(`Build failed: ${error}`);
            traceError(`Build failed: ${error}`);
            return;
        }
    }

    // Server not connected - show error
    vscode.window.showErrorMessage('Backend server not connected. Run "ato serve" to start it.');
}

async function atoExport() {
    const builds = _getSelectedBuilds();
    const root = getProjectRoot();

    if (!root) {
        vscode.window.showErrorMessage('No project folder selected');
        return;
    }

    const buildArgs = ['build', '-t', 'all'];
    for (const build of builds) {
        buildArgs.push('--build', build.name);
    }

    const targetNames = builds.map(b => b.name).join(', ');
    await _runInTerminal(`export ${targetNames}`, root, buildArgs, false);

    captureEvent('vsce:build_start', { targets: builds.map(b => b.name) });
}

async function atoAddPart() {
    let result = await window.showInputBox({
        placeHolder: 'Manufacturer:PartNumber or LCSC_ID',
    });
    result = result?.trim();
    if (!result) {
        return;
    }

    await _runInTerminalWithProjectRoot(
        'create part',
        ['create', 'part', '--search', result, '--accept-single'],
        false,
    );

    captureEvent('vsce:part_create', { part: result });
}

async function atoAddPackage() {
    let result = await window.showInputBox({
        placeHolder: 'Package name',
    });
    result = result?.trim();

    if (!result) {
        return;
    }

    await _runInTerminalWithProjectRoot('add', ['add', result], false);

    captureEvent('vsce:package_add', { package: result });
}

async function atoRemovePackage() {
    let result = await window.showInputBox({
        placeHolder: 'Package name',
    });
    result = result?.trim();

    if (!result) {
        return;
    }

    await _runInTerminalWithProjectRoot('remove', ['remove', result], false);

    captureEvent('vsce:package_remove', { package: result });
}

async function atoCreateProject() {
    await _runInTerminal('create project', undefined, ['create', 'project'], false);

    captureEvent('vsce:project_create');
}

async function atoChooseProject() {
    await _reloadBuilds();

    const roots = _getProjectRoots();

    if (roots.length === 0) {
        vscode.window.showInformationMessage('No projects found. Create a project first.');
        return;
    }

    const currentRoot = getProjectRoot();
    const items = roots.map(root => ({
        label: `${root === currentRoot ? '$(check) ' : ''}${path.basename(root)}`,
        description: root,
        root: root,
    }));

    const result = await window.showQuickPick(items, {
        placeHolder: 'Choose project folder',
    });

    if (!result) {
        return;
    }

    setProjectRoot(result.root);

    const builds = getBuilds().filter(b => b.root === result.root);
    setSelectedTargets(builds);

    captureEvent('vsce:project_select', { project: result.root });
}

async function atoChooseBuild() {
    await _reloadBuilds();

    const currentRoot = getProjectRoot();
    if (!currentRoot) {
        vscode.window.showInformationMessage('Select a project folder first.');
        return;
    }

    const projectBuilds = getBuilds().filter(b => b.root === currentRoot);

    if (projectBuilds.length === 0) {
        vscode.window.showInformationMessage('No build targets found in this project.');
        return;
    }

    interface BuildQuickPickItem extends vscode.QuickPickItem {
        build: Build;
    }

    const quickPick = window.createQuickPick<BuildQuickPickItem>();
    quickPick.items = projectBuilds.map(build => ({
        label: `${isTargetSelected(build) ? '$(check)' : '$(circle-outline)'} ${build.name}`,
        description: build.entry,
        build: build,
        picked: isTargetSelected(build),
    }));
    quickPick.title = 'Select Build Targets';
    quickPick.placeholder = 'Click to toggle selection (click outside to close)';
    quickPick.canSelectMany = false;

    quickPick.buttons = [
        { iconPath: new vscode.ThemeIcon('check-all'), tooltip: 'Select All' },
        { iconPath: new vscode.ThemeIcon('circle-outline'), tooltip: 'Select None' },
    ];

    quickPick.onDidTriggerButton(button => {
        if (button.tooltip === 'Select All') {
            setSelectedTargets(projectBuilds);
        } else if (button.tooltip === 'Select None') {
            setSelectedTargets([]);
        }
        quickPick.items = projectBuilds.map(build => ({
            label: `${isTargetSelected(build) ? '$(check)' : '$(circle-outline)'} ${build.name}`,
            description: build.entry,
            build: build,
            picked: isTargetSelected(build),
        }));
    });

    quickPick.onDidAccept(() => {
        const selected = quickPick.selectedItems[0];
        if (selected) {
            toggleTarget(selected.build);
            quickPick.items = projectBuilds.map(build => ({
                label: `${isTargetSelected(build) ? '$(check)' : '$(circle-outline)'} ${build.name}`,
                description: build.entry,
                build: build,
                picked: isTargetSelected(build),
            }));
        }
    });

    quickPick.onDidHide(() => {
        quickPick.dispose();
        captureEvent('vsce:build_targets_select', {
            targets: getSelectedTargets().map(b => b.name),
        });
    });

    quickPick.show();
}

async function atoLaunchKicad(buildArg?: Build) {
    // Use passed build or fall back to selected build target
    const build = buildArg || _getBuildTarget();

    const pcb_name = build.name + '.kicad_pcb';
    const search_path = `**/${build.name}/${pcb_name}`;
    let paths: string[] = build.root
        ? (await glob(search_path, { cwd: build.root })).map((p) => path.join(build.root as string, p))
        : (await vscode.workspace.findFiles(search_path)).map((uri) => uri.fsPath);

    if (paths.length === 0) {
        traceError(`No pcb file found: ${pcb_name}`);
        vscode.window.showErrorMessage(`No pcb file found: ${pcb_name}. Did you build the project?`);
        captureEvent('vsce:pcbnew_fail', { error: 'no_pcb_file' });
        return;
    }
    if (paths.length > 1) {
        vscode.window.showErrorMessage(`Bug: multiple pcb files found: ${paths.join(', ')}`);
        captureEvent('vsce:pcbnew_fail', { error: 'multiple_pcb_files' });
        return;
    }
    const pcb_path = paths[0];

    try {
        await openPcb(pcb_path);
        captureEvent('vsce:pcbnew_success');
    } catch (error) {
        traceError(`Error launching KiCad: ${error}`);
        vscode.window.showErrorMessage(`Error launching KiCad: ${error}`);
        captureEvent('vsce:pcbnew_fail', { error: 'unknown' });
    }
}

async function atoPackageExplorer() {
    try {
        await openPackageExplorer();
    } catch (error) {
        traceError(`Error opening Package Explorer: ${error}`);
        vscode.window.showErrorMessage(`Error opening Package Explorer: ${error}`);
    }
}

async function atoKicanvasPreview() {
    await kicanvas.openKiCanvasPreview();
}

async function atoModelViewerPreview() {
    await modelviewer.openModelViewerPreview();
}

async function atoServe() {
    await backendServer.startOrShowTerminal();
}
