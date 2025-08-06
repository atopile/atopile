import path = require('path');
import * as fs from 'fs-extra';
import { getExtension } from './vscodeapi';

export function getResourcesPath() {
    let extensionPath = getExtension().extensionUri;
    return path.join(extensionPath.fsPath, 'resources');
}

export function getAndCheckResource(rel_path: string) {
    const root = getResourcesPath();
    const full_path = path.join(root, rel_path);
    if (!fs.existsSync(full_path)) {
        throw new Error(`Resource ${rel_path} not found in ${full_path}`);
    }
    return full_path;
}

export function loadResource(rel_path: string) {
    const full_path = getAndCheckResource(rel_path);
    return fs.readFileSync(full_path, 'utf8');
}
