/**
 * Tree visualizer webview for Power Tree and I2C Tree views.
 *
 * Loads the React-based tree viewer from the ui-server build output.
 * Data is passed via window.__TREE_VIEWER_CONFIG__ with a webview URI to the JSON file.
 *
 * Production: loads from resources/webviews/tree-viewer.html
 * Development: loads from ui-server/dist/tree-viewer.html
 */

import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { getCurrentPowerTree, onPowerTreeChanged } from '../common/power-tree';
import { getCurrentI2CTree, onI2CTreeChanged } from '../common/i2c-tree';
import { BaseWebview } from './webview-base';

/**
 * Locate the tree-viewer dist directory.
 * Checks two places:
 *   1. resources/webviews/ (production / packaged extension)
 *   2. ui-server/dist/ (development)
 */
function getTreeViewerDistPath(): string | null {
    const extensionPath = vscode.extensions.getExtension('atopile.atopile')?.extensionUri?.fsPath;

    if (extensionPath) {
        // Production: webviews are built into resources/webviews/
        const prodPath = path.join(extensionPath, 'resources', 'webviews');
        if (fs.existsSync(path.join(prodPath, 'tree-viewer.html'))) {
            return prodPath;
        }
    }

    // Development: use ui-server dist directly
    for (const folder of vscode.workspace.workspaceFolders ?? []) {
        const devPath = path.join(folder.uri.fsPath, 'src', 'ui-server', 'dist');
        if (fs.existsSync(path.join(devPath, 'tree-viewer.html'))) {
            return devPath;
        }
    }

    return null;
}

type TreeType = 'power' | 'i2c';

class TreeVisualizerWebview extends BaseWebview {
    private treeType: TreeType;

    constructor(treeType: TreeType) {
        const label = treeType === 'power' ? 'Power Tree' : 'I2C Tree';
        super({
            id: `${treeType}_tree_preview`,
            title: label,
        });
        this.treeType = treeType;
    }

    protected getHtmlContent(webview: vscode.Webview): string {
        const distPath = getTreeViewerDistPath();
        if (!distPath) {
            return this.getMissingResourceHtml('Tree Viewer (not built)');
        }

        // Get the JSON data file for the current build
        const resource = this.treeType === 'power'
            ? getCurrentPowerTree()
            : getCurrentI2CTree();

        if (!resource || !resource.exists) {
            return this.getMissingResourceHtml(
                this.treeType === 'power' ? 'Power Tree' : 'I2C Tree'
            );
        }

        const indexHtmlPath = path.join(distPath, 'tree-viewer.html');
        let html = fs.readFileSync(indexHtmlPath, 'utf-8');

        // Rewrite asset paths to webview URIs
        const distUri = webview.asWebviewUri(vscode.Uri.file(distPath));
        const dataUri = this.getWebviewUri(webview, resource.path);

        // Replace relative asset paths with webview URIs
        html = html.replace(/(href|src)="\.\/assets\//g, `$1="${distUri}/assets/`);
        html = html.replace(/(href|src)="\/assets\//g, `$1="${distUri}/assets/`);
        html = html.replace(/(href|src)="\.\/treeViewer\./g, `$1="${distUri}/treeViewer.`);
        html = html.replace(/(href|src)="\/treeViewer\./g, `$1="${distUri}/treeViewer.`);

        // Also handle the entry JS in dev mode
        html = html.replace(/src="\.\/src\/treeViewer\.tsx"/g, `src="${distUri}/treeViewer.js"`);

        // Inject data URL and type as a script before the closing </head>
        const configScript = `
            <script>
                window.__TREE_VIEWER_CONFIG__ = {
                    type: "${this.treeType}",
                    dataUrl: "${dataUri.toString()}"
                };
            </script>
        `;
        html = html.replace('</head>', `${configScript}</head>`);

        return html;
    }

    protected getLocalResourceRoots(): vscode.Uri[] {
        const roots = super.getLocalResourceRoots();
        const distPath = getTreeViewerDistPath();
        if (distPath) {
            roots.push(vscode.Uri.file(distPath));
        }
        // Also allow access to the build output directory
        const resource = this.treeType === 'power'
            ? getCurrentPowerTree()
            : getCurrentI2CTree();
        if (resource && fs.existsSync(resource.path)) {
            roots.push(vscode.Uri.file(path.dirname(resource.path)));
        }
        return roots;
    }
}

let powerTreeViewer: TreeVisualizerWebview | undefined;
let i2cTreeViewer: TreeVisualizerWebview | undefined;

export async function openPowerTreePreview() {
    if (!powerTreeViewer) {
        powerTreeViewer = new TreeVisualizerWebview('power');
    }
    await powerTreeViewer.open();
}

export async function openI2CTreePreview() {
    if (!i2cTreeViewer) {
        i2cTreeViewer = new TreeVisualizerWebview('i2c');
    }
    await i2cTreeViewer.open();
}

export function closePowerTreePreview() {
    powerTreeViewer?.dispose();
    powerTreeViewer = undefined;
}

export function closeI2CTreePreview() {
    i2cTreeViewer?.dispose();
    i2cTreeViewer = undefined;
}

export async function activate(context: vscode.ExtensionContext) {
    context.subscriptions.push(
        onPowerTreeChanged((_) => {
            if (powerTreeViewer?.isOpen()) {
                openPowerTreePreview();
            }
        }),
        onI2CTreeChanged((_) => {
            if (i2cTreeViewer?.isOpen()) {
                openI2CTreePreview();
            }
        }),
    );
}

export function deactivate() {
    closePowerTreePreview();
    closeI2CTreePreview();
}
