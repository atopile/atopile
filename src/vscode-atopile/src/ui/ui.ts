import * as vscode from 'vscode';
import { window, Uri } from 'vscode';
import * as yaml from 'js-yaml';
import * as cp from 'child_process';

let statusbarAtoBuild: vscode.StatusBarItem;
let statusbarAtoCreate: vscode.StatusBarItem;
let statusbarAtoInstall: vscode.StatusBarItem;
let statusbarAtoInstallPackage: vscode.StatusBarItem;
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
const atopileInterpreterSetting = 'atopile.interpreter';

async function atoBuild() {
    // save all dirty editors
    vscode.workspace.saveAll();

    // create a terminal to work with
    let buildTerminal = vscode.window.createTerminal({
        name: 'ato Build',
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
        name: 'ato Create',
        cwd: '${workspaceFolder}',
        hideFromUser: false,
    });

    createTerminal.sendText('ato create');
    createTerminal.show();
}

async function processInstallJlcpcb() {
    let result = await window.showInputBox({
        placeHolder: 'JLCPCB Component ID',
    });
    // delete whitespace
    result = result?.trim();

    // if we got a part, try to install it
    if (result) {
        let installTerminal = vscode.window.createTerminal({
            name: 'ato Install',
            cwd: '${workspaceFolder}',
            hideFromUser: false,
        });

        installTerminal.sendText('ato install --jlcpcb ' + result);
        installTerminal.show();
    }
}

async function processInstallPackage() {
    let result = await window.showInputBox({
        placeHolder: 'Package name',
    });
    // delete whitespace
    result = result?.trim();

    // if we got a part, try to install it
    if (result) {
        let installTerminal = vscode.window.createTerminal({
            name: 'ato Install',
            cwd: '${workspaceFolder}',
            hideFromUser: false,
        });
        installTerminal.sendText('ato install ' + result);
        installTerminal.show();
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
        vscode.commands.registerCommand('atopile.install', () => {
            processInstallJlcpcb();
        }),
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('atopile.install_package', () => {
            processInstallPackage();
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
    statusbarAtoCreate.text = `$(plus)`;
    statusbarAtoCreate.tooltip = 'ato: create project/build';
    // statusbarAtoCreate.color = "#F95015";

    const commandAtoInstall = 'atopile.install';
    statusbarAtoInstall = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 0);
    statusbarAtoInstall.command = commandAtoInstall;
    statusbarAtoInstall.text = `$(cloud-download)`;
    statusbarAtoInstall.tooltip = 'ato: install JLCPCB component';
    // statusbarAtoInstall.color = "#F95015";

    const commandAtoInstallPackage = 'atopile.install_package';
    statusbarAtoInstallPackage = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 0);
    statusbarAtoInstallPackage.command = commandAtoInstallPackage;
    statusbarAtoInstallPackage.text = `$(package)`;
    statusbarAtoInstallPackage.tooltip = 'ato: install package';
    // statusbarAtoInstallPackage.color = "#F95015";

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
        statusbarAtoInstall.show();
        statusbarAtoInstallPackage.show();
        statusbarAtoBuild.show();
        statusbarAtoLaunchKiCAD.show();
        statusbarAtoBuildTarget.show();
    } else {
        statusbarAtoCreate.hide();
        statusbarAtoInstall.hide();
        statusbarAtoInstallPackage.hide();
        statusbarAtoBuild.hide();
        statusbarAtoBuildTarget.hide();
        statusbarAtoLaunchKiCAD.hide();
    }
}

async function _loadBuilds() {
    let ws = vscode.workspace.workspaceFolders![0].uri.path;
    let uri = vscode.Uri.file(ws + '/ato.yaml');

    // open ato.yaml file
    try {
        //
        builds = [];
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

export function deactivate() {}
