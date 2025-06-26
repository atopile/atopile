import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { onThreeDModelChanged, getCurrentThreeDModel } from '../common/3dmodel';
import { getResourcesPath } from '../common/resources';

let panel: vscode.WebviewPanel | undefined;
const modelViewerVersion = '4.1.0';
const modelViewerUrl = `https://ajax.googleapis.com/ajax/libs/model-viewer/${modelViewerVersion}/model-viewer.min.js`;

function _getMissingHTML(): string {
    return /* html */ `
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1.0" />
            <title>No 3D Model</title>
            <style>
                html, body {padding: 0; margin: 0; height: 100%; width: 100%; display: flex; align-items: center; justify-content: center; background: var(--vscode-editor-background); color: var(--vscode-descriptionForeground); font-family: var(--vscode-font-family);}
                .msg {font-size: 0.9rem; opacity: 0.8;}
            </style>
        </head>
        <body><div class="msg">Build target does not have a valid 3D model.</div></body>
        </html>`;
}

function _getModelViewerHTML(webview: vscode.Webview, model_path: string | undefined): string {
    if (!model_path) {
        return _getMissingHTML();
    }

    const cacheBuster = Date.now();
    let modelWebUri = webview.asWebviewUri(vscode.Uri.file(model_path));
    // use cache buster to force reload
    modelWebUri = vscode.Uri.parse(`${modelWebUri.toString()}?cb=${cacheBuster}`);

    return /* html */ `
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1.0" />
            <title>3D Model Preview</title>
            <script type="module" src="${modelViewerUrl}"></script>
            <style>
                html, body {padding: 0; margin: 0; height: 100%; width: 100%; overflow: hidden;}
                #container {height: 100%; width: 100%;}
                model-viewer {height: 100%; width: 100%; display: block;}
            </style>
        </head>
        <body>
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
        </body>
        </html>`;
}

export async function openModelViewerPreview() {
    const model = getCurrentThreeDModel();
    let model_path = undefined;
    if (model && fs.existsSync(model.path)) {
        model_path = model.path;
    }

    let resourceRoots = [
        vscode.Uri.file(getResourcesPath()),
        ...(vscode.workspace.workspaceFolders?.map((f) => f.uri) ?? []),
    ];
    if (model_path) {
        resourceRoots.push(vscode.Uri.file(path.dirname(model_path)));
    }

    if (!panel) {
        panel = vscode.window.createWebviewPanel('modelviewer_preview', '3D Model', vscode.ViewColumn.Beside, {
            enableScripts: true,
            localResourceRoots: resourceRoots,
        });

        panel.onDidDispose(() => {
            panel = undefined;
        });

        // FIXME: add a 3d model icon
        const icon = vscode.Uri.file(path.join(getResourcesPath(), 'pcb-icon-transparent.svg'));
        panel.iconPath = {
            light: icon,
            dark: icon,
        };
    }

    panel.webview.options = { ...panel.webview.options, localResourceRoots: resourceRoots };
    panel.webview.html = _getModelViewerHTML(panel.webview, model_path);

    panel.reveal();
}

export function closeModelViewerPreview() {
    if (!panel) {
        return;
    }
    panel.dispose();
    panel = undefined;
}

export async function activate(context: vscode.ExtensionContext) {
    context.subscriptions.push(
        onThreeDModelChanged((_) => {
            if (!panel) {
                return;
            }
            openModelViewerPreview();
        }),
    );
}

export function deactivate() {
    closeModelViewerPreview();
}