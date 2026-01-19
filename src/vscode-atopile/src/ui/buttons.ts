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
    setBuildTarget,
    getSelectedTargets,
    setSelectedTargets,
    isTargetSelected,
    toggleTarget,
    getProjectRoot,
    setProjectRoot,
} from '../common/target';
import { disambiguatePaths } from '../common/utilities';

let buttons: Button[] = [];
let commands: Command[] = [];

class Command {
    handler: () => Promise<void>;
    command_name: string;

    constructor(handler: () => Promise<void>, command_name: string) {
        this.handler = handler;
        this.command_name = command_name;
        commands.push(this);
    }

    async init(context: vscode.ExtensionContext) {
        context.subscriptions.push(vscode.commands.registerCommand(this.getCommandName(), this.handler));
    }

    getCommandName() {
        return this.command_name;
    }
}
class Button {
    statusbar_item: vscode.StatusBarItem;
    show_on_no_targets: boolean;
    show_on_no_ato: boolean;
    description: string;
    tooltip: string;
    icon: vscode.ThemeIcon;
    command: Command;

    constructor(
        icon: string,
        command: Command,
        tooltip: string,
        description: string,
        show_on_no_ato: boolean = false,
        show_on_no_target: boolean = false,
    ) {
        this.show_on_no_ato = show_on_no_ato;
        this.show_on_no_targets = show_on_no_target;
        this.description = description;
        this.tooltip = tooltip;
        this.icon = new vscode.ThemeIcon(icon);
        this.command = command;

        this.statusbar_item = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 0);
        this.statusbar_item.tooltip = `ato: ${tooltip}`;
        this.statusbar_item.command = command.getCommandName();
        this.statusbar_item.text = `$(${icon})`;

        buttons.push(this);
    }

    async setText(text: string) {
        this.statusbar_item.text = text;
    }

    async hide() {
        this.statusbar_item.hide();
    }

    async show() {
        this.statusbar_item.show();
    }
}

let cmdShell = new Command(atoShell, 'atopile.shell');
let cmdCreateProject = new Command(atoCreateProject, 'atopile.create_project');
let cmdAddPart = new Command(atoAddPart, 'atopile.add_part');
let cmdAddPackage = new Command(atoAddPackage, 'atopile.add_package');
let cmdRemovePackage = new Command(atoRemovePackage, 'atopile.remove_package');
let cmdBuild = new Command(atoBuild, 'atopile.build');
let cmdPackageExplorer = new Command(atoPackageExplorer, 'atopile.package_explorer');
let cmdChooseBuild = new Command(atoChooseBuild, 'atopile.choose_build');
let cmdChooseProject = new Command(atoChooseProject, 'atopile.choose_project');
let cmdLaunchKicad = new Command(atoLaunchKicad, 'atopile.launch_kicad');
let cmdKicanvasPreview = new Command(atoKicanvasPreview, 'atopile.kicanvas_preview');
let cmdModelViewerPreview = new Command(atoModelViewerPreview, 'atopile.modelviewer_preview');
let cmdExport = new Command(atoExport, 'atopile.export');

let buttonShell = new Button('terminal', cmdShell, 'Shell', 'Open ato shell', true, true);
let buttonCreateProject = new Button('new-file', cmdCreateProject, 'Create Project', 'Create new project', true, true);
// Need project;
let buttonAddPart = new Button('file-binary', cmdAddPart, 'Add Part', 'Add part to project');
let buttonAddPackage = new Button('package', cmdAddPackage, 'Add Package', 'Add package dependency');
let buttonRemovePackage = new Button('trash', cmdRemovePackage, 'Remove Package', 'Remove package dependency');
let buttonBuild = new Button('play', cmdBuild, 'Build', 'Build project');
let buttonExport = new Button('file-zip', cmdExport, 'Generate Manufacturing Data', 'Generate manufacturing data for the build');
let buttonLaunchKicad = new Button('circuit-board', cmdLaunchKicad, 'Launch KiCad', 'Open board in KiCad');
let buttonPackageExplorer = new Button('symbol-misc', cmdPackageExplorer, 'Package Explorer', 'Open Package Explorer');
let buttonKicanvasPreview = new Button('eye', cmdKicanvasPreview, 'Layout Preview', 'Open Layout Preview');
let buttonModelViewerPreview = new Button(
    'symbol-constructor',
    cmdModelViewerPreview,
    '3D Preview',
    'Open 3D Model Preview',
);
let dropdownChooseBuild = new Button('checklist', cmdChooseBuild, 'Choose Build Targets', 'Select build targets');
let dropdownChooseProject = new Button('folder', cmdChooseProject, 'Choose Project', 'Select project folder');

const NO_BUILD = '$(checklist)';
const NO_PROJECT = '$(folder)';

// Initialize button text
dropdownChooseBuild.setText(NO_BUILD);
dropdownChooseProject.setText(NO_PROJECT);

export function getButtons() {
    return buttons;
}

