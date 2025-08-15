import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { BaseWebview } from './webview-base';
import { buildHtml } from './html-builder';
import { runAtoCommandWithOutput } from '../common/findbin';
import { getProjectRoot } from '../common/utilities';
import { traceError, traceInfo } from '../common/log/logging';

interface DiagramViewerMessage {
    type: 'depthChanged' | 'typeChanged' | 'loadDiagram' | 'generatePowerTree';
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
                    background: var(--vscode-editor-background);
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
                    <div class="control-group">
                        <button id="generatePowerTreeBtn">Generate Power Tree</button>
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
                    
                    document.getElementById('generatePowerTreeBtn').addEventListener('click', () => {
                        vscode.postMessage({ type: 'generatePowerTree' });
                    });
                    
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
                            // Don't reload the whole page, just update the diagram area
                            console.log('Diagram loaded message received');
                        }
                    });
                </script>
            `,
        });
    }

    private getDiagramContent(): string {
        if (!this.currentDiagramPath) {
            return `
                <div class="no-diagram-message">
                    <div class="load-diagram-container">
                        <p>No power tree diagram generated</p>
                        <p>Click "Generate Power Tree" to create a power tree diagram</p>
                    </div>
                </div>
            `;
        }

        traceInfo(`getDiagramContent: currentDiagramPath length: ${this.currentDiagramPath.length}`);
        traceInfo(`getDiagramContent: starts with <svg: ${this.currentDiagramPath.startsWith('<svg')}`);

        // If we have SVG content directly (from command output), display it
        if (this.currentDiagramPath.startsWith('<svg')) {
            traceInfo('Rendering SVG content directly');
            return `<div class="diagram-content">${this.currentDiagramPath}</div>`;
        }

        // Check if it looks like raw Graphviz content (fallback case)
        if (this.currentDiagramPath.includes('digraph') || this.currentDiagramPath.includes('graph')) {
            traceInfo('Detected raw Graphviz content');
            return `<pre style="color: var(--vscode-editor-foreground); background: var(--vscode-editor-background); padding: 20px; font-family: monospace; white-space: pre-wrap; word-wrap: break-word;">${this.currentDiagramPath}</pre>`;
        }

        // Otherwise, treat it as a file path (for backwards compatibility)
        if (!fs.existsSync(this.currentDiagramPath)) {
            traceInfo('File does not exist, showing not found message');
            return `
                <div class="no-diagram-message">
                    <div class="load-diagram-container">
                        <p>Diagram file not found</p>
                        <p>Click "Generate Power Tree" to create a new power tree diagram</p>
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
            traceError(`Error in getDiagramContent: ${error}`);
            return `
                <div class="no-diagram-message">
                    <p>Error loading diagram file: ${error}</p>
                </div>
            `;
        }
    }

    private async generatePowerTree(): Promise<string | null> {
        try {
            traceInfo('Generating power tree diagram...');
            
            // Get project root
            const projectRoot = await getProjectRoot();
            traceInfo(`Project root: ${projectRoot.uri.fsPath}`);

            // Execute the ato command with the new utility function
            const result = await runAtoCommandWithOutput(
                projectRoot.uri.fsPath,
                ['view', 'power-tree', `--max-depth=${this.currentDepth}`, '--format=dot'],
                30000
            );

            traceInfo(`Command result - err: ${!!result.err}, stdout length: ${result.stdout?.length || 0}, stderr: ${result.stderr || 'none'}`);

            if (result.err) {
                traceError(`Command failed: ${result.stderr || result.err.message}`);
                vscode.window.showErrorMessage(`Failed to generate power tree: ${result.stderr || result.err.message}`);
                return null;
            }

            if (!result.stdout || result.stdout.trim() === '') {
                traceError('Command returned no output');
                vscode.window.showWarningMessage('Power tree command executed but returned no output.');
                return null;
            }

            traceInfo(`Power tree output (first 200 chars): ${result.stdout.substring(0, 200)}...`);
            traceInfo('Power tree generated successfully, converting Graphviz to SVG...');
            
            try {
                // Use require to import viz.js and handle types manually
                const vizModule = require('@viz-js/viz');
                const viz = await vizModule.instance();
                
                // Convert Graphviz DOT to SVG
                let svgOutput = viz.renderString(result.stdout, { format: 'svg', engine: 'dot' });
                
                // Apply VS Code theme colors to the SVG
                svgOutput = this.applyVSCodeThemeToSVG(svgOutput);
                
                traceInfo(`SVG output length: ${svgOutput.length}`);
                traceInfo(`SVG starts with: ${svgOutput.substring(0, 100)}`);
                traceInfo('Graphviz converted to SVG successfully');
                return svgOutput;
                
            } catch (vizError) {
                traceError(`Error converting Graphviz to SVG: ${vizError}`);
                vscode.window.showErrorMessage(`Failed to render Graphviz output: ${vizError}`);
                
                // Fallback: return the raw graphviz content for debugging
                return `<pre style="color: var(--vscode-editor-foreground); background: var(--vscode-editor-background); padding: 20px; font-family: monospace; white-space: pre-wrap; word-wrap: break-word;">${result.stdout}</pre>`;
            }

        } catch (error) {
            traceError(`Error generating power tree: ${error}`);
            vscode.window.showErrorMessage(`Error generating power tree: ${error}`);
            return null;
        }
    }

    private applyVSCodeThemeToSVG(svgContent: string): string {
        try {
            // Add CSS styles to make the SVG use VS Code theme colors
            const styleTag = `<style>
                /* Apply VS Code theme colors */
                .node polygon, .node ellipse, .node path {
                    fill: var(--vscode-editor-background) !important;
                    stroke: var(--vscode-editor-foreground) !important;
                    stroke-width: 1 !important;
                }
                
                .node text {
                    fill: var(--vscode-editor-foreground) !important;
                    font-family: var(--vscode-font-family) !important;
                }
                
                .edge path {
                    stroke: var(--vscode-editor-foreground) !important;
                    stroke-width: 1 !important;
                }
                
                .edge polygon {
                    fill: var(--vscode-editor-foreground) !important;
                    stroke: var(--vscode-editor-foreground) !important;
                }
                
                .edge text {
                    fill: var(--vscode-editor-foreground) !important;
                    font-family: var(--vscode-font-family) !important;
                }
                
                /* Background */
                svg {
                    background: var(--vscode-editor-background) !important;
                }
                
                /* Graph background if present */
                .graph > polygon {
                    fill: var(--vscode-editor-background) !important;
                }
            </style>`;

            // Find the opening <svg> tag and insert the style after it
            const svgTagMatch = svgContent.match(/<svg[^>]*>/);
            if (svgTagMatch) {
                const insertIndex = svgTagMatch.index! + svgTagMatch[0].length;
                return svgContent.slice(0, insertIndex) + styleTag + svgContent.slice(insertIndex);
            }

            // Fallback: just prepend the style if we can't find the svg tag
            return styleTag + svgContent;
        } catch (error) {
            traceError(`Error applying VS Code theme to SVG: ${error}`);
            return svgContent; // Return original if theming fails
        }
    }

    private async handleGeneratePowerTree(): Promise<void> {
        try {
            // Show progress indicator
            await vscode.window.withProgress({
                location: vscode.ProgressLocation.Notification,
                title: "Generating Power Tree",
                cancellable: false
            }, async (progress) => {
                progress.report({ increment: 0, message: "Executing ato view power-tree..." });
                
                const svgContent = await this.generatePowerTree();
                
                if (svgContent) {
                    // Store the SVG content directly as the "path"
                    this.currentDiagramPath = svgContent;
                    traceInfo(`Stored SVG content, length: ${svgContent.length}`);
                    progress.report({ increment: 100, message: "Power tree generated successfully" });
                    this.refreshView();
                } else {
                    traceError('No SVG content generated');
                    progress.report({ increment: 100, message: "Failed to generate power tree" });
                }
            });
        } catch (error) {
            traceError(`Error in handleGeneratePowerTree: ${error}`);
            vscode.window.showErrorMessage(`Failed to generate power tree: ${error}`);
        }
    }

    protected setupPanel(): void {
        if (!this.panel) return;

        this.panel.webview.onDidReceiveMessage(
            async (message: DiagramViewerMessage) => {
                switch (message.type) {
                    case 'generatePowerTree':
                        await this.handleGeneratePowerTree();
                        break;
                    case 'typeChanged':
                        if (message.diagramType !== undefined) {
                            this.currentType = message.diagramType;
                            this.refreshView();
                        }
                        break;
                    case 'depthChanged':
                        if (message.depth !== undefined) {
                            this.currentDepth = message.depth;
                            // Regenerate if we already have a power tree
                            if (this.currentDiagramPath && !this.currentDiagramPath.includes('/')) {
                                await this.handleGeneratePowerTree();
                            } else {
                                this.refreshView();
                            }
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

    public async generatePowerTreeDiagram(): Promise<void> {
        await this.handleGeneratePowerTree();
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
