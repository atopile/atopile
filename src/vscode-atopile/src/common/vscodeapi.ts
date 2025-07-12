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
import { traceInfo } from './log/logging';

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

export async function getWorkspaceFoldersWithFile(glob: string): Promise<readonly WorkspaceFolder[]> {
    /**
     * Find all files in open workspaces that match the filename
     * Determine the workspace folder for each file
     */

    const files = await workspace.findFiles(glob, '**/.*/**');
    const workspace_folders = new Set<WorkspaceFolder>();

    for (const file of files) {
        const folder = getWorkspaceFolder(file);
        if (!folder) {
            continue;
        }
        workspace_folders.add(folder);
    }

    return Array.from(workspace_folders);
}

export async function getAtopileWorkspaceFolders(): Promise<readonly WorkspaceFolder[]> {
    return await getWorkspaceFoldersWithFile('**/ato.yaml');
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
export interface MCP_Config {
    command: string;
    args: string[];
    env: Record<string, string>;
}

interface LLM_Rule_Host {
    get_rule_path(name: string): string;
    build_rule(rule: LLM_Rule): string;
}

interface MCP_Host {
    insert_mcp(name: string, mcp_config: MCP_Config, workspace_folder: WorkspaceFolder): void;
}

class Cursor implements LLM_Rule_Host, MCP_Host {
    get_rule_path(name: string): string {
        return `\${workspaceFolder}/.cursor/rules/${name}.mdc`;
    }
    build_rule(rule: LLM_Rule): string {
        return (
            dedent(
                `
            ---
            description: ${rule.description}
            globs: ${rule.globs.join(', ')}
            alwaysApply: ${rule.alwaysApply}
            ---
        `,
            ) +
            '\n' +
            rule.text
        );
    }

    get_mcp_path(_: string): string {
        return `\${workspaceFolder}/.cursor/mcp.json`;
    }

    insert_mcp(name: string, mcp_config: MCP_Config, workspace_folder: WorkspaceFolder): void {
        const config_path = resolvePath(this.get_mcp_path(name), workspace_folder);
        if (!fs.existsSync(config_path)) {
            fs.mkdirSync(path.dirname(config_path), { recursive: true });
            fs.writeJsonSync(config_path, { mcpServers: {} });
        }
        // load .cursor/mcp.json
        const config = fs.readJsonSync(config_path);

        if (!config.mcpServers) {
            config.mcpServers = {};
        }

        // add to mcp.json
        config.mcpServers[name] = mcp_config;

        // save .cursor/mcp.json
        // write pretty json
        traceInfo(`Writing Cursor mcp.json to ${config_path}`);
        fs.writeJsonSync(config_path, config, { spaces: 4 });
    }
}

class ClaudeCode implements LLM_Rule_Host, MCP_Host {
    get_rule_path(_: string): string {
        return `\${workspaceFolder}/CLAUDE.md`;
    }

    build_rule(rule: LLM_Rule): string {
        return '# CLAUDE.md' + '\n\n' + rule.text;
    }

    get_mcp_path(_: string): string {
        return `\${workspaceFolder}/.mcp.json`;
    }

    insert_mcp(name: string, mcp_config: MCP_Config, workspace_folder: WorkspaceFolder): void {
        const config_path = resolvePath(this.get_mcp_path(name), workspace_folder);
        if (!fs.existsSync(config_path)) {
            fs.mkdirSync(path.dirname(config_path), { recursive: true });
            fs.writeJsonSync(config_path, { mcpServers: {} });
        }

        // load .mcp.json
        const config = fs.readJsonSync(config_path);

        if (!config.mcpServers) {
            config.mcpServers = {};
        }

        // add to mcp.json
        config.mcpServers[name] = mcp_config;

        // save .mcp.json
        // write pretty json
        traceInfo(`Writing Claude .mcp.json to ${config_path}`);
        fs.writeJsonSync(config_path, config, { spaces: 4 });
    }
}

class Windsurf implements LLM_Rule_Host {
    get_rule_path(name: string): string {
        return `\${workspaceFolder}/.windsurf/rules/${name}.md`;
    }

    build_rule(rule: LLM_Rule): string {
        return (
            dedent(
                `
            ---
            description: ${rule.description}
            globs: ${rule.globs.join(', ')}
            alwaysApply: ${rule.alwaysApply}
            ---
        `,
            ) +
            '\n' +
            rule.text
        );
    }

    // MCP no support for http: https://docs.windsurf.com/windsurf/cascade/mcp
}

class Copilot implements LLM_Rule_Host {
    get_rule_path(name: string): string {
        return `\${workspaceFolder}/.github/instructions/${name}.instructions.md`;
    }

    build_rule(rule: LLM_Rule): string {
        return (
            dedent(
                `
            ---
            description: ${rule.description}
            applyTo: ${rule.globs.join(', ')}
            ---
        `,
            ) +
            '\n' +
            rule.text
        );
    }

    // MCP is in preview atm: https://code.visualstudio.com/docs/copilot/chat/mcp-servers
}

const rule_hosts: Record<string, LLM_Rule_Host> = {
    cursor: new Cursor(),
    windsurf: new Windsurf(),
    copilot: new Copilot(),
    claude: new ClaudeCode(),
};

const mcp_hosts: Record<string, MCP_Host> = {
    cursor: new Cursor(),
    claude: new ClaudeCode(),
};

export function install_rule(
    name: string,
    rule: LLM_Rule,
    workspaces: readonly WorkspaceFolder[] | undefined = undefined,
) {
    const workspace_folders = workspaces || getWorkspaceFolders();

    for (const workspace of workspace_folders) {
        for (const [_, host] of Object.entries(rule_hosts)) {
            const rel_path = host.get_rule_path(name);
            const full_path = resolvePath(rel_path, workspace);
            traceInfo(`Installing rule ${name} to ${full_path}`);

            const dir = path.dirname(full_path);
            fs.mkdirSync(dir, { recursive: true });
            fs.writeFileSync(full_path, host.build_rule(rule));
        }
    }
}

export function install_mcp_server(
    name: string,
    config: MCP_Config,
    workspaces: readonly WorkspaceFolder[] | undefined = undefined,
) {
    const workspace_folders = workspaces || getWorkspaceFolders();

    for (const workspace_folder of workspace_folders) {
        for (const [_, host] of Object.entries(mcp_hosts)) {
            host.insert_mcp(name, config, workspace_folder);
        }
    }
}
