import { StatusBarItem, window as vscodeWindow, ProgressLocation } from 'vscode';
import axios from 'axios';
import * as fs from 'fs';
import { promises as fsPromises } from 'fs';
import * as path from 'path';
import * as decompress from 'decompress'; // Handles .zip, .tar.gz, etc.
import { traceInfo, traceError } from './log/logging';

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
            await fsPromises.mkdir(outputDir, { recursive: true });
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

        await fsPromises.writeFile(outpath, targetFile.data, { mode: targetFile.mode });
        // If executable permission is important, you might need to explicitly set it for non-Windows
        if (process.platform !== 'win32' && targetFile.mode & 0o111) {
            // Check for any execute bit
            await fsPromises.chmod(outpath, targetFile.mode); // Use original mode
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

export async function downloadAndExtractRepoSubfolder(
    repo: string, // e.g., "owner/repository"
    ref: string | null, // branch, tag, or commit hash. null for default branch.
    subfolderInRepo: string, // e.g., "examples/project"
    destinationPath: string, // Full path to extract the subfolder's contents
): Promise<void> {
    const repoName = repo.split('/')[1] || 'repository';

    await vscodeWindow.withProgress(
        {
            location: ProgressLocation.Notification,
            title: `Fetching ${repoName} Data`,
            cancellable: false,
        },
        async (progress) => {
            progress.report({ increment: 0, message: 'Initializing...' });

            try {
                const zipballUrl = `https://api.github.com/repos/${repo}/zipball/${ref || ''}`;
                traceInfo(`Constructed zipball URL: ${zipballUrl}`);

                progress.report({ increment: 20, message: `Downloading ${repoName} archive...` });
                traceInfo(`Downloading archive from ${zipballUrl} for ${subfolderInRepo}`);
                const response = await axios.get(zipballUrl, {
                    responseType: 'arraybuffer',
                    // GitHub API might rate limit unauthenticated requests.
                    // For higher limits, a token might be needed in headers.
                    // headers: { 'Authorization': 'token YOUR_GITHUB_TOKEN' }
                });
                const archiveBuffer = Buffer.from(response.data);
                traceInfo(`Archive downloaded, size: ${archiveBuffer.length} bytes.`);

                progress.report({ increment: 30, message: `Extracting ${subfolderInRepo}...` });
                traceInfo(`Ensuring destination directory exists: ${destinationPath}`);
                if (!fs.existsSync(destinationPath)) {
                    await fsPromises.mkdir(destinationPath, { recursive: true });
                    traceInfo(`Created destination directory: ${destinationPath}`);
                }

                const files = await decompress(archiveBuffer);
                traceInfo(`Decompressed archive, found ${files.length} files/folders.`);

                let rootDirInZip = '';
                if (files.length > 0) {
                    const firstPath = files[0].path.replace(/\\\\/g, '/');
                    const slashIndex = firstPath.indexOf('/');
                    if (slashIndex !== -1) {
                        rootDirInZip = firstPath.substring(0, slashIndex + 1);
                    } else if (files.some((f) => f.path.includes('/'))) {
                        // Fallback: if no slash in first path, but others have, implies flat structure
                        // This case shouldn't happen for GitHub zips but is a safeguard.
                        rootDirInZip = '';
                    } else {
                        // It might be that the first entry is a file in a flat zip.
                        // Or it's a single folder zip and firstPath is the folder name without trailing slash.
                        // For GitHub zips, firstPath is typically "owner-repo-commitsha/"
                        // If firstPath has no slash, but it's a directory type, append one.
                        if (files[0].type === 'directory' && !firstPath.endsWith('/')) {
                            rootDirInZip = firstPath + '/';
                        } else {
                            // If still no clear root, assume files are at top level of zip effectively
                            rootDirInZip = '';
                        }
                    }
                }

                if (rootDirInZip === '' && files.length > 0 && files[0].path.split('/').length > 1) {
                    // More robust way to get the root dir based on first file path
                    // e.g. atopile-atopile-026a58f/README.md -> atopile-atopile-026a58f/
                    const parts = files[0].path.replace(/\\\\/g, '/').split('/');
                    if (parts.length > 1) {
                        rootDirInZip = parts[0] + '/';
                    }
                }
                traceInfo(`Determined root directory in zip: '${rootDirInZip}'`);

                const PURE_SUBFOLDER_IN_REPO = subfolderInRepo.replace(/\\\\/g, '/').replace(/^\/|\/$/g, ''); // remove leading/trailing slashes
                const subfolderPrefixInZip = path.posix.join(rootDirInZip, PURE_SUBFOLDER_IN_REPO);
                // Ensure prefix ends with a slash if subfolderInRepo is not empty
                const effectivePrefix = PURE_SUBFOLDER_IN_REPO
                    ? subfolderPrefixInZip.endsWith('/')
                        ? subfolderPrefixInZip
                        : subfolderPrefixInZip + '/'
                    : rootDirInZip;

                traceInfo(`Looking for files with prefix: '${effectivePrefix}'`);

                let foundFiles = false;
                for (const file of files) {
                    const normalizedFilePath = file.path.replace(/\\\\/g, '/');
                    if (file.type === 'file' && normalizedFilePath.startsWith(effectivePrefix)) {
                        foundFiles = true;
                        const relativePath = normalizedFilePath.substring(effectivePrefix.length);
                        if (relativePath.startsWith('/')) {
                            // Should not happen if prefix and path are correct
                            traceError(`Unexpected leading slash in relativePath: ${relativePath}`);
                            continue;
                        }
                        const targetFilePath = path.join(destinationPath, relativePath);
                        const targetFileDir = path.dirname(targetFilePath);

                        if (!fs.existsSync(targetFileDir)) {
                            await fsPromises.mkdir(targetFileDir, { recursive: true });
                        }
                        await fsPromises.writeFile(targetFilePath, file.data, { mode: file.mode });
                        if (process.platform !== 'win32' && file.mode & 0o111) {
                            await fsPromises.chmod(targetFilePath, file.mode);
                        }
                    }
                }

                if (!foundFiles) {
                    const availablePaths = files
                        .slice(0, 10)
                        .map((f) => f.path)
                        .join(', ');
                    traceError(
                        `No files found with prefix '${effectivePrefix}'. Available paths sample: ${availablePaths}`,
                    );
                    throw new Error(
                        `Subfolder '${subfolderInRepo}' not found or empty in the archive. Prefix used: '${effectivePrefix}'.`,
                    );
                }

                traceInfo(`Successfully extracted ${subfolderInRepo} to ${destinationPath}`);
                progress.report({ increment: 50, message: 'Extraction complete.' });
            } catch (error: any) {
                traceError(`[github] Failed to download/extract ${subfolderInRepo}:`, error);
                const errorMessage = error instanceof Error ? error.message : String(error);
                // The progress window will be closed by VS Code on error automatically
                // Re-throw to be caught by the caller
                throw new Error(`Failed to download or extract '${subfolderInRepo}': ${errorMessage}`);
            }
        },
    );
}

// Minimal interface for GitHub content API response items
interface GitHubFile {
    type: 'file' | 'dir' | 'symlink' | 'submodule';
    name: string;
    path: string;
    sha: string;
    url: string;
    git_url: string | null;
    html_url: string | null;
    download_url: string | null;
    // ... other fields are available but not needed for this function
}

export async function listDirectoriesInRepoSubfolder(
    repo: string, // e.g., "owner/repository"
    ref: string | null, // branch, tag, or commit hash. null for default branch.
    subfolderInRepo: string,
): Promise<string[]> {
    const subfolderPath = subfolderInRepo.replace(/^\/|\/$/g, ''); // Remove leading/trailing slashes
    let apiUrl = `https://api.github.com/repos/${repo}/contents/${subfolderPath}`;
    if (ref) {
        apiUrl += `?ref=${ref}`;
    }

    traceInfo(`[github] Listing directories in ${repo}/${subfolderPath}${ref ? `@${ref}` : ''} using URL: ${apiUrl}`);

    try {
        const response = await axios.get<GitHubFile[] | GitHubFile>(apiUrl, {
            // Response can be array or single file object
            headers: { Accept: 'application/vnd.github.v3+json' },
        });

        if (Array.isArray(response.data)) {
            const fileNames = response.data.filter((item) => item.type === 'dir').map((item) => item.name);
            traceInfo(`[github] Found ${fileNames.length} directories in ${repo}/${subfolderPath}.`);
            return fileNames;
        } else if (response.data && typeof response.data === 'object' && (response.data as GitHubFile).type === 'dir') {
            // If the path points directly to a single file, GitHub API returns a single object, not an array.
            traceInfo(
                `[github] Path ${repo}/${subfolderPath} points directly to a directory: ${(response.data as GitHubFile).name}`,
            );
            return [(response.data as GitHubFile).name];
        } else {
            // This case might occur if the path is a directory but somehow doesn't return an array,
            // or if it's an unexpected response type.
            traceError(
                `[github] Expected an array of files or a single file object from ${apiUrl}, but got:`,
                response.data,
            );
            throw new Error(
                `Invalid response structure from GitHub API for ${subfolderPath}. Expected an array or a file object.`,
            );
        }
    } catch (error: any) {
        traceError(`[github] Failed to list directories in ${repo}/${subfolderPath}:`, error);
        const message = error.response?.data?.message || error.message || 'Unknown error';
        if (error.response?.status === 404) {
            throw new Error(`Subfolder or file '${subfolderPath}' not found in repository '${repo}'.`);
        }
        throw new Error(`Failed to list directories in '${subfolderPath}': ${message}`);
    }
}
