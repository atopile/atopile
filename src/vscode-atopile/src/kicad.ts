import * as cp from 'child_process';
import { glob } from 'glob';
import * as path from 'path';
import * as vscode from 'vscode';
import * as yaml from 'js-yaml';
import type { AtoYaml, BuildTarget } from '../../ui/shared/types';

async function loadBuilds(): Promise<BuildTarget[]> {
    const builds: BuildTarget[] = [];
    const manifests = await vscode.workspace.findFiles('**/ato.yaml', '**/.*/**');

    for (const manifest of manifests) {
        try {
            const file = await vscode.workspace.fs.readFile(manifest);
            const data = yaml.load(String.fromCharCode(...file)) as AtoYaml;
            const rootDir = path.dirname(manifest.fsPath);
            const layoutSubDir = data.paths?.layout || 'elec/layout';

            for (const [name, buildCfg] of Object.entries(data.builds)) {
                try {
                    let layoutPath = path.join(buildCfg.paths?.layout || layoutSubDir, name, `${name}.kicad_pcb`);
                    const modelPath = path.join(rootDir, 'build', 'builds', name, `${name}.pcba.glb`);

                    if (!path.isAbsolute(layoutPath)) {
                        layoutPath = path.resolve(rootDir, layoutPath);
                    }

                    builds.push({
                        name,
                        entry: buildCfg.entry,
                        pcb_path: layoutPath,
                        model_path: modelPath,
                        root: rootDir,
                    });
                } catch (err) {
                    console.error(`Error processing build config ${name}: ${err}`);
                }
            }
        } catch {
            // skip unreadable manifests
        }
    }

    return builds;
}

export async function getBuildTarget(projectRoot: string, target: string): Promise<BuildTarget> {
    const builds = await loadBuilds();
    const build = builds.find((candidate) => candidate.root === projectRoot && candidate.name === target);
    if (!build) {
        throw new Error(`No build config found for target "${target}".`);
    }
    return build;
}

/**
 * Creates a new environment object with Python virtual environment-specific
 * variables removed or modified. This is to prevent KiCad's potential
 * internal Python scripting from being affected by the calling environment.
 * @returns A new environment object.
 */
function removeVenvFromEnv(): NodeJS.ProcessEnv {
    const newEnv = { ...process.env };

    const venvPath = process.env.VIRTUAL_ENV;

    if (venvPath) {
        delete newEnv.VIRTUAL_ENV;

        if (newEnv.PATH) {
            const pathDirs = newEnv.PATH.split(path.delimiter);
            const venvBinDirs = [
                path.join(venvPath, 'bin'), // For Linux/macOS
                path.join(venvPath, 'Scripts'), // For Windows
            ];
            newEnv.PATH = pathDirs.filter((dir) => !venvBinDirs.includes(dir)).join(path.delimiter);
        }
    }
    return newEnv;
}

/**
 * Finds the path to the pcbnew executable.
 * @returns The path to the pcbnew executable.
 * @throws FileNotFoundError if pcbnew cannot be found.
 */
export async function findKicadBin(bin_name: string): Promise<string> {
    const platform = process.platform;
    let searchQuery: string | null = null;

    let paths: string[] = [];

    if (platform === 'darwin') {
        searchQuery = `/Applications/KiCad/**/${bin_name}`;
    } else if (platform === 'win32') {
        let programFiles = process.env.ProgramFiles;
        if (programFiles) {
            programFiles = programFiles.replace(/\\/g, '/');
            searchQuery = programFiles + `/KiCad/**/${bin_name}.exe`;
        }
    } else {
        paths.push(bin_name);
    }

    if (searchQuery) {
        const results = await glob(searchQuery, { nodir: true, absolute: true });
        if (results.length > 0) {
            paths.push(...results);
        }
    }

    if (paths.length === 0) {
        throw new Error(
            `Could not find ${bin_name} executable. Searched based on platform: ${platform}.
            Ensure KiCad is installed and in a standard location.`,
        );
    }

    if (paths.length > 1) {
        console.warn(`Found multiple ${bin_name} executables: ${paths.join(', ')}. Using the first one.`);
    }

    const binPath = paths[0];

    console.log(`Found pcbnew executable: ${binPath}`);
    return binPath;
}

export async function findPcbnew(): Promise<string> {
    return findKicadBin('pcbnew');
}

/**
 * Opens a PCB file with pcbnew.
 * @param pcbPath The absolute path to the .kicad_pcb file.
 * @throws RuntimeError if pcbnew is already running with the specified PCB file.
 * @throws Error if pcbnew cannot be launched.
 */
export async function openPcb(pcbPath: string): Promise<void> {
    const pcbnewExecutable = await findPcbnew();
    const cleanedEnv = removeVenvFromEnv();

    console.log(`Launching pcbnew with ${pcbnewExecutable} ${pcbPath}`);
    const child = cp.spawn(pcbnewExecutable, [pcbPath], {
        detached: true,
        stdio: 'ignore', // Corresponds to stderr=subprocess.DEVNULL and not waiting
        env: cleanedEnv,
    });

    child.on('error', (err) => {
        // This error usually means the executable could not be found or run
        console.error(`Failed to start pcbnew with ${pcbPath}:`, err);
        throw new Error(`Failed to launch pcbnew: ${err.message}`);
    });

    child.unref(); // Allows the parent (VS Code extension) to exit independently
}

/**
 * Finds the PCB path for a build target and opens it with pcbnew.
 * @throws Error if the build target cannot be found.
 */
export async function openKicadForBuild(projectRoot: string, target: string): Promise<void> {
    const build = await getBuildTarget(projectRoot, target);
    await openPcb(build.pcb_path);
}
