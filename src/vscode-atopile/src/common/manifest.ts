import * as vscode from 'vscode';
import * as yaml from 'js-yaml';
import * as path from 'path';
import { traceInfo } from './log/logging';

export interface Build {
    name: string;
    entry: string;
    root: string;
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
    const manifests = await vscode.workspace.findFiles('**/ato.yaml', '**/.*/**');

    for (const manifest of manifests) {
        try {
            const file = await vscode.workspace.fs.readFile(manifest);
            let fileStr = String.fromCharCode(...file);
            const data = yaml.load(fileStr) as AtoYaml;

            for (const k in data.builds) {
                builds.push({
                    name: k,
                    entry: data.builds[k].entry,
                    root: path.dirname(manifest.fsPath),
                });
            }
        } catch (error) {
            // do nothing
        }
    }
    return builds;
}
