import * as vscode from 'vscode';
import { window } from 'vscode';
import * as os from 'os';
import { Build, getBuilds, loadBuilds } from '../common/manifest';
import { getAtoBin, onDidChangeAtoBinInfo } from '../common/findbin';
import { traceError, traceInfo } from '../common/log/logging';
import { openPcb } from '../common/kicad';
import { glob } from 'glob';
import * as path from 'path';
import { g_lsClient } from '../extension'

let statusbarAtoAdd: vscode.StatusBarItem;
let statusbarAtoBuild: vscode.StatusBarItem;
let statusbarAtoBuildTarget: vscode.StatusBarItem;
let statusbarAtoCreate: vscode.StatusBarItem;
let statusbarAtoLaunchKiCAD: vscode.StatusBarItem;
let statusbarAtoRemove: vscode.StatusBarItem;

function _buildsToStr(builds: Build[]): string[] {
    const multiple_ws = new Set(builds.map((build) => build.root)).size > 1;
    if (multiple_ws) {
        return builds.map((build) => `${build.root} | ${build.name} | ${build.entry}`);
    } else {
        return builds.map((build) => `${build.name} | ${build.entry}`);
    }
}

function _buildStrToBuild(build_str: string): Build {
    const split = build_str.split(' | ');
    if (split.length === 3) {
        const [root, name, entry] = split;
        return { root, name, entry };
    } else {
        const [name, entry] = split;
        return { root: null, name, entry };
    }
}

async function _displayButtons() {
    let builds: Build[] = [];
    const atoBin = await _getAtoCommand();
    // only display buttons if we have a valid ato command
    if (atoBin) {
        builds = getBuilds();
    }

    const build_strs = _buildsToStr(builds);

    if (builds.length !== 0) {
        statusbarAtoCreate.show();
        statusbarAtoAdd.show();
        statusbarAtoRemove.show();
        statusbarAtoBuild.show();
        statusbarAtoLaunchKiCAD.show();
        statusbarAtoBuildTarget.show();

        statusbarAtoBuildTarget.text = build_strs[0];
        statusbarAtoBuildTarget.tooltip = 'ato: build target';
        g_lsClient?.sendNotification('atopile/didChangeBuildTarget', {
            buildTarget: _buildStrToBuild(build_strs[0]).entry,
        });
    } else {
        statusbarAtoCreate.hide();
        statusbarAtoAdd.hide();
        statusbarAtoRemove.hide();
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
        vscode.commands.registerCommand('atopile.create', () => {
            atoCreate();
        }),
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('atopile.build', () => {
            atoBuild();
        }),
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('atopile.add', () => {
            atoAddFlow();
        }),
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('atopile.remove', () => {
            atoRemoveFlow();
        }),
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('atopile.launch_kicad', () => {
            pcbnew();
        }),
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('atopile.choose_build', () => {
            selectBuildTargetFlow();
        }),
    );

    const commandAtoCreate = 'atopile.create';
    statusbarAtoCreate = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 0);
    statusbarAtoCreate.command = commandAtoCreate;
    statusbarAtoCreate.text = `$(new-file)`;
    statusbarAtoCreate.tooltip = 'ato: create';
    // statusbarAtoCreate.color = "#F95015";

    const commandAtoAdd = 'atopile.add';
    statusbarAtoAdd = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 0);
    statusbarAtoAdd.command = commandAtoAdd;
    statusbarAtoAdd.text = `$(package)`;
    statusbarAtoAdd.tooltip = 'ato: add a dependency';
    // statusbarAtoInstall.color = "#F95015";

    const commandAtoRemove = 'atopile.remove';
    statusbarAtoRemove = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 0);
    statusbarAtoRemove.command = commandAtoRemove;
    statusbarAtoRemove.text = `$(trash)`;
    statusbarAtoRemove.tooltip = 'ato: remove a dependency';
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
    statusbarAtoAdd.dispose();
    statusbarAtoBuild.dispose();
    statusbarAtoBuildTarget.dispose();
    statusbarAtoCreate.dispose();
    statusbarAtoLaunchKiCAD.dispose();
    statusbarAtoRemove.dispose();
}

async function _getAtoCommand() {
    const atoBin = await getAtoBin();
    if (atoBin === null) {
        return null;
    }
    let out = atoBin.map((bin) => `"${bin}"`).join(' ');
    // if running in powershell, need to add & to the command
    if (os.platform() === 'win32' && vscode.env.shell && vscode.env.shell.toLowerCase().includes('powershell')) {
        out = '& ' + out;
    }
    return out;
}
// Buttons handlers --------------------------------------------------------------------

async function atoBuild() {
    // TODO: not sure that's very standard behavior
    // save all dirty editors
    // vscode.workspace.saveAll();

    const atoBin = await _getAtoCommand();
    if (atoBin === null) {
        return;
    }

    // parse what build target to use
    const build = _buildStrToBuild(statusbarAtoBuildTarget.text);

    // create a terminal to work with
    let buildTerminal = vscode.window.createTerminal({
        name: `ato build ${build.name}`,
        cwd: build.root || '${workspaceFolder}',
        hideFromUser: false,
    });

    buildTerminal.sendText(atoBin + ' build --build ' + build.name);
    buildTerminal.show();
}

async function atoCreate() {
    const atoBin = await _getAtoCommand();
    if (atoBin === null) {
        return;
    }

    let createTerminal = vscode.window.createTerminal({
        name: 'ato create',
        cwd: '${workspaceFolder}',
        hideFromUser: false,
    });

    createTerminal.sendText(atoBin + ' create');
    createTerminal.show();
}

async function atoAddFlow() {
    const atoBin = await _getAtoCommand();
    if (atoBin === null) {
        return;
    }

    let result = await window.showInputBox({
        placeHolder: 'Package name',
    });
    // delete whitespace
    result = result?.trim();

    // if we got a part, try to add it
    if (result) {
        let addTerminal = vscode.window.createTerminal({
            name: 'ato add',
            cwd: '${workspaceFolder}',
            hideFromUser: false,
        });

        addTerminal.sendText(atoBin + ' add ' + result);
        addTerminal.show();
    }
}

async function atoRemoveFlow() {
    const atoBin = await _getAtoCommand();
    if (atoBin === null) {
        return;
    }

    let result = await window.showInputBox({
        placeHolder: 'Package name',
    });
    // delete whitespace
    result = result?.trim();

    // if we got a part, try to remove it
    if (result) {
        let removeTerminal = vscode.window.createTerminal({
            name: 'ato remove',
            cwd: '${workspaceFolder}',
            hideFromUser: false,
        });
        removeTerminal.sendText(atoBin + ' remove ' + result);
        removeTerminal.show();
    }
}

async function selectBuildTargetFlow() {
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

async function pcbnew() {
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
