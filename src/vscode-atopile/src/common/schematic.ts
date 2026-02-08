import * as vscode from 'vscode';
import { getBuildTarget } from '../common/target';
import { Build } from './manifest';
import * as fs from 'fs';
import * as path from 'path';
import { FileResource, FileResourceWatcher } from './file-resource-watcher';

export interface Schematic extends FileResource {}

class SchematicWatcher extends FileResourceWatcher<Schematic> {
    constructor() {
        super('Schematic');
    }

    protected getResourceForBuild(build: Build | undefined): Schematic | undefined {
        if (!build?.entry) {
            return undefined;
        }

        const jsonPath = path.join(build.root, 'build', 'builds', build.name, build.name + '.schematic.json');
        return { path: jsonPath, exists: fs.existsSync(jsonPath) };
    }
}

const schematicWatcher = new SchematicWatcher();

export const onSchematicChanged = schematicWatcher.onChanged;

export function getCurrentSchematic(): Schematic | undefined {
    return schematicWatcher.getCurrent();
}

export function getSchematicForBuild(buildTarget?: Build | undefined): Schematic | undefined {
    const build = buildTarget || getBuildTarget();
    return schematicWatcher['getResourceForBuild'](build);
}

export async function activate(context: vscode.ExtensionContext) {
    await schematicWatcher.activate(context);
}

export function deactivate() {
    schematicWatcher.deactivate();
}
