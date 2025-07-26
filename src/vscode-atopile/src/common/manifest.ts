import * as vscode from 'vscode';
import * as yaml from 'js-yaml';
import * as path from 'path';
import { traceError } from './log/logging';

export interface Build {
    name: string;
    entry: string;
    pcb_path: string; // absolute path to .kicad_pcb file (may not exist yet)
    model_path: string; // absolute path to .glb file (pending build with relevant target active)
    root: string; // workspace root
}
let builds: Build[] = [];
let manifests: vscode.Uri[] = [];

export function eqBuilds(a: Build | undefined, b: Build | undefined) {
    if ((a === undefined) !== (b === undefined)) {
        return false;
    }
    if (a === undefined || b === undefined) {
        return true;
    }
    return a.name == b.name && a.entry == b.entry && a.root == b.root;
}

interface AtoYaml {
    atoVersion?: string;
    paths?: {
        layout?: string; // relative path to root containing layout directories
    };
    builds: {
        [key: string]: {
            entry: string;
            paths?: {
                layout?: string;
            };
        };
    };
    dependencies?: Array<{
        type?: string;
        identifier: string;
        release?: string;
    }>;
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

            const rootDir = path.dirname(manifest.fsPath);
            const layoutSubDir = data.paths?.layout || 'elec/layout';

            for (const k in data.builds) {
                try {
                    const buildCfg: any = data.builds[k];

                    let layoutPath = path.join(buildCfg.paths?.layout || layoutSubDir, k, k + '.kicad_pcb');
                    let modelPath = path.join(rootDir, 'build', 'builds', k, k + '.pcba.glb')

                    // Ensure entry path is absolute (may or may not exist yet)
                    if (!path.isAbsolute(layoutPath)) {
                        layoutPath = path.resolve(rootDir, layoutPath);
                    }

                    builds.push({
                        name: k,
                        entry: buildCfg.entry,
                        pcb_path: layoutPath,
                        model_path: modelPath,
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

export async function getManifestData(manifestPath: vscode.Uri): Promise<AtoYaml | null> {
    try {
        const file = await vscode.workspace.fs.readFile(manifestPath);
        let fileStr = String.fromCharCode(...file);
        const data = yaml.load(fileStr) as AtoYaml;
        return data;
    } catch (error) {
        return null;
    }
}

export interface PackageDependency {
    installed: boolean;
    version?: string;
}

export async function getPackageDependency(manifestPath: vscode.Uri, packageId: string): Promise<PackageDependency> {
    const data = await getManifestData(manifestPath);
    
    if (!data) {
        return { installed: false };
    }

    const dependencies = data.dependencies || [];
    
    for (const dep of dependencies) {
        if (dep.identifier === packageId) {
            return {
                installed: true,
                version: dep.release
            };
        }
    }

    return { installed: false };
}
