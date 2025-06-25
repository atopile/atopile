import * as vscode from 'vscode';
import * as yaml from 'js-yaml';
import * as path from 'path';
import { traceError } from './log/logging';

export interface Build {
    name: string;
    entry: string; // absolute path to .kicad_pcb file (may not exist yet)
    root: string; // workspace root
    layoutDir?: string; // optional relative path to directory containing layout
}
let builds: Build[] = [];
let manifests: vscode.Uri[] = [];

interface AtoYaml {
    atoVersion?: string;
    paths?: {
        layout?: string; // relative path to root containing layout directories
    };
    builds: {
        [key: string]: {
            entry: string;
            layout?: string; // optional override
        };
    };
    dependencies?: string[];
}

export function getBuilds() {
    return builds;
}

export function getManifests() {
    return manifests;
}

export async function loadBuilds() {
    builds = [];
    manifests = await vscode.workspace.findFiles('**/ato.yaml', '**/.*/**');

    for (const manifest of manifests) {
        try {
            const file = await vscode.workspace.fs.readFile(manifest);
            let fileStr = String.fromCharCode(...file);
            const data = yaml.load(fileStr) as AtoYaml;

            for (const k in data.builds) {
                try {
                    const buildCfg: any = data.builds[k];
                    const rootDir = path.dirname(manifest.fsPath);

                    let pcbPath = buildCfg.entry;

                    // Determine layout directory (store but do not resolve PCB here)
                    let layoutDir: string | undefined;
                    if (buildCfg.layout) {
                        layoutDir = buildCfg.layout;
                    } else if (data.paths?.layout) {
                        layoutDir = path.join(data.paths.layout, k);
                    }

                    // Ensure entry path is absolute (may or may not exist yet)
                    if (!path.isAbsolute(pcbPath)) {
                        pcbPath = path.resolve(rootDir, pcbPath);
                    }

                    builds.push({
                        name: k,
                        entry: pcbPath,
                        root: rootDir,
                        layoutDir,
                    });
                } catch (err) {
                    traceError(`Error processing build config ${k}: ${err}`);
                }
            }
        } catch (error) {
            // do nothing
        }
    }
    return builds;
}
