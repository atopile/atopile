import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { onThreeDModelChanged, getCurrentThreeDModel } from '../common/3dmodel';
import { BaseWebview } from './webview-base';
import { buildHtml } from './html-builder';

const modelViewerVersion = '4.1.0';
const modelViewerUrl = `https://ajax.googleapis.com/ajax/libs/model-viewer/${modelViewerVersion}/model-viewer.min.js`;

class ModelViewerWebview extends BaseWebview {
    constructor() {
        super({
            id: 'modelviewer_preview',
            title: '3D Model',
            // iconName: '3dmodel-icon-transparent.svg', // FIXME: add
        });
    }

    protected getHtmlContent(webview: vscode.Webview): string {
        const model = getCurrentThreeDModel();
        if (!model || !fs.existsSync(model.path)) {
            return this.getMissingResourceHtml('3D Model');
        }

        const modelWebUri = this.getWebviewUri(webview, model.path);

        return buildHtml({
            title: '3D Model Preview',
            scripts: [{ type: 'module', src: modelViewerUrl }],
            styles: `
                #container {height: 100%; width: 100%;}
                model-viewer {height: 100%; width: 100%; display: block;}
            `,
            body: `
                <div id="container">
                    <model-viewer
                        id="mv"
                        src="${modelWebUri}"
                        auto-rotate
                        camera-controls
                        tone-mapping="neutral"
                        exposure="1.2"
                        shadow-intensity="0.7"
                        shadow-softness="0.8"
                        ar
                        ar-modes="webxr scene-viewer quick-look"
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