import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { onThreeDModelChanged, getCurrentThreeDModel } from '../common/3dmodel';
import { BaseWebview } from './webview-base';
import { buildHtml } from './html-builder';
import { getAndCheckResource, getResourcesPath } from '../common/resources';

class ModelViewerWebview extends BaseWebview {
    constructor() {
        super({
            id: 'modelviewer_preview',
            title: '3D Model',
            iconName: 'cube-icon.svg',
        });
    }

    protected getHtmlContent(webview: vscode.Webview): string {
        const model = getCurrentThreeDModel();
        if (!model || !fs.existsSync(model.path)) {
            return this.getMissingResourceHtml('3D Model');
        }

        const scriptUri = this.getModelViewerScriptUri(webview);
        const modelWebUri = this.getWebviewUri(webview, model.path);

        return buildHtml({
            title: '3D Model Preview',
            scripts: [{ type: 'module', src: scriptUri.toString() }],
            styles: `
                #container {height: 100%; width: 100%;}
                model-viewer {height: 100%; width: 100%; display: block;}
            `,
            body: `
                <div id="container">
                    <model-viewer
                        id="mv"
                        src="${modelWebUri}"
                        camera-controls
                        tone-mapping="neutral"
                        exposure="1.2"
                        shadow-intensity="0.7"
                        shadow-softness="0.8"
                    ></model-viewer>
                </div>
            `,
        });
    }

    protected getLocalResourceRoots(): vscode.Uri[] {
        const roots = super.getLocalResourceRoots();
        const model = getCurrentThreeDModel();
        if (model && fs.existsSync(model.path)) {
            roots.push(vscode.Uri.file(path.dirname(model.path)));
        }
        return roots;
    }

    private getModelViewerScriptUri(webview: vscode.Webview): vscode.Uri {
        return webview.asWebviewUri(vscode.Uri.file(getAndCheckResource('model-viewer/model-viewer.min.js')));
    }
}

let modelViewer: ModelViewerWebview | undefined;

export async function openModelViewerPreview() {
    if (!modelViewer) {
        modelViewer = new ModelViewerWebview();
    }
    await modelViewer.open();
}

export function closeModelViewerPreview() {
    modelViewer?.dispose();
    modelViewer = undefined;
}

export async function activate(context: vscode.ExtensionContext) {
    context.subscriptions.push(
        onThreeDModelChanged((_) => {
            if (modelViewer?.isOpen()) {
                openModelViewerPreview();
            }
        }),
    );
}

export function deactivate() {
    closeModelViewerPreview();
}
