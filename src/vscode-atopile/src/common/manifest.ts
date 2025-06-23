import * as vscode from 'vscode';
import * as yaml from 'js-yaml';
import * as path from 'path';
import { traceInfo, traceError } from './log/logging';
import { glob } from 'glob';

export interface Build {
    name: string;
    entry: string; // absolute path to .kicad_pcb file for this build
    root: string; // workspace root this build belongs to
}
let builds: Build[] = [];

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

export async function loadBuilds() {
    builds = [];
    const manifests = await vscode.workspace.findFiles('**/ato.yaml', '**/.*/**');

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

                    // Determine layout directory to search for PCB
                    let layoutDir: string | undefined = undefined;
                    if (buildCfg.layout) {
                        layoutDir = buildCfg.layout;
                    } else if (data.paths?.layout) {
                        // Use top-level layout path joined with build name
                        layoutDir = path.join(data.paths.layout, k);
                    }

                    if (layoutDir) {
                        const absLayoutDir = path.resolve(rootDir, layoutDir);
                        // traceInfo(`Searching for .kicad_pcb in layout dir: ${absLayoutDir}`);
                        const matches = await glob('*.kicad_pcb', {
                            cwd: absLayoutDir,
                            absolute: true,
                        });
                        if (matches.length > 0) {
                            pcbPath = matches[0];
                            // traceInfo(`Found .kicad_pcb in layout dir: ${pcbPath}`);
                        } else {
                            traceError(`No .kicad_pcb found in layout dir ${absLayoutDir} for build ${k}`);
                        }
                    }

                    // Ensure pcbPath is absolute
                    if (!path.isAbsolute(pcbPath)) {
                        pcbPath = path.resolve(rootDir, pcbPath);
                    }

                    builds.push({
                        name: k,
                        entry: pcbPath,
                        root: rootDir,
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
