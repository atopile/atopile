import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { BaseWebview } from './webview-base';
import { buildHtml } from './html-builder';

interface DiagramViewerMessage {
    type: 'depthChanged' | 'typeChanged' | 'loadDiagram';
    depth?: number;
    diagramType?: string;
    diagramPath?: string;
}

class DiagramViewerWebview extends BaseWebview {
    private currentDiagramPath: string | undefined;
    private currentDepth: number = 1;
    private currentType: string = 'power tree';

    constructor() {
        super({
            id: 'diagram_viewer',
            title: 'Diagram Viewer',
            iconName: 'atopile-icon.svg',
            enableScripts: true,
        });
    }

    protected getHtmlContent(_webview: vscode.Webview): string {
        const diagramContent = this.getDiagramContent();

        return buildHtml({
            title: 'Diagram Viewer',
            styles: `
                body {
                    font-family: var(--vscode-font-family);
                    background: var(--vscode-editor-background);
                    color: var(--vscode-editor-foreground);
                    display: flex;
                    flex-direction: column;
                    height: 100vh;
                    margin: 0;
                    padding: 0;
                }
                
                .controls {
                    padding: 10px;
                    border-bottom: 1px solid var(--vscode-panel-border);
                    background: var(--vscode-sideBar-background);
                    display: flex;
                    align-items: center;
                    gap: 15px;
                    flex-shrink: 0;
                    flex-wrap: wrap;
                }
                
                .submenu-controls {
                    padding: 8px 10px;
                    border-bottom: 1px solid var(--vscode-panel-border);
                    background: var(--vscode-editor-background);
                    display: flex;
                    align-items: center;
                    gap: 15px;
                    flex-shrink: 0;
                    flex-wrap: wrap;
                    opacity: 0.9;
                }
                
                .submenu-controls.hidden {
                    display: none;
                }
                
                .control-group {
                    display: flex;
                    align-items: center;
                    gap: 5px;
                }
                
                label {
                    font-size: 12px;
                    color: var(--vscode-descriptionForeground);
                    min-width: 40px;
                }
                
                select, button {
                    background: var(--vscode-button-background);
                    color: var(--vscode-button-foreground);
                    border: 1px solid var(--vscode-button-border);
                    border-radius: 2px;
                    padding: 4px 8px;
                    font-size: 12px;
                    cursor: pointer;
                    min-width: 80px;
                }
                
                select:hover, button:hover {
                    background: var(--vscode-button-hoverBackground);
                }
                
                select:focus, button:focus {
                    outline: 1px solid var(--vscode-focusBorder);
                    outline-offset: 2px;
                }
                
                .diagram-container {
                    flex: 1;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    padding: 20px;
                    overflow: auto;
                }
                
                .diagram-content {
                    max-width: 100%;
                    max-height: 100%;
                    border: 1px solid var(--vscode-panel-border);
                    border-radius: 4px;
                    background: white;
                }
                
                .no-diagram-message {
                    color: var(--vscode-descriptionForeground);
                    font-style: italic;
                    text-align: center;
                }
                
                .load-diagram-container {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    gap: 10px;
                }
            `,
            body: `
                <div class="controls">
                    <div class="control-group">
                        <label for="typeSelect">Type:</label>
                        <select id="typeSelect">
                            <option value="power tree" ${this.currentType === 'power tree' ? 'selected' : ''}>Power Tree</option>
                        </select>
                    </div>
                </div>
                
                <div class="submenu-controls ${this.currentType === 'power tree' ? '' : 'hidden'}" id="submenuControls">
                    <div class="control-group">
                        <label for="depthSelect">Depth:</label>
                        <select id="depthSelect">
                            <option value="1" ${this.currentDepth === 1 ? 'selected' : ''}>1</option>
                            <option value="2" ${this.currentDepth === 2 ? 'selected' : ''}>2</option>
                            <option value="3" ${this.currentDepth === 3 ? 'selected' : ''}>3</option>
                            <option value="4" ${this.currentDepth === 4 ? 'selected' : ''}>4</option>
                            <option value="5" ${this.currentDepth === 5 ? 'selected' : ''}>5</option>
                            <option value="10" ${this.currentDepth === 10 ? 'selected' : ''}>10</option>
                        </select>
                    </div>
                </div>
                
                <div class="diagram-container">
                    ${diagramContent}
                </div>
                
                <script>
                    const vscode = acquireVsCodeApi();
                    
                    document.getElementById('typeSelect').addEventListener('change', (e) => {
                        const diagramType = e.target.value;
                        vscode.postMessage({ type: 'typeChanged', diagramType: diagramType });
                        
                        // Show/hide submenu based on type
                        const submenu = document.getElementById('submenuControls');
                        if (diagramType === 'power tree') {
                            submenu.classList.remove('hidden');
                        } else {
                            submenu.classList.add('hidden');
                        }
                    });
                    
                    document.getElementById('depthSelect').addEventListener('change', (e) => {
                        const depth = parseInt(e.target.value);
                        vscode.postMessage({ type: 'depthChanged', depth: depth });
                    });
                    
                    // Listen for messages from the extension
                    window.addEventListener('message', event => {
                        const message = event.data;
                        if (message.type === 'diagramLoaded') {
                            location.reload();
                        }
                    });
                </script>
            `,
        });
    }

