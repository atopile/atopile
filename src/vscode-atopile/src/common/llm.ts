import { getAtoBin } from './findbin';
import { loadResource } from './resources';
import { getWorkspaceFolders, install_mcp_server, install_rule } from './vscodeapi';

export async function ask_for_installing_rules_and_mcp_server() {
    const ato_bin = await getAtoBin();
    if (!ato_bin) {
        return;
    }

    const workspaces = getWorkspaceFolders();
    // TODO filter workspaces with ato projects

    //install_rule(
    //    'ato',
    //    {
    //        description: 'ato is a declarative DSL to design electronics (PCBs) with.',
    //        globs: ['*.ato', 'ato.yaml'],
    //        alwaysApply: true,
    //        text: build_rules(),
    //    },
    //    workspaces,
    //);

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
    return content;
}

function _md(file_name: string): string {
    return _read_template(file_name);
}

function _code(file_name: string, type: string): string {
    return `\`\`\`${type}\n${_read_template(file_name)}\n\`\`\``;
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
    `;

    return TEMPLATE;
}