function _updateBuildTargetDisplay() {
    const selected = getSelectedTargets();
    if (selected.length === 0) {
        dropdownChooseBuild.setText(NO_BUILD);
    } else if (selected.length === 1) {
        dropdownChooseBuild.setText(`$(check) ${selected[0].name}`);
    } else {
        dropdownChooseBuild.setText(`$(checklist) ${selected.length} targets`);
    }
}

function _updateProjectDisplay() {
    const root = getProjectRoot();
    if (root) {
        dropdownChooseProject.setText(`$(folder) ${path.basename(root)}`);
    } else {
        dropdownChooseProject.setText(NO_PROJECT);
    }
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

function _buildsToStr(builds: Build[]): string[] {
    // disambiguate roots folder_names by attach prefixes until unique
    const disambiguated = disambiguatePaths(builds, (build) => `${build.root}/${build.name}`);

    function uniqueToStr(_path: string, build: Build): string {
        const split = _path.split('/');
        if (split.length === 1) {
            return `${path.basename(build.root)} | ${build.name}`;
        }
        return `${path.join(...split.slice(0, -1))} | ${split[split.length - 1]}`;
    }

    return Object.entries(disambiguated).map(([path, build]) => `${uniqueToStr(path, build)}`);
}

function _buildStrToBuild(build_str: string): Build | undefined {
    // Remove checkbox prefix if present
    const cleanStr = build_str.replace(/^\$\([^)]+\)\s*/, '').trim();

    const split = cleanStr.split(' | ');
    if (split.length !== 2) {
        return undefined;
    }
    const [disambiguated_root, name] = split;

    const builds = getBuilds();
    const build = builds.find(
        (build) => (!disambiguated_root || build.root.endsWith(disambiguated_root)) && build.name === name,
    );
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

async function _displayButtons() {
    let builds: Build[] = [];
    const atoBin = await getAtoBin();
    // only display buttons if we have a valid ato command
    if (atoBin) {
        builds = getBuilds();
    }

    for (const button of buttons) {
        if (builds.length > 0) {
            button.show();
        } else if (!button.show_on_no_targets) {
            button.hide();
        } else {
            if (atoBin) {
                button.show();
            } else if (!button.show_on_no_ato) {
                button.hide();
            } else {
                button.show();
            }
        }
    }

    // Auto-select first project and all its builds if nothing selected
    const selected = getSelectedTargets();
    if (builds.length > 0 && selected.length === 0) {
        // Get unique project roots
        const roots = _getProjectRoots();
        if (roots.length > 0) {
            const firstRoot = roots[0];
            setProjectRoot(firstRoot);
            // Select all builds in the first project
            const projectBuilds = builds.filter(b => b.root === firstRoot);
            setSelectedTargets(projectBuilds);
        }
    }
    if (builds.length === 0) {
        setSelectedTargets([]);
        setProjectRoot(undefined);
    }

    _updateBuildTargetDisplay();
    _updateProjectDisplay();
}

async function _reloadBuilds() {
    await loadBuilds();
    await _displayButtons();
    return getBuilds();
}

export async function forceReloadButtons() {
    await _reloadBuilds();
}

export async function activate(context: vscode.ExtensionContext) {
    // register command handlers and buttons
    for (const command of commands) {
        await command.init(context);
    }

    await _reloadBuilds();

    context.subscriptions.push(
        onDidChangeAtoBinInfo(async () => {
            await _reloadBuilds();
        }),
        // on file save of ato.yaml, reload the builds
        vscode.workspace.onDidSaveTextDocument(async (document) => {
            if (document.uri.fsPath.endsWith('ato.yaml')) {
                await _reloadBuilds();
            }
        }),
        // on file creation of ato.yaml, reload the builds
        vscode.workspace.onDidCreateFiles(async (event) => {
            if (event.files.some((file) => file.fsPath.endsWith('ato.yaml'))) {
                await _reloadBuilds();
            }
        }),
        // on file deletion of ato.yaml, reload the builds
        vscode.workspace.onDidDeleteFiles(async (event) => {
            if (event.files.some((file) => file.fsPath.endsWith('ato.yaml'))) {
                await _reloadBuilds();
            }
        }),
    );
}

export function deactivate() {
    for (const button of buttons) {
        button.statusbar_item.dispose();
    }
}

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

// Buttons handlers --------------------------------------------------------------------

async function atoShell() {
    await _runInTerminal('shell', undefined, ['--help'], false);
}

async function atoBuild() {
    // Get all selected build targets
    const builds = _getSelectedBuilds();
    const root = getProjectRoot();

    if (!root) {
        vscode.window.showErrorMessage('No project folder selected');
        return;
    }

    // Focus the log viewer panel to show build progress
    vscode.commands.executeCommand('atopile.logViewer.focus');

    // Run build in terminal (server starts automatically)
    const buildArgs = ['build'];
    for (const build of builds) {
        buildArgs.push('--build', build.name);
    }

    const targetNames = builds.map(b => b.name).join(', ');
    await _runInTerminal(`build ${targetNames}`, root, buildArgs, false);

    captureEvent('vsce:build_start', { targets: builds.map(b => b.name) });
}

async function atoExport() {
    // Get all selected build targets
    const builds = _getSelectedBuilds();
    const root = getProjectRoot();

    if (!root) {
        vscode.window.showErrorMessage('No project folder selected');
        return;
    }

    // Export all selected targets
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

    captureEvent('vsce:part_create', {
        part: result,
    });
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

    captureEvent('vsce:package_add', {
        package: result,
    });
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

    captureEvent('vsce:package_remove', {
        package: result,
    });
}

async function atoCreateProject() {
    await _runInTerminal('create project', undefined, ['create', 'project'], false);

    captureEvent('vsce:project_create');
}

async function atoChooseProject() {
    // Check if builds were updated
    await _reloadBuilds();

    const roots = _getProjectRoots();

    if (roots.length === 0) {
        vscode.window.showInformationMessage('No projects found. Create a project first.');
        return;
    }

    // Show project folders with current selection marked
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

    // Set the project root
    setProjectRoot(result.root);
    _updateProjectDisplay();

    // Auto-select all builds in this project
    const builds = getBuilds().filter(b => b.root === result.root);
    setSelectedTargets(builds);
    _updateBuildTargetDisplay();

    captureEvent('vsce:project_select', {
        project: result.root,
    });
}

async function atoChooseBuild() {
    // Check if builds were updated
    await _reloadBuilds();

    const currentRoot = getProjectRoot();
    if (!currentRoot) {
        vscode.window.showInformationMessage('Select a project folder first.');
        return;
    }

    // Get builds for the current project only
    const projectBuilds = getBuilds().filter(b => b.root === currentRoot);

    if (projectBuilds.length === 0) {
        vscode.window.showInformationMessage('No build targets found in this project.');
        return;
    }

    // Create items with checkmarks for selected builds
    interface BuildQuickPickItem extends vscode.QuickPickItem {
        build: Build;
    }

    const items: BuildQuickPickItem[] = projectBuilds.map(build => ({
        label: `${isTargetSelected(build) ? '$(check)' : '$(circle-outline)'} ${build.name}`,
        description: build.entry,
        build: build,
        picked: isTargetSelected(build),
    }));

    // Add "Select All" and "Select None" options
    const selectAllLabel = '$(checklist) Select All';
    const selectNoneLabel = '$(circle-outline) Select None';

    // Create a quick pick with custom behavior
    const quickPick = window.createQuickPick<BuildQuickPickItem>();
    quickPick.items = items;
    quickPick.title = 'Select Build Targets';
    quickPick.placeholder = 'Click to toggle selection (click outside to close)';
    quickPick.canSelectMany = false; // We'll handle multi-select ourselves

    // Add buttons for select all/none
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
        // Refresh the list
        quickPick.items = projectBuilds.map(build => ({
            label: `${isTargetSelected(build) ? '$(check)' : '$(circle-outline)'} ${build.name}`,
            description: build.entry,
            build: build,
            picked: isTargetSelected(build),
        }));
        _updateBuildTargetDisplay();
    });

    quickPick.onDidAccept(() => {
        const selected = quickPick.selectedItems[0];
        if (selected) {
            // Toggle the selected build
            toggleTarget(selected.build);
            // Refresh the list to show updated checkmarks
            quickPick.items = projectBuilds.map(build => ({
                label: `${isTargetSelected(build) ? '$(check)' : '$(circle-outline)'} ${build.name}`,
                description: build.entry,
                build: build,
                picked: isTargetSelected(build),
            }));
            _updateBuildTargetDisplay();
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

async function atoLaunchKicad() {
    // get the first selected build target
    const build = _getBuildTarget();

    const pcb_name = build.name + '.kicad_pcb';
    const search_path = `**/${build.name}/${pcb_name}`;
    let paths: string[] = build.root
        ? (await glob(search_path, { cwd: build.root })).map((p) => path.join(build.root as string, p))
        : (await vscode.workspace.findFiles(search_path)).map((uri) => uri.fsPath);

    if (paths.length === 0) {
        traceError(`No pcb file found: ${pcb_name}`);
        vscode.window.showErrorMessage(`No pcb file found: ${pcb_name}. Did you build the project?`);
        captureEvent('vsce:pcbnew_fail', {
            error: 'no_pcb_file',
        });
        return;
    }
    if (paths.length > 1) {
        vscode.window.showErrorMessage(`Bug: multiple pcb files found: ${paths.join(', ')}`);
        captureEvent('vsce:pcbnew_fail', {
            error: 'multiple_pcb_files',
        });
        return;
    }
    const pcb_path = paths[0];

    try {
        await openPcb(pcb_path);
        captureEvent('vsce:pcbnew_success');
    } catch (error) {
        traceError(`Error launching KiCad: ${error}`);
        vscode.window.showErrorMessage(`Error launching KiCad: ${error}`);
        captureEvent('vsce:pcbnew_fail', {
            error: 'unknown',
        });
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
