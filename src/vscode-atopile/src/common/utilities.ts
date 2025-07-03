// Copyright (c) Microsoft Corporation. All rights reserved.
// Licensed under the MIT License.

import * as fs from 'fs-extra';
import * as path from 'path';
import { LogLevel, Uri, WorkspaceFolder } from 'vscode';
import { Trace } from 'vscode-jsonrpc/node';
import { getWorkspaceFolders } from './vscodeapi';

function logLevelToTrace(logLevel: LogLevel): Trace {
    switch (logLevel) {
        case LogLevel.Error:
        case LogLevel.Warning:
            return Trace.Off; // Only application error/warning logs, no LSP message tracing

        case LogLevel.Info:
            return Trace.Off; // Only application info logs, no LSP message tracing

        case LogLevel.Debug:
            return Trace.Messages; // Application debug logs + LSP message tracing

        case LogLevel.Trace:
            return Trace.Verbose; // Application trace logs + verbose LSP message tracing

        case LogLevel.Off:
        default:
            return Trace.Off;
    }
}

export function getLSClientTraceLevel(channelLogLevel: LogLevel, globalLogLevel: LogLevel): Trace {
    if (channelLogLevel === LogLevel.Off) {
        return logLevelToTrace(globalLogLevel);
    }
    if (globalLogLevel === LogLevel.Off) {
        return logLevelToTrace(channelLogLevel);
    }
    const level = logLevelToTrace(channelLogLevel <= globalLogLevel ? channelLogLevel : globalLogLevel);
    return level;
}

export async function getProjectRoot(): Promise<WorkspaceFolder> {
    const workspaces: readonly WorkspaceFolder[] = getWorkspaceFolders();
    if (workspaces.length === 0) {
        return {
            uri: Uri.file(process.cwd()),
            name: path.basename(process.cwd()),
            index: 0,
        };
    } else if (workspaces.length === 1) {
        return workspaces[0];
    } else {
        let rootWorkspace = workspaces[0];
        let root = undefined;
        for (const w of workspaces) {
            if (await fs.pathExists(w.uri.fsPath)) {
                root = w.uri.fsPath;
                rootWorkspace = w;
                break;
            }
        }

        for (const w of workspaces) {
            if (root && root.length > w.uri.fsPath.length && (await fs.pathExists(w.uri.fsPath))) {
                root = w.uri.fsPath;
                rootWorkspace = w;
            }
        }
        return rootWorkspace;
    }
}

export function disambiguatePaths(iterable: Iterable<any>, path_key: (item: any) => string): Record<string, any> {
    /**
     * Disambiguate paths by attaching prefixes until unique
     * Returns map of unique path to original object
     *
     * Examples:
     * - ['/bla/foo/bar', '/bla/foo/baz'] => ['bar', 'baz']
     * - ['/bla/foo/bar', '/bla/baz/bar'] => ['foo/bar', 'baz/bar']
     * - ['/bla/foo/bar', '/baz/foo/bar'] => ['bla/foo/bar', 'baz/foo/bar']
     * - ['/bla/foo/bar', '/bla/foo/bar'] => error
     */
    const items = Array.from(iterable);
    const pathToItem = new Map<string, any>();

    // Extract paths and check for duplicates
    for (const item of items) {
        const path = path_key(item);
        if (pathToItem.has(path)) {
            throw new Error(`Duplicate path found: ${path}`);
        }
        pathToItem.set(path, item);
    }

    const paths = Array.from(pathToItem.keys());

    if (paths.length === 0) {
        return {};
    }

    // Split paths into segments, filtering out empty segments
    const pathSegments = paths.map((path) => path.split('/').filter((segment) => segment !== ''));

    const result: Record<string, any> = {};

    // For each path, find the minimal suffix that makes it unique
    for (let i = 0; i < paths.length; i++) {
        const currentPath = paths[i];
        const currentSegments = pathSegments[i];

        // Try different suffix lengths starting from 1
        for (let suffixLength = 1; suffixLength <= currentSegments.length; suffixLength++) {
            const suffix = currentSegments.slice(-suffixLength).join('/');

            // Check if this suffix is unique among all other paths
            let isUnique = true;
            for (let j = 0; j < paths.length; j++) {
                if (i === j) continue;

                const otherSegments = pathSegments[j];
                const otherSuffix = otherSegments.slice(-suffixLength).join('/');

                if (suffix === otherSuffix) {
                    isUnique = false;
                    break;
                }
            }

            if (isUnique) {
                result[suffix] = pathToItem.get(currentPath);
                break;
            }
        }
    }

    return result;
}

export function dedent(input_string: string, remove_first_line: boolean = true): string {
    /**
     * Determine common indentation of all non-empty lines
     * Remove that indentation from all lines
     * Return the dedented string
     */
    const lines = input_string.split('\n');
    if (remove_first_line && lines.length > 0 && lines[0].trim().length === 0) {
        lines.shift();
    }

    const non_empty_lines = lines.filter((line) => line.trim().length > 0);

    if (non_empty_lines.length === 0) {
        return input_string;
    }

    const min_indent = Math.min(...non_empty_lines.map((line) => line.match(/^\s*/)?.[0]?.length ?? 0));

    return lines.map((line) => line.slice(min_indent)).join('\n');
}

export function indent(input_string: string, indent: number, skip_first: boolean = true): string {
    return input_string
        .split('\n')
        .map((line, index) => (index === 0 && skip_first ? line : ' '.repeat(indent) + line))
        .join('\n');
}
