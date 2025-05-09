import { StatusBarItem } from 'vscode';
import axios from 'axios';
import * as fs from 'fs';
import * as path from 'path';
import * as decompress from 'decompress'; // Handles .zip, .tar.gz, etc.
import { traceInfo } from './log/logging';

// Define a simple type for the GitHub Asset if not available elsewhere
interface GitHubAsset {
    name: string;
    browser_download_url: string;
}

// Define a simple type for the GitHub Release if not available elsewhere
interface GitHubRelease {
    assets: GitHubAsset[];
    tag_name: string;
}

export interface PlatformArch {
    platform: string;
    arch: string;
}

export async function downloadReleaseAssetBin(
    repo: string, // e.g., "owner/repository"
    outpath: string, // Full path to save the extracted innerPath file
    binName: string, // Path inside the archive to extract
    get_platform_arch_from_name: (name: string) => PlatformArch | null,
    status: StatusBarItem,
): Promise<void> {
    traceInfo(`Downloading ${repo} release asset ${binName} to ${outpath}`);
    status.text = `$(sync~spin) Fetching ${repo} release...`;
    status.show();

    if (process.platform === 'win32') {
        binName += '.exe';
    }

    try {
        // 1. Determine current system platform and architecture
        // Node's process.platform: 'darwin', 'freebsd', 'linux', 'openbsd', 'win32', 'android', 'cygwin', 'sunos'
        // Node's process.arch: 'arm', 'arm64', 'ia32', 'mips', 'mipsel', 'ppc', 'ppc64', 's390', 's390x', 'x32', 'x64'
        const currentPlatform = process.platform;
        const currentArch = process.arch;

        // 2. Use GitHub API to get the latest release
        const releaseUrl = `https://api.github.com/repos/${repo}/releases/latest`;
        const releaseResponse = await axios.get<GitHubRelease>(releaseUrl, {
            headers: { Accept: 'application/vnd.github.v3+json' },
        });
        const release = releaseResponse.data;

        if (!release || !release.assets || release.assets.length === 0) {
            throw new Error(`No assets found in the latest release of ${repo}`);
        }

        // 3. Look at each asset name, extract platform/arch, and find a match
        let matchedAsset: GitHubAsset | undefined;
        for (const asset of release.assets) {
            const assetPlatformArch = get_platform_arch_from_name(asset.name);
            if (!assetPlatformArch) {
                continue;
            }

            if (assetPlatformArch.platform === currentPlatform && assetPlatformArch.arch === currentArch) {
                matchedAsset = asset;
                break;
            }
        }

        if (!matchedAsset) {
            throw new Error(
                `No suitable asset found for platform ${currentPlatform} and architecture ${currentArch} in ${repo}@${release.tag_name}. ` +
                    `Available assets: ${release.assets.map((a) => a.name).join(', ')}`,
            );
        }

        traceInfo(`Downloading ${matchedAsset.name}...`);
        status.text = `$(cloud-download) Downloading ${matchedAsset.name}...`;

        // 4. Download the matched asset
        const assetDownloadUrl = matchedAsset.browser_download_url;
        const assetResponse = await axios.get(assetDownloadUrl, {
            responseType: 'arraybuffer', // Get data as a Buffer
        });
        const assetBuffer = Buffer.from(assetResponse.data);

        traceInfo(`Extracting ${binName}...`);
        status.text = `$(archive) Extracting ${binName}...`;

        // 5. Extract innerPath from the downloaded archive to outpath
        // Ensure output directory exists
        const outputDir = path.dirname(outpath);
        if (!fs.existsSync(outputDir)) {
            await fs.promises.mkdir(outputDir, { recursive: true });
        }

        // Decompress and find the specific file
        // `decompress` returns an array of {data: Buffer, mode: Number, mtime: Date, path: String, type: String}
        const decompressedFiles = await decompress(assetBuffer);

        const targetFile = decompressedFiles.find((file) => {
            return path.basename(file.path) === binName && file.type === 'file';
        });

        if (!targetFile) {
            // print filenames in the archive
            traceInfo(`Filenames in the archive: ${decompressedFiles.map((f) => f.path).join(', ')}`);
            throw new Error(`File '${binName}' not found in the archive ${matchedAsset.name}.`);
        }

        await fs.promises.writeFile(outpath, targetFile.data, { mode: targetFile.mode });
        // If executable permission is important, you might need to explicitly set it for non-Windows
        if (process.platform !== 'win32' && targetFile.mode & 0o111) {
            // Check for any execute bit
            await fs.promises.chmod(outpath, targetFile.mode); // Use original mode
        }

        traceInfo(`${path.basename(outpath)} downloaded and extracted.`);
        status.text = `$(check) ${path.basename(outpath)} downloaded and extracted.`;
        // Consider hiding status after a short delay or let the caller manage it
        setTimeout(() => {
            if (status.text.startsWith('$(check)')) {
                // Only hide if it's our success message
                status.hide();
            }
        }, 5000);
    } catch (error: any) {
        console.error('Failed to download or extract release asset:', error);
        const message = error instanceof Error ? error.message : String(error);
        status.text = `$(error) Failed: ${message.substring(0, 100)}`; // Keep message short
        // Don't hide on error immediately, let user see it.
        // The caller should probably handle more detailed error display (e.g. vscode.window.showErrorMessage)
        throw error; // Re-throw for the caller to handle
    }
    // `finally` block is not strictly needed if status.hide() is managed on success/error path or by caller
}
