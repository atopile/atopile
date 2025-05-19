import * as vscode from 'vscode';
import * as fs from 'fs';
import { onDidChangeAtoBinInfoEvent, g_uv_path_local, getAtoBin } from '../common/findbin';
import { traceError, traceInfo } from '../common/log/logging';
import { downloadReleaseAssetBin, PlatformArch } from '../common/github';

/**
 * Check if ato bin is available (see findbin.ts)
 * If not ask user with popup if they want to configure their settings.json or
 * automatically install ato
 *
 * If automatic install:
 *  1. check the platform
 *  2. download the appropriate uv binary from
 *    https://github.com/astral-sh/uv/releases/latest
 *  3. Extract uv from the package and save it to some vscode folder
 *  4. findbin.ts will detect uv from now on and run ato with it
 */

// Map platform and architecture to the appropriate asset information
const _PLATFORM_MAP: Record<string, string> = {
    'unknown-linux-gnu': 'linux',
    'pc-windows-msvc': 'win32',
    'apple-darwin': 'darwin',
};

const _ARCH_MAP: Record<string, string> = {
    aarch64: 'arm64',
    x86_64: 'x64',
    x86: 'x86',
    amd64: 'x64',
    i386: 'x86',
    i686: 'x86',
};

function uvNameToPlatformArch(name: string): PlatformArch | null {
    // example: uv-aarch64-unknown-linux-gnu.tar.gz
    // format: uv-<arch>-<platform_long>.<zip|tar.gz>
    // platform_long: linux: unknown-linux-gnu, win32: pc-windows-msvc, darwin: apple-darwin

    // regex match uv-<arch>-<platform_long>.<zip|tar.gz>
    const regex = /^uv-([^-]+)-([^.]+)\.(zip|tar\.gz)$/;
    const match = name.match(regex);
    if (!match) {
        return null;
    }
    const arch = match[1];
    const platformLong = match[2];
    const platform = _PLATFORM_MAP[platformLong];
    if (!platform) {
        return null;
    }
    const arch_mapped = _ARCH_MAP[arch] || arch;

    return {
        platform: platform,
        arch: arch_mapped,
    };
}

async function downloadAndInstallUv(status: vscode.StatusBarItem) {
    const uvExePath = g_uv_path_local;

    if (!uvExePath) {
        traceError(`uv executable path not found`);
        throw new Error(`uv executable path not found`);
    }

    if (fs.existsSync(uvExePath)) {
        traceInfo(`uv already found at ${uvExePath}`);
        return;
    }

    await downloadReleaseAssetBin('astral-sh/uv', uvExePath, 'uv', uvNameToPlatformArch, status);
}

export async function activate(context: vscode.ExtensionContext) {
    traceInfo('Activating setup');

    // Pass context to getAtoBin so it can be stored and used by getExtensionManagedUvPath
    let atoBin = await getAtoBin();
    if (atoBin) {
        traceInfo(`atopile binary found: ${atoBin.join(' ')}, skipping setup.`);
        return;
    }

    const choice = await vscode.window.showWarningMessage(
        'atopile executable not found. How would you like to proceed?',
        { modal: false },
        'Install Automatically (recommended)',
        'Configure Manually (settings.json)',
    );

    if (choice === 'Configure Manually (settings.json)') {
        await vscode.commands.executeCommand('workbench.action.openSettings', 'atopile.ato');
    } else if (choice === 'Install Automatically (recommended)') {
        await vscode.window.withProgress(
            {
                location: vscode.ProgressLocation.Notification,
                title: 'Setting up atopile',
                cancellable: false,
            },
            async (progress) => {
                const status = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
                context.subscriptions.push(status);

                try {
                    progress.report({ message: 'Downloading and installing uv...' });
                    await downloadAndInstallUv(status);
                    traceInfo('uv installation successful, attempting to install atopile...');
                    progress.report({ message: 'Installing atopile via uv...' });
                    atoBin = await getAtoBin();
                    if (!atoBin) {
                        traceError('Failed to install atopile via uv');
                        vscode.window.showErrorMessage('Failed to install atopile via uv. Please check logs.');
                        return;
                    }
                    // show a message to the user
                    vscode.window.showInformationMessage(`Installed atopile via uv: ${atoBin.join(' ')}`);
                    onDidChangeAtoBinInfoEvent.fire({ init: false });
                } catch (error: any) {
                    traceError(`Failed to install uv: ${error.message}`);
                    vscode.window.showErrorMessage(
                        `Failed to install uv: ${error.message}. Please configure 'atopile.ato' manually or check logs.`,
                    );
                } finally {
                    status.dispose();
                }
            },
        );
    }
}

export function deactivate() {}
