import * as vscode from 'vscode';
import { window, Uri } from 'vscode';
import { getBuilds, loadBuilds } from '../common/manifest';
import { getAtoBin, onDidChangeAtoBinInfo } from '../common/findbin';
import { traceError } from '../common/log/logging';
import { openPcb } from '../common/kicad';

let statusbarAtoAdd: vscode.StatusBarItem;
let statusbarAtoBuild: vscode.StatusBarItem;
let statusbarAtoBuildTarget: vscode.StatusBarItem;
let statusbarAtoCreate: vscode.StatusBarItem;
let statusbarAtoLaunchKiCAD: vscode.StatusBarItem;
let statusbarAtoRemove: vscode.StatusBarItem;

async function _displayButtons() {
    let builds: string[] = [];
    const atoBin = await _getAtoCommand();
    // only display buttons if we have a valid ato command
    if (atoBin) {
        builds = getBuilds();
    }

    if (builds.length !== 0) {
        statusbarAtoCreate.show();
        statusbarAtoAdd.show();
        statusbarAtoRemove.show();
        statusbarAtoBuild.show();
        statusbarAtoLaunchKiCAD.show();
        statusbarAtoBuildTarget.show();

        statusbarAtoBuildTarget.text = builds[0];
        statusbarAtoBuildTarget.tooltip = 'ato: build target';
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
    return atoBin.map((bin) => `"${bin}"`).join(' ');
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

    // create a terminal to work with
    let buildTerminal = vscode.window.createTerminal({
        name: 'ato build',
        cwd: '${workspaceFolder}',
        hideFromUser: false,
    });

    // parse what build target to use
    let buildArray: string[] = statusbarAtoBuildTarget.text.split('-');

    buildTerminal.sendText(atoBin + ' build --build ' + buildArray[0]);
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

    const result = await window.showQuickPick(getBuilds(), {
        placeHolder: 'Choose build target',
    });
    // set the statusbar to the new text, ignore if canceled
    if (result) {
        statusbarAtoBuildTarget.text = String(result);
    }
}

async function pcbnew() {
    // get the build target name
    let buildArray: string[] = statusbarAtoBuildTarget.text.split('-');
    const buildtarget = buildArray[0];

    let _paths: Uri[] = await vscode.workspace.findFiles(`**/${buildtarget}/${buildtarget}.kicad_pcb`);
    let paths: string[] = _paths.map((uri) => uri.fsPath);

    if (paths.length === 0) {
        traceError(`No pcb file found: ${buildtarget}.kicad_pcb`);
        vscode.window.showErrorMessage(`No pcb file found: ${buildtarget}.kicad_pcb. Did you build the project?`);
        return;
    }
    // TODO handle
    const path = paths[0];

    try {
        await openPcb(path);
    } catch (error) {
        traceError(`Error launching KiCad: ${error}`);
        vscode.window.showErrorMessage(`Error launching KiCad: ${error}`);
    }
}
