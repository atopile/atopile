import * as vscode from 'vscode';
import { getAtoBin } from './findbin';
import { traceInfo } from './log/logging';
import { loadResource } from './resources';
import { dedent, indent } from './utilities';
import { getAtopileWorkspaceFolders, install_mcp_server, install_rule } from './vscodeapi';

export async function llm_setup_rules_and_mcp_server() {
    const ato_bin = await getAtoBin();
    if (!ato_bin) {
        return;
    }

    const workspaces = await getAtopileWorkspaceFolders();

    traceInfo('Installing ato rule');
    install_rule(
        'ato',
        {
            description: 'ato is a declarative DSL to design electronics (PCBs) with.',
            globs: ['*.ato', 'ato.yaml'],
            alwaysApply: true,
            text: build_rules(),
        },
        workspaces,
    );

    traceInfo('Installing atopile MCP server');
    install_mcp_server(
        'atopile',
        {
            command: ato_bin.command[0],
            args: [...ato_bin.command.slice(1), 'mcp', 'start', '--no-http'],
            env: {},
        },
        workspaces,
    );
}

function _read_template(file_name: string): string {
    const content = loadResource(`templates/rules/${file_name}`);
    // indenting with 8 to bring to same level as first line
    // where its being inserted
    return indent(content, 8, true);
}

function _md(file_name: string): string {
    return _read_template(file_name);
}

function _code(file_name: string, type: string): string {
    // indenting with 8 to bring to same level as first line
    // where its being inserted
    return `\`\`\`${type}\n        ${_read_template(file_name)}\n        \`\`\``;
}

function _ato(file_name: string): string {
    return _code(file_name, 'ato');
}

function build_rules() {
    const TEMPLATE = `
        ato is a declarative DSL to design electronics (PCBs) with.
        It is part of the atopile project.
        Atopile is run by the vscode/cursor/windsurf extension.
        The CLI (which is invoked by the extension) actually builds the project.

        ${_md('negative.md')}

        # Ato Syntax

        ato sytax is heavily inspired by Python, but fully declarative.
        ato thus has no procedural code, and no side effects.

        ## Examples of syntax

        ${_ato('syntax.ato')}

        ## G4 Grammar

        ${_code('grammar.g4', 'g4')}

        # Most used library modules/interfaces (api of them)

        ${_ato('common.ato')}

        For the rest use the atopile MCP server 
        - \`get_library_interfaces\` to list interfaces
        - \`get_library_modules\` to list modules
        - \`inspect_library_module_or_interface\` to inspect the code

        ${_md('ato.md')}

        # Creating a package

        ${_md('create_package.md')}

        # Vibe coding a project
        
        If the user gives you high level description of the project, use the following guide:

        ${_md('vibe_electronics.md')}

    `;

    return dedent(TEMPLATE);
}

export async function activate(context: vscode.ExtensionContext) {
    // on-startup
    await llm_setup_rules_and_mcp_server();

    context.subscriptions.push(
        // on-command
        vscode.commands.registerCommand('atopile.llm.setup', llm_setup_rules_and_mcp_server),
        // if workspace folder added
        vscode.workspace.onDidChangeWorkspaceFolders(async () => {
            await llm_setup_rules_and_mcp_server();
        }),
        // if ato.yaml created
        vscode.workspace.onDidCreateFiles(async (e) => {
            if (e.files.some((f) => f.fsPath.endsWith('ato.yaml'))) {
                await llm_setup_rules_and_mcp_server();
            }
        }),
    );
}
