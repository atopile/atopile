// Copyright (c) Microsoft Corporation. All rights reserved.
// Licensed under the MIT License.

import { WorkspaceFolder } from 'vscode';
import { getConfiguration, getWorkspaceFolders, resolvePath } from './vscodeapi';
import { SERVER_ID } from './constants';

export interface ISettings {
    cwd: string;
    workspace: string;
    ato: string | undefined;
    from: string | undefined;
    telemetry: boolean | undefined;
}

export function getExtensionSettings(): Promise<ISettings[]> {
    return Promise.all(getWorkspaceFolders().map((w) => getWorkspaceSettings(w)));
}

export async function getWorkspaceSettings(workspace: WorkspaceFolder): Promise<ISettings> {
    const config = getConfiguration(SERVER_ID, workspace.uri);

    const ato_config = config.get<string>(`ato`);
    const workspaceSetting = {
        cwd: workspace.uri.fsPath,
        workspace: workspace.uri.toString(),
        ato: ato_config ? resolvePath(ato_config, workspace) : undefined,
        from: config.get<string>(`from`),
        telemetry: config.get<boolean>(`telemetry`),
    };
    return workspaceSetting;
}