    private getDiagramContent(): string {
        if (!this.currentDiagramPath || !fs.existsSync(this.currentDiagramPath)) {
            return `
                <div class="no-diagram-message">
                    <div class="load-diagram-container">
                        <p>No power tree diagram loaded</p>
                        <p>Click "Load Power Tree" to select a power tree diagram file</p>
                    </div>
                </div>
            `;
        }

        try {
            const fileExtension = path.extname(this.currentDiagramPath).toLowerCase();
            
            if (fileExtension === '.svg') {
                const svgContent = fs.readFileSync(this.currentDiagramPath, 'utf8');
                return `<div class="diagram-content">${svgContent}</div>`;
            } else if (['.png', '.jpg', '.jpeg', '.gif'].includes(fileExtension)) {
                const fileName = path.basename(this.currentDiagramPath);
                return `<div class="diagram-content"><img src="file://${this.currentDiagramPath}" alt="${fileName}" style="max-width: 100%; max-height: 100%; object-fit: contain;" /></div>`;
            } else if (fileExtension === '.pdf') {
                return `
                    <div class="no-diagram-message">
                        <p>PDF viewing not yet supported</p>
                        <p>File: ${path.basename(this.currentDiagramPath)}</p>
                    </div>
                `;
            } else {
                return `
                    <div class="no-diagram-message">
                        <p>Unsupported file type: ${fileExtension}</p>
                    </div>
                `;
            }
        } catch (error) {
            return `
                <div class="no-diagram-message">
                    <p>Error loading diagram file: ${error}</p>
                </div>
            `;
        }
    }

    protected setupPanel(): void {
        if (!this.panel) return;

        this.panel.webview.onDidReceiveMessage(
            async (message: DiagramViewerMessage) => {
                switch (message.type) {
                    case 'typeChanged':
                        if (message.diagramType !== undefined) {
                            this.currentType = message.diagramType;
                            this.refreshView();
                        }
                        break;
                    case 'depthChanged':
                        if (message.depth !== undefined) {
                            this.currentDepth = message.depth;
                            this.refreshView();
                        }
                        break;
                }
            }
        );
    }

    private refreshView(): void {
        if (this.panel) {
            this.panel.webview.html = this.getHtmlContent(this.panel.webview);
        }
    }

    protected getLocalResourceRoots(): vscode.Uri[] {
        const roots = super.getLocalResourceRoots();
        
        if (this.currentDiagramPath && fs.existsSync(this.currentDiagramPath)) {
            roots.push(vscode.Uri.file(path.dirname(this.currentDiagramPath)));
        }
        
        return roots;
    }

    public getCurrentDepth(): number {
        return this.currentDepth;
    }

    public getCurrentType(): string {
        return this.currentType;
    }

    public getCurrentDiagramPath(): string | undefined {
        return this.currentDiagramPath;
    }

    public async loadSpecificDiagram(diagramPath: string): Promise<void> {
        if (fs.existsSync(diagramPath)) {
            this.currentDiagramPath = diagramPath;
            
            // Type is always "power tree" now
            this.currentType = 'power tree';
            
            this.refreshView();
        } else {
            vscode.window.showErrorMessage(`Diagram file not found: ${diagramPath}`);
        }
    }
}

let diagramViewerInstance: DiagramViewerWebview | undefined;

export function activate(_context: vscode.ExtensionContext) {
    diagramViewerInstance = new DiagramViewerWebview();
    // Note: Command registration is handled by buttons.ts
}

export function deactivate() {
    if (diagramViewerInstance) {
        diagramViewerInstance.dispose();
        diagramViewerInstance = undefined;
    }
}

export function getDiagramViewerInstance(): DiagramViewerWebview | undefined {
    return diagramViewerInstance;
}
