// Copyright (c) Microsoft Corporation. All rights reserved.
// Licensed under the MIT License.

/* eslint-disable @typescript-eslint/explicit-module-boundary-types */
/* eslint-disable @typescript-eslint/no-explicit-any */
import * as fs from 'fs-extra';
import {
    commands,
    ConfigurationScope,
    Disposable,
    LogOutputChannel,
    Uri,
    window,
    workspace,
    WorkspaceConfiguration,
    WorkspaceFolder,
    extensions,
    Extension,
    env,
} from 'vscode';
import { dedent } from './utilities';
import path = require('path');

export function createOutputChannel(name: string): LogOutputChannel {
    return window.createOutputChannel(name, { log: true });
}

export function getConfiguration(config: string, scope?: ConfigurationScope): WorkspaceConfiguration {
    return workspace.getConfiguration(config, scope);
}

export function registerCommand(command: string, callback: (...args: any[]) => any, thisArg?: any): Disposable {
    return commands.registerCommand(command, callback, thisArg);
}

export const { onDidChangeConfiguration } = workspace;

export function isVirtualWorkspace(): boolean {
    const isVirtual = workspace.workspaceFolders && workspace.workspaceFolders.every((f) => f.uri.scheme !== 'file');
    return !!isVirtual;
}

export function getWorkspaceFolders(): readonly WorkspaceFolder[] {
    return workspace.workspaceFolders ?? [];
}

export function getWorkspaceFolder(uri: Uri): WorkspaceFolder | undefined {
    return workspace.getWorkspaceFolder(uri);
}

const vscodeVariables = require('vscode-variables');

export function resolvePath(s: string, workspace?: WorkspaceFolder) {
    // Need to manually resolve workspaceFolder because multiple could be active
    if (workspace) {
        s = s.replace('${workspaceFolder}', workspace.uri.fsPath);
    }
    return vscodeVariables(s);
}

export function getExtension(): Extension<unknown> {
    const extension = extensions.getExtension('atopile.atopile');
    if (!extension) {
        throw new Error('atopile.atopile extension not found');
    }
    return extension;
}

enum IDE_TYPE {
    CURSOR = 'Cursor',
    WINDSURF = 'Windsurf',
    VSCODE_OTHER = 'Code',
}

export function get_ide_type(): IDE_TYPE {
    // Check environment variables to determine IDE type

    const appName = env.appName;

    // Check for Cursor-specific environment variables
    if (appName.includes('Cursor')) {
        return IDE_TYPE.CURSOR;
    }

    // Check for Windsurf-specific environment variables
    if (appName.includes('Windsurf')) {
        return IDE_TYPE.WINDSURF;
    }

    // Default to VS Code if no specific IDE indicators found
    // This is the most common case for our VS Code extension
    return IDE_TYPE.VSCODE_OTHER;
}

export interface LLM_Rule {
    description: string;
    globs: string[];
    alwaysApply: boolean;
    text: string;
}

export function install_rule(name: string, rule: LLM_Rule) {
    /**
     * 1. Determine workspace(s) root
     * 2. Determine rules dirs
     * 3. Check if rule exist (if yes override)
     * 4. Write rule to rules dir
     */
    const TEMPLATE = `
        ---
        description: ${rule.description}
        globs: ${rule.globs.join(', ')}
        alwaysApply: ${rule.alwaysApply}
        ---
        ${rule.text}
    `;
    const rule_text = dedent(TEMPLATE);

    // TODO write to workspace root
    // TODO write to .cursorrules
    // TODO write to .windsurfrules
    // TODO write to .vscode/settings.json
    const dirs: string[] = [];

    for (const p of dirs) {
        const out = path.join(p, `${name}.adc`);
        fs.writeFileSync(out, rule_text);
    }
}

export interface MCP_Config {
    command: string;
    args: string[];
    env: Record<string, string>;
}
export function install_mcp_server(name: string, config: MCP_Config) {
    /**
     * 1. Determine workspace(s) root
     * 2. Determine mcp dirs
     * 3. Load servers
     * 4. Check if server exist (if yes override)
     * 5. Write server to mcp dir
     */

    const current_mcp_config = getConfiguration('mcpServers');
    const new_mcp_config = {
        ...current_mcp_config,
        [name]: config,
    };

    setConfiguration('mcpServers', new_mcp_config);

    // TODO write to .cursorrules
    // TODO write to .windsurfrules
    // TODO write to .vscode/settings.json
}
