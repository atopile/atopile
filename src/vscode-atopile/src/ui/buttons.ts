import * as vscode from 'vscode';
import { window } from 'vscode';
import * as os from 'os';
import { Build, getBuilds, loadBuilds } from '../common/manifest';
import { getAtoAlias, getAtoBin, onDidChangeAtoBinInfo, runAtoCommandInTerminal } from '../common/findbin';
import { traceError, traceInfo } from '../common/log/logging';
import { openPcb } from '../common/kicad';
import { glob } from 'glob';
import * as path from 'path';
import { g_lsClient } from '../extension';

let statusbarAtoAddPackage: vscode.StatusBarItem;
let statusbarAtoBuild: vscode.StatusBarItem;
let statusbarAtoBuildTarget: vscode.StatusBarItem;
let statusbarAtoAddPart: vscode.StatusBarItem;
let statusbarAtoLaunchKiCAD: vscode.StatusBarItem;
let statusbarAtoRemovePackage: vscode.StatusBarItem;
let statusbarAtoCreateProject: vscode.StatusBarItem;
let statusbarAtoShell: vscode.StatusBarItem;

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
        statusbarAtoShell.show();
        statusbarAtoCreateProject.show();
    } else {
        statusbarAtoShell.hide();
        statusbarAtoCreateProject.hide();
    }

    const build_strs = _buildsToStr(builds);

    if (builds.length !== 0) {
        traceInfo(`Buttons: Showing, found ato command in ${atoBin?.source}`);
        // TODO: not happy yet with the flow
        statusbarAtoAddPart.show();
        statusbarAtoAddPackage.show();
        statusbarAtoRemovePackage.show();
        statusbarAtoBuild.show();
        statusbarAtoLaunchKiCAD.show();
        statusbarAtoBuildTarget.show();

        statusbarAtoBuildTarget.text = build_strs[0];
        statusbarAtoBuildTarget.tooltip = 'ato: build target';
        g_lsClient?.sendNotification('atopile/didChangeBuildTarget', {
            buildTarget: _buildStrToBuild(build_strs[0]).entry,
        });
    } else {
        if (atoBin) {
            traceInfo(`Buttons: No builds found, hiding`);
        } else {
            traceInfo('Buttons: No ato command found, hiding');
        }

        statusbarAtoAddPart.hide();
        statusbarAtoAddPackage.hide();
        statusbarAtoRemovePackage.hide();
        statusbarAtoBuild.hide();
        statusbarAtoLaunchKiCAD.hide();
        statusbarAtoBuildTarget.hide();
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
    context.subscriptions.push(
        vscode.commands.registerCommand('atopile.add_part', () => {
            atoAddPart();
        }),
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('atopile.shell', () => {
            atoShell();
        }),
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('atopile.build', () => {
            atoBuild();
        }),
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('atopile.add_package', () => {
            atoAddPackage();
        }),
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('atopile.remove_package', () => {
            atoRemovePackage();
        }),
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('atopile.create_project', () => {
            atoCreateProject();
        }),
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('atopile.launch_kicad', () => {
            atoLaunchKicad();
        }),
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('atopile.choose_build', () => {
            atoChooseBuild();
        }),
    );

    const commandAtoShell = 'atopile.shell';
    statusbarAtoShell = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 0);
    statusbarAtoShell.command = commandAtoShell;
    statusbarAtoShell.text = `$(terminal)$(plus)`;
    statusbarAtoShell.tooltip = 'ato: open a shell';

    const commandAtoCreateProject = 'atopile.create_project';
    statusbarAtoCreateProject = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 0);
    statusbarAtoCreateProject.command = commandAtoCreateProject;
    statusbarAtoCreateProject.text = `$(new-file)`;
    statusbarAtoCreateProject.tooltip = 'ato: create project';

    const commandAtoCreate = 'atopile.add_part';
    statusbarAtoAddPart = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 0);
    statusbarAtoAddPart.command = commandAtoCreate;
    statusbarAtoAddPart.text = `$(file-binary)$(arrow-down)`;
    statusbarAtoAddPart.tooltip = 'ato: add a part';
    // statusbarAtoCreate.color = "#F95015";

    const commandAtoAdd = 'atopile.add_package';
    statusbarAtoAddPackage = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 0);
    statusbarAtoAddPackage.command = commandAtoAdd;
    statusbarAtoAddPackage.text = `$(package)$(arrow-down)`;
    statusbarAtoAddPackage.tooltip = 'ato: add a package dependency';
    // statusbarAtoInstall.color = "#F95015";

    const commandAtoRemove = 'atopile.remove_package';
    statusbarAtoRemovePackage = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 0);
    statusbarAtoRemovePackage.command = commandAtoRemove;
    statusbarAtoRemovePackage.text = `$(package)$(close)`;
    statusbarAtoRemovePackage.tooltip = 'ato: remove a package dependency';
    // statusbarAtoRemove.color = "#F95015";

    const commandAtoBuild = 'atopile.build';
    statusbarAtoBuild = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 0);
    statusbarAtoBuild.command = commandAtoBuild;
    statusbarAtoBuild.text = `$(play)`;
    statusbarAtoBuild.tooltip = 'ato: build';
    // statusbarAtoBuild.color = '#F95015';

    const commandAtoLaunchKiCAD = 'atopile.launch_kicad';
    statusbarAtoLaunchKiCAD = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 0);
    statusbarAtoLaunchKiCAD.command = commandAtoLaunchKiCAD;
    statusbarAtoLaunchKiCAD.text = `$(circuit-board)`;
    statusbarAtoLaunchKiCAD.tooltip = 'ato: Launch KiCAD';
    // statusbarAtoBuild.color = '#F95015';

    const commandAtoBuildTarget = 'atopile.choose_build';
    statusbarAtoBuildTarget = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 0);
    statusbarAtoBuildTarget.command = commandAtoBuildTarget;

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
    statusbarAtoAddPackage.dispose();
    statusbarAtoBuild.dispose();
    statusbarAtoBuildTarget.dispose();
    statusbarAtoAddPart.dispose();
    statusbarAtoLaunchKiCAD.dispose();
    statusbarAtoRemovePackage.dispose();
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
    const build = _buildStrToBuild(statusbarAtoBuildTarget.text);
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
    const build = _buildStrToBuild(statusbarAtoBuildTarget.text);

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

    statusbarAtoBuildTarget.text = result;
    g_lsClient?.sendNotification('atopile/didChangeBuildTarget', {
        buildTarget: _buildStrToBuild(result).entry,
    });
}

async function atoLaunchKicad() {
    // get the build target name
    const build = _buildStrToBuild(statusbarAtoBuildTarget.text);

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
