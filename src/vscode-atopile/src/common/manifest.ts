import * as vscode from 'vscode';
import * as yaml from 'js-yaml';

export interface Build {
    name: string;
    entry: string;
    root: string | null;
}
let builds: Build[] = [];

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
    builds = [];
    for (const ws of vscode.workspace.workspaceFolders || []) {
        let uri = vscode.Uri.file(ws.uri.fsPath + '/ato.yaml');
        try {
            const file = await vscode.workspace.fs.readFile(uri);
            let fileStr = String.fromCharCode(...file);
            const data = yaml.load(fileStr) as AtoYaml;

            for (const k in data.builds) {
                builds.push({
                    name: k,
                    entry: data.builds[k].entry,
                    root: ws.uri.fsPath,
                });
            }
        } catch (error) {
            // do nothing
        }
    }
    return builds;
}
