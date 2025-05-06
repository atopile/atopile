import * as vscode from 'vscode';
import { window, Uri } from 'vscode';
import * as yaml from 'js-yaml';
import * as cp from 'child_process';

let statusbarAtoBuild: vscode.StatusBarItem;
let statusbarAtoCreate: vscode.StatusBarItem;
let statusbarAtoAdd: vscode.StatusBarItem;
let statusbarAtoRemove: vscode.StatusBarItem;
let statusbarAtoBuildTarget: vscode.StatusBarItem;
let statusbarAtoLaunchKiCAD: vscode.StatusBarItem;

let builds: string[] = [];
interface AtoYaml {
    atoVersion: string;
    builds: {
        [key: string]: {
            entry: string;
        };
    };
    dependencies: string[];
}

async function atoBuild() {
    // save all dirty editors
    vscode.workspace.saveAll();

    // create a terminal to work with
    let buildTerminal = vscode.window.createTerminal({
        name: 'ato build',
        cwd: '${workspaceFolder}',
        hideFromUser: false,
    });

    // parse what build target to use
    let buildArray: string[] = statusbarAtoBuildTarget.text.split('-');

    buildTerminal.sendText('ato build --build ' + buildArray[0]);
    buildTerminal.show();
}

async function atoCreate() {
    let createTerminal = vscode.window.createTerminal({
        name: 'ato create',
        cwd: '${workspaceFolder}',
        hideFromUser: false,
    });

    createTerminal.sendText('ato create');
    createTerminal.show();
}

async function processAddPackage() {
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

        addTerminal.sendText('ato add ' + result);
        addTerminal.show();
    }
}

async function processRemovePackage() {
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
        removeTerminal.sendText('ato remove ' + result);
        removeTerminal.show();
    }
}

async function processChooseBuildTarget() {
    // check if a new build was created
    await _loadBuilds();

    const result = await window.showQuickPick(builds, {
        placeHolder: 'Choose build target',
    });
    // set the statusbar to the new text, ignore if canceled
    if (result) {
        statusbarAtoBuildTarget.text = String(result);
    }
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
            processAddPackage();
        }),
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('atopile.remove', () => {
            processRemovePackage();
        }),
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('atopile.launch_kicad', () => {
            processLaunchKiCAD();
        }),
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('atopile.choose_build', () => {
            processChooseBuildTarget();
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

    await _loadBuilds();
    _displayButtons();
}

async function processLaunchKiCAD() {
    // get the build target name
    let buildArray: string[] = statusbarAtoBuildTarget.text.split('-');

    // search for the *.kicad_pcb file in the **/layout/[build]/ folder, relative to workspace root, only find 1 file
    let path = await vscode.workspace.findFiles('**/layout/' + buildArray[0] + '/*.kicad_pcb', '**/.ato/**', 1);

    // turn the result into a Uri
    let schem = Uri.parse(path.toString());

    // launch if it found a file to open
    if (schem.path !== '/') {
        cp.exec(`start "" ${schem.fsPath}`);
    }
}

function _displayButtons() {
    if (builds.length !== 0) {
        statusbarAtoCreate.show();
        statusbarAtoAdd.show();
        statusbarAtoRemove.show();
        statusbarAtoBuild.show();
        statusbarAtoLaunchKiCAD.show();
        statusbarAtoBuildTarget.show();
    } else {
        statusbarAtoCreate.hide();
        statusbarAtoAdd.hide();
        statusbarAtoRemove.hide();
        statusbarAtoBuild.hide();
        statusbarAtoLaunchKiCAD.hide();
        statusbarAtoBuildTarget.hide();
    }
}

async function _loadBuilds() {
    let ws = vscode.workspace.workspaceFolders![0].uri.path;
    let uri = vscode.Uri.file(ws + '/ato.yaml');

    builds = [];
    try {
        const file = await vscode.workspace.fs.readFile(uri);
        let fileStr = String.fromCharCode(...file);
        const data = yaml.load(fileStr) as AtoYaml;

        for (const k in data.builds) {
            // make things easy and put the target name in what is displayed, we
            // can parse it later without having to reload again
            builds.push(k + '-' + data.builds[k].entry);
        }
        statusbarAtoBuildTarget.text = builds[0];
        statusbarAtoBuildTarget.tooltip = 'ato: build target';
    } catch (error) {
        // do nothing
    }
}

export function deactivate() { }
