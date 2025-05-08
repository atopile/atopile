import * as vscode from 'vscode';

/**
 * Check if ato bin is available (see findbin.ts)
 * If not ask user with popup if they want to configure their settings.json or
 * automatically install ato
 *
 * If automatic install:
 *  1. check their platform
 *  2. download the appropriate uv binary from
 *    https://github.com/astral-sh/uv/releases/latest
 *  3. Extract uvx from the package and save it to some vscode folder
 *    (determined by findbin.ts)
 *  4. findbin.ts will detect uvx from now on and run ato with it
 */

export async function activate(context: vscode.ExtensionContext) {
    // TODO:
}

export function deactivate() {}
