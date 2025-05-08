import * as vscode from 'vscode';
import { window, Uri } from 'vscode';
import * as yaml from 'js-yaml';
import * as cp from 'child_process';

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

export function getBuilds() {
    return builds;
}

export async function loadBuilds() {
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
    } catch (error) {
        // do nothing
    }
}
