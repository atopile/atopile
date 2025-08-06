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
import { getBuildTarget, setBuildTarget } from '../common/target';
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
let dropdownChooseBuild = new Button('gear', cmdChooseBuild, 'Choose Build Target', 'Select active build target');
const NO_BUILD = '';
// replace icon with empty text
dropdownChooseBuild.setText(NO_BUILD);

export function getButtons() {
    return buttons;
}

function _setBuildTarget(build: Build | undefined) {
    let text = NO_BUILD;
    if (build) {
        text = _buildsToStr([build])[0];
    }
    dropdownChooseBuild?.setText(text);
    setBuildTarget(build);
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
    if (build_str === NO_BUILD) {
        return undefined;
    }

    const split = build_str.split(' | ');
    if (split.length !== 2) {
        throw new Error(`Invalid build string: ${build_str}`);
    }
    const [disambiguated_root, name] = split;

    const builds = getBuilds();
    const build = builds.find(
        (build) => (!disambiguated_root || build.root.endsWith(disambiguated_root)) && build.name === name,
    );
    if (!build) {
        throw new Error(`Build not found: ${build_str}`);
    }
    return build;
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

    let current_build = undefined;
    try {
        current_build = _buildStrToBuild(dropdownChooseBuild.statusbar_item.text);
    } catch (error) {}

    if (builds.length > 0 && !current_build) {
        _setBuildTarget(builds[0]);
    }
    if (builds.length === 0) {
        _setBuildTarget(undefined);
    }
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

async function _runInTerminalWithBuildTarget(name: string, subcommand: string[], hideFromUser: boolean) {
    const build = _getBuildTarget();

    await _runInTerminal(name, build.root, subcommand, hideFromUser);
}

// Buttons handlers --------------------------------------------------------------------

async function atoShell() {
    await _runInTerminal('shell', undefined, ['--help'], false);
}

async function atoBuild() {
    // TODO: not sure that's very standard behavior
    // save all dirty editors
    // vscode.workspace.saveAll();

    // parse what build target to use
    const build = _getBuildTarget();

    await _runInTerminalWithBuildTarget(`build ${build.name}`, ['build', '--build', build.name], false);

    captureEvent('vsce:build_start'); // TODO: build properties?
}

async function atoExport() {
    // parse what build target to use
    const build = _getBuildTarget();

    await _runInTerminalWithBuildTarget(`export ${build.name}`, ['build', '--build', build.name, '-t', 'all'], false);

    captureEvent('vsce:build_start', {'targets': ['all']});
}

async function atoAddPart() {
    let result = await window.showInputBox({
        placeHolder: 'Manufacturer:PartNumber or LCSC_ID',
    });
    result = result?.trim();
    if (!result) {
        return;
    }

    await _runInTerminalWithBuildTarget(
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

    await _runInTerminalWithBuildTarget('add', ['add', result], false);

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

    await _runInTerminalWithBuildTarget('remove', ['remove', result], false);

    captureEvent('vsce:package_remove', {
        package: result,
    });
}

async function atoCreateProject() {
    await _runInTerminal('create project', undefined, ['create', 'project'], false);

    captureEvent('vsce:project_create');
}

async function atoChooseBuild() {
    // check if a new build was created
    await _reloadBuilds();

    const build_strs = _buildsToStr(getBuilds());

    const result = await window.showQuickPick(build_strs, {
        placeHolder: 'Choose build target',
    });
    if (!result) {
        return;
    }

    let build = _buildStrToBuild(result);
    _setBuildTarget(build);

    captureEvent('vsce:build_target_select', {
        build_target: result,
    });
}

async function atoLaunchKicad() {
    // get the build target name
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
