import * as cp from 'child_process';
import { glob } from 'glob';
import * as path from 'path';
import { traceError, traceInfo, traceWarn } from './log/logging';

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
export async function findPcbnew(): Promise<string> {
    const platform = process.platform;
    let searchQuery: string | null = null;

    let paths: string[] = [];

    if (platform === 'darwin') {
        searchQuery = '/Applications/KiCad/**/pcbnew';
    } else if (platform === 'win32') {
        let programFiles = process.env.ProgramFiles;
        if (programFiles) {
            programFiles = programFiles.replace(/\\/g, '/');
            searchQuery = programFiles + '/KiCad/**/pcbnew.exe';
        }
    } else {
        paths.push('pcbnew');
    }

    if (searchQuery) {
        const results = await glob(searchQuery, { nodir: true, absolute: true });
        if (results.length > 0) {
            paths.push(...results);
        }
    }

    if (paths.length === 0) {
        throw new Error(
            `Could not find pcbnew executable. Searched based on platform: ${platform}. 
            Ensure KiCad is installed and in a standard location.`,
        );
    }

    if (paths.length > 1) {
        traceWarn(`Found multiple pcbnew executables: ${paths.join(', ')}. Using the first one.`);
    }

    const path = paths[0];

    traceInfo(`Found pcbnew executable: ${path}`);
    return path;
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

    traceInfo(`Launching pcbnew with ${pcbnewExecutable} ${pcbPath}`);
    const child = cp.spawn(pcbnewExecutable, [pcbPath], {
        detached: true,
        stdio: 'ignore', // Corresponds to stderr=subprocess.DEVNULL and not waiting
        env: cleanedEnv,
    });

    child.on('error', (err) => {
        // This error usually means the executable could not be found or run
        traceError(`Failed to start pcbnew with ${pcbPath}:`, err);
        throw new Error(`Failed to launch pcbnew: ${err.message}`);
    });

    child.unref(); // Allows the parent (VS Code extension) to exit independently
}
