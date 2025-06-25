import * as vscode from 'vscode';
import { window } from 'vscode';
import { Build, getBuilds, loadBuilds } from '../common/manifest';
import { getAtoBin, onDidChangeAtoBinInfo, runAtoCommandInTerminal } from '../common/findbin';
import { traceError, traceInfo } from '../common/log/logging';
import { openPcb } from '../common/kicad';
import { glob } from 'glob';
import * as path from 'path';
import { g_lsClient } from '../extension';
import { openPackageExplorer } from './packagexplorer';

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

let buttonShell = new Button('terminal', cmdShell, 'Shell', 'Open ato shell', true);
let buttonCreateProject = new Button('new-file', cmdCreateProject, 'Create Project', 'Create new project', true);
// Need project;
let buttonAddPart = new Button('file-binary', cmdAddPart, 'Add Part', 'Add part to project');
let buttonAddPackage = new Button('package', cmdAddPackage, 'Add Package', 'Add package dependency');
let buttonRemovePackage = new Button('trash', cmdRemovePackage, 'Remove Package', 'Remove package dependency');
let buttonBuild = new Button('play', cmdBuild, 'Build', 'Build project');
let buttonLaunchKicad = new Button('circuit-board', cmdLaunchKicad, 'Launch KiCad', 'Open board in KiCad');
let buttonPackageExplorer = new Button('symbol-misc', cmdPackageExplorer, 'Package Explorer', 'Open Package Explorer');
let dropdownChooseBuild = new Button('gear', cmdChooseBuild, 'Choose Build Target', 'Select active build target');

export function getButtons() {
    return buttons;
}

function setBuildTarget(build: Build) {
    dropdownChooseBuild?.setText(_buildsToStr([build])[0]);
    g_lsClient?.sendNotification('atopile/didChangeBuildTarget', {
        buildTarget: build.entry,
    });
}

function getBuildTarget(): Build {
    return _buildStrToBuild(dropdownChooseBuild.statusbar_item.text);
}

function _buildsToStr(builds: Build[]): string[] {
    return builds.map((build) => `${build.root} | ${build.name} | ${build.entry}`);

    // Makes more readable but annoying to parse
    //const multiple_ws = new Set(builds.map((build) => build.root)).size > 1;
    //if (multiple_ws) {
    //    return builds.map((build) => `${build.root} | ${build.name} | ${build.entry}`);
    //} else {
    //    return builds.map((build) => `${build.name} | ${build.entry}`);
    //}
}

function _buildStrToBuild(build_str: string): Build {
    const split = build_str.split(' | ');

    if (split.length !== 3) {
        throw new Error(`Invalid build string: ${build_str}`);
    }

    const [root, name, entry] = split;
    return { root, name, entry };

    // See above
    //if (split.length === 3) {
    //    const [root, name, entry] = split;
    //    return { root, name, entry };
    //} else {
    //    const [name, entry] = split;
    //    return { root: null, name, entry };
    //}
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
            traceInfo(`Buttons: Showing ${button.description} because we have builds`);
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

    if (builds.length > 0) {
        traceInfo(`Buttons: Showing, found ato command in ${atoBin?.source}`);
        setBuildTarget(builds[0]);
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
    const build = getBuildTarget();
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
    const build = getBuildTarget();

    await _runInTerminalWithBuildTarget(`build ${build.name}`, ['build', '--build', build.name], false);
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
}

async function atoCreateProject() {
    await _runInTerminal('create project', undefined, ['create', 'project'], false);
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
    setBuildTarget(build);
}

async function atoLaunchKicad() {
    // get the build target name
    const build = getBuildTarget();

    const pcb_name = build.name + '.kicad_pcb';
    const search_path = `**/${build.name}/${pcb_name}`;
    let paths: string[] = build.root
        ? (await glob(search_path, { cwd: build.root })).map((p) => path.join(build.root as string, p))
        : (await vscode.workspace.findFiles(search_path)).map((uri) => uri.fsPath);

    if (paths.length === 0) {
        traceError(`No pcb file found: ${pcb_name}`);
        vscode.window.showErrorMessage(`No pcb file found: ${pcb_name}. Did you build the project?`);
        return;
    }
    if (paths.length > 1) {
        vscode.window.showErrorMessage(`Bug: multiple pcb files found: ${paths.join(', ')}`);
        return;
    }
    const pcb_path = paths[0];

    try {
        await openPcb(pcb_path);
    } catch (error) {
        traceError(`Error launching KiCad: ${error}`);
        vscode.window.showErrorMessage(`Error launching KiCad: ${error}`);
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
