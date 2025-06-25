import path = require('path');
import { getExtension } from './vscodeapi';

export function getResourcesPath() {
    let extensionPath = getExtension().extensionUri;
    return path.join(extensionPath.fsPath, 'resources');
}
