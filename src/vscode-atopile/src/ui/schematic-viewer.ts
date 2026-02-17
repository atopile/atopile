/**
 * Schematic viewer webview.
 *
 * Loads the React-based schematic viewer from the ui-server build output.
 * Data is passed via window.__SCHEMATIC_VIEWER_CONFIG__ with a webview URI to the JSON file.
 *
 * Production: loads from resources/webviews/schematic.html
 * Development: loads from ui-server/dist/schematic.html
 */

import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import axios from 'axios';
import { getCurrentSchematic, onSchematicChanged } from '../common/schematic';
import { BaseWebview } from './webview-base';
import { backendServer } from '../common/backendServer';
import { getBuildTarget, getProjectRoot } from '../common/target';

/**
 * Locate the schematic viewer dist directory.
 */
function getSchematicViewerDistPath(): string | null {
    const extensionPath = vscode.extensions.getExtension('atopile.atopile')?.extensionUri?.fsPath;

    if (extensionPath) {
        // Production: webviews are built into resources/webviews/
        const prodPath = path.join(extensionPath, 'resources', 'webviews');
        if (fs.existsSync(path.join(prodPath, 'schematic.html'))) {
            return prodPath;
        }
    }

    // Development: use ui-server dist directly
    for (const folder of vscode.workspace.workspaceFolders ?? []) {
        const devPath = path.join(folder.uri.fsPath, 'src', 'ui-server', 'dist');
        if (fs.existsSync(path.join(devPath, 'schematic.html'))) {
            return devPath;
        }
    }

    return null;
}

type SchematicBuildPhase = 'idle' | 'building' | 'queued' | 'success' | 'failed';

interface SchematicBuildStatusPayload {
    phase: SchematicBuildPhase;
    dirty: boolean;
    viewingLastSuccessful: boolean;
    lastSuccessfulAt: number | null;
    message: string | null;
}

interface SchematicBuildError {
    message: string;
    filePath: string | null;
    line: number | null;
    column: number | null;
}

interface ShowInSchematicRequest {
    filePath: string;
    line: number;
    column: number;
    symbol?: string;
}

const SCHEMATIC_BUILD_DEBOUNCE_MS = 500;
const SCHEMATIC_BUILD_POLL_MS = 700;
const SCHEMATIC_BUILD_TIMEOUT_MS = 8 * 60 * 1000;
const SCHEMATIC_INCLUDE_TARGETS = ['schematic'];
const SCHEMATIC_EXCLUDE_TARGETS = ['default'];
const AUTO_BUILD_EXTENSIONS = new Set(['.ato', '.py']);
const SHOW_IN_SCHEMATIC_COMMAND = 'atopile.show_in_schematic';
const SYMBOL_TOKEN_RE = /[A-Za-z_][A-Za-z0-9_\[\]\.]*/;
const IGNORED_SYMBOL_TOKENS = new Set([
    'new',
    'module',
    'component',
    'interface',
    'signal',
    'from',
    'import',
    'if',
    'else',
    'for',
    'while',
    'return',
]);

class SchematicWebview extends BaseWebview {
    /**
     * Timestamp of the last position save initiated by the webview.
     * Used to suppress file-watcher reloads triggered by our own writes.
     */
    private _lastSaveTime = 0;
    private static readonly SAVE_SUPPRESS_MS = 2000;

    /** Check if a recent self-save should suppress a file-watcher event. */
    public shouldSuppressReload(): boolean {
        return Date.now() - this._lastSaveTime < SchematicWebview.SAVE_SUPPRESS_MS;
    }

    /** Mark that we just saved positions (so we can suppress the echo). */
    public markSave(): void {
        this._lastSaveTime = Date.now();
    }

    constructor() {
        super({
            id: 'schematic_preview',
            title: 'Schematic',
        });
    }

    protected getHtmlContent(webview: vscode.Webview): string {
        const resource = getCurrentSchematic();

        if (!resource || !resource.exists) {
            return this.getMissingResourceHtml('Schematic');
        }

        const distPath = getSchematicViewerDistPath();
        if (distPath) {
            return this.getProductionHtml(webview, distPath, resource.path);
        }

        // Fallback: inline minimal message
        return this.getInlineHtml();
    }

    protected getLocalResourceRoots(): vscode.Uri[] {
        const roots = super.getLocalResourceRoots();
        const distPath = getSchematicViewerDistPath();
        if (distPath) {
            roots.push(vscode.Uri.file(distPath));
        }
        const resource = getCurrentSchematic();
        if (resource && fs.existsSync(resource.path)) {
            roots.push(vscode.Uri.file(path.dirname(resource.path)));
        }
        return roots;
    }

    /**
     * Load the compiled React app from dist, injecting the data URL.
     */
    private getProductionHtml(webview: vscode.Webview, distPath: string, dataPath: string): string {
        const indexHtmlPath = path.join(distPath, 'schematic.html');
        let html = fs.readFileSync(indexHtmlPath, 'utf-8');

        const distUri = webview.asWebviewUri(vscode.Uri.file(distPath));
        const dataUri = this.getWebviewUri(webview, dataPath);

        // Rewrite asset paths
        html = html.replace(/(href|src)="\.\/assets\//g, `$1="${distUri}/assets/`);
        html = html.replace(/(href|src)="\/assets\//g, `$1="${distUri}/assets/`);
        html = html.replace(/(href|src)="\.\/schematic\./g, `$1="${distUri}/schematic.`);
        html = html.replace(/(href|src)="\/schematic\./g, `$1="${distUri}/schematic.`);

        // Also handle the entry JS in dev mode
        html = html.replace(/src="\.\/src\/schematic\.tsx"/g, `src="${distUri}/schematic.js"`);

        // Inject config — .ato_sch contains both schematic data and positions
        const configScript = `
            <script>
                window.__SCHEMATIC_VIEWER_CONFIG__ = {
                    dataUrl: "${dataUri.toString()}",
                    atoSchPath: "${dataPath.replace(/\\/g, '\\\\')}"
                };
            </script>
        `;
        html = html.replace('</head>', `${configScript}</head>`);

        return html;
    }

    /**
     * Fallback when the React app hasn't been built yet.
     */
    private getInlineHtml(): string {
        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Schematic</title>
    <style>
        body {
            display: flex; align-items: center; justify-content: center;
            height: 100vh; margin: 0;
            background: var(--vscode-editor-background, #1e1e1e);
            color: var(--vscode-descriptionForeground, #888);
            font-family: var(--vscode-font-family, system-ui);
            font-size: 13px; text-align: center; padding: 24px;
        }
        code { background: var(--vscode-textCodeBlock-background, #2d2d30); padding: 2px 6px; border-radius: 3px; font-size: 12px; }
    </style>
</head>
<body>
    <div>
        <p>Schematic viewer not built.</p>
        <p>Run <code>cd src/ui-server && npm run build</code> then rebuild the extension.</p>
    </div>
</body>
</html>`;
    }

    /**
     * Set up the panel to receive messages from the webview.
     */
    protected setupPanel(): void {
        if (!this.panel) return;

        this.panel.webview.onDidReceiveMessage(async (message) => {
            switch (message.type) {
                case 'openSource': {
                    // Bidirectional: webview sends an atopile address to open in source
                    const address = message.address as string | undefined;
                    const filePath = message.filePath as string | undefined;
                    const line = message.line as number | undefined;
                    const column = message.column as number | undefined;
                    const hasValidLine = typeof line === 'number' && Number.isFinite(line) && line > 0;

                    if (filePath && hasValidLine) {
                        // Direct source location when the schematic has a concrete line mapping.
                        this.openSourceFile(filePath, line, column);
                    } else if (address) {
                        // Fallback for schematics where source.line is missing/0:
                        // resolve the address to a concrete location first.
                        const resolved = await this.resolveAddressToSource(address);
                        if (resolved) {
                            this.openSourceFile(resolved.filePath, resolved.line, resolved.column);
                        } else if (filePath) {
                            this.openSourceFile(filePath);
                        }
                    } else if (filePath) {
                        this.openSourceFile(filePath);
                    }
                    break;
                }
                case 'revealInExplorer': {
                    const filePath = message.filePath as string | undefined;
                    const address = message.address as string | undefined;

                    if (filePath) {
                        this.revealFileInExplorer(filePath);
                    } else if (address) {
                        const resolved = await this.resolveAddressToSource(address);
                        if (resolved?.filePath) {
                            this.revealFileInExplorer(resolved.filePath);
                        }
                    }
                    break;
                }
                case 'save-layout': {
                    // Merge positions back into the .ato_sch file
                    const atoSchPath = message.atoSchPath as string | undefined;
                    const positions = message.positions;
                    const portSignalOrders = message.portSignalOrders;
                    const routeOverrides = message.routeOverrides;
                    if (atoSchPath && positions) {
                        try {
                            let data: Record<string, unknown> = {};
                            if (fs.existsSync(atoSchPath)) {
                                data = JSON.parse(fs.readFileSync(atoSchPath, 'utf-8'));
                            }
                            data.positions = positions;
                            if (portSignalOrders && typeof portSignalOrders === 'object') {
                                data.portSignalOrders = portSignalOrders;
                            }
                            if (routeOverrides && typeof routeOverrides === 'object') {
                                data.routeOverrides = routeOverrides;
                            }
                            const dir = path.dirname(atoSchPath);
                            if (!fs.existsSync(dir)) {
                                fs.mkdirSync(dir, { recursive: true });
                            }
                            // Mark self-save so the file watcher doesn't trigger a reload
                            this.markSave();
                            fs.writeFileSync(atoSchPath, JSON.stringify(data, null, 2), 'utf-8');
                        } catch (e) {
                            console.error('Failed to save positions to .ato_sch:', e);
                        }
                    }
                    break;
                }
                case 'revertToLastSuccessful': {
                    if (lastSuccessfulSchematicData) {
                        this.postMessage({
                            type: 'update-schematic',
                            data: lastSuccessfulSchematicData,
                        });
                        updateSchematicBuildState({
                            viewingLastSuccessful: true,
                        });
                    }
                    break;
                }
                case 'showInSchematicResult': {
                    const found = message.found === true;
                    if (!found) {
                        const symbol = typeof message.symbol === 'string'
                            ? message.symbol
                            : undefined;
                        const detail = symbol
                            ? ` for "${symbol}"`
                            : '';
                        void vscode.window.setStatusBarMessage(
                            `atopile: No schematic match found${detail}`,
                            3500,
                        );
                    }
                    break;
                }
            }
        });
    }

    private openSourceFile(filePath: string, line?: number, column?: number): void {
        const uri = vscode.Uri.file(filePath);
        const location = (() => {
            if (line == null || line <= 0) return null;
            const zeroBasedColumn = (column != null && column > 0)
                ? column - 1
                : 0;
            const position = new vscode.Position(
                Math.max(0, line - 1),
                zeroBasedColumn,
            );
            return {
                position,
                range: new vscode.Range(position, position),
                selection: new vscode.Selection(position, position),
            };
        })();

        const existingVisibleEditor = vscode.window.visibleTextEditors.find(
            (editor) => editor.document.uri.toString() === uri.toString(),
        );
        if (existingVisibleEditor) {
            if (location) {
                existingVisibleEditor.selection = location.selection;
                existingVisibleEditor.revealRange(
                    location.range,
                    vscode.TextEditorRevealType.InCenterIfOutsideViewport,
                );
            }
            void vscode.window.showTextDocument(existingVisibleEditor.document, {
                viewColumn: existingVisibleEditor.viewColumn,
                preserveFocus: true,
            });
            return;
        }

        vscode.workspace.openTextDocument(uri).then((doc) => {
            const options: vscode.TextDocumentShowOptions = {
                viewColumn: vscode.window.activeTextEditor?.viewColumn ?? vscode.ViewColumn.One,
            };
            if (location) {
                options.selection = location.range;
            }
            vscode.window.showTextDocument(doc, options);
        });
    }

    private revealFileInExplorer(filePath: string): void {
        void vscode.commands.executeCommand('revealFileInOS', vscode.Uri.file(filePath));
    }

    private async resolveAddressToSource(address: string): Promise<{
        filePath: string;
        line?: number;
        column?: number;
    } | null> {
        if (!backendServer.isConnected) return null;

        try {
            const root = getProjectRoot();
            const url = `${backendServer.apiUrl}/api/resolve-location?address=${encodeURIComponent(address)}${root ? `&project_root=${encodeURIComponent(root)}` : ''}`;
            const resp = await axios.get(url);
            const filePath = (resp.data?.file_path ?? resp.data?.file) as string | undefined;
            if (!filePath) return null;
            const line = typeof resp.data?.line === 'number' ? resp.data.line : undefined;
            const column = typeof resp.data?.column === 'number' ? resp.data.column : undefined;
            return { filePath, line, column };
        } catch {
            // Silently fail — resolve-location may not find all addresses
            return null;
        }
    }

    /**
     * Send a message to the webview (for active file tracking etc).
     */
    public postMessage(message: unknown): void {
        this.panel?.webview.postMessage(message);
    }
}

let schematicViewer: SchematicWebview | undefined;
let buildDebounceTimer: NodeJS.Timeout | null = null;
let buildInFlight = false;
let buildQueued = false;
let lastSuccessfulSchematicData: unknown | null = null;
let lastBuildErrors: SchematicBuildError[] = [];

const schematicBuildState: SchematicBuildStatusPayload = {
    phase: 'idle',
    dirty: false,
    viewingLastSuccessful: false,
    lastSuccessfulAt: null,
    message: null,
};

function sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

function updateSchematicBuildState(
    patch: Partial<SchematicBuildStatusPayload>,
): void {
    Object.assign(schematicBuildState, patch);
    schematicViewer?.postMessage({
        type: 'schematic-build-status',
        ...schematicBuildState,
    });
}

function setSchematicBuildErrors(errors: SchematicBuildError[]): void {
    lastBuildErrors = errors;
    schematicViewer?.postMessage({
        type: 'schematic-build-errors',
        errors,
    });
}

async function fetchSchematicArtifact(
    endpoint: '/api/bom' | '/api/variables',
    projectRoot: string,
    target: string,
): Promise<unknown | null> {
    try {
        const response = await axios.get(`${backendServer.apiUrl}${endpoint}`, {
            params: {
                project_root: projectRoot,
                target,
            },
            timeout: 10000,
        });
        return response.data ?? null;
    } catch (error) {
        if (axios.isAxiosError(error)) {
            const status = error.response?.status;
            // No artifacts yet is expected before the first successful build.
            if (status === 404 || status === 400) {
                return null;
            }
        }
        return null;
    }
}

async function pushSchematicArtifactsToWebview(): Promise<void> {
    if (!schematicViewer?.isOpen()) return;

    const build = getBuildTarget();
    if (!build) {
        schematicViewer.postMessage({
            type: 'schematic-artifacts',
            bomData: null,
            variablesData: null,
        });
        return;
    }

    try {
        if (!backendServer.isConnected) {
            await backendServer.startServer();
        }
    } catch {
        // If backend startup fails, still push an empty payload.
    }

    if (!backendServer.isConnected) {
        schematicViewer.postMessage({
            type: 'schematic-artifacts',
            bomData: null,
            variablesData: null,
        });
        return;
    }

    const [bomData, variablesData] = await Promise.all([
        fetchSchematicArtifact('/api/bom', build.root, build.name),
        fetchSchematicArtifact('/api/variables', build.root, build.name),
    ]);

    schematicViewer.postMessage({
        type: 'schematic-artifacts',
        bomData,
        variablesData,
    });
}

function readCurrentSchematicPayload():
    | { data: unknown; mtimeMs: number }
    | null {
    const resource = getCurrentSchematic();
    if (!resource?.exists) return null;
    try {
        const raw = fs.readFileSync(resource.path, 'utf-8');
        const data = JSON.parse(raw);
        const mtimeMs = fs.statSync(resource.path).mtimeMs;
        return { data, mtimeMs };
    } catch {
        return null;
    }
}

function rememberLastSuccessfulSchematic(
    data: unknown,
    mtimeMs?: number,
): void {
    lastSuccessfulSchematicData = data;
    updateSchematicBuildState({
        lastSuccessfulAt: mtimeMs ?? Date.now(),
    });
}

/**
 * Send updated schematic data to an already-open webview without
 * replacing the HTML (preserves navigation state, selection, etc.).
 */
function sendSchematicUpdate(markSuccessful: boolean = false): boolean {
    if (!schematicViewer?.isOpen()) return false;
    const payload = readCurrentSchematicPayload();
    if (!payload) return false;

    schematicViewer.postMessage({ type: 'update-schematic', data: payload.data });

    if (markSuccessful) {
        rememberLastSuccessfulSchematic(payload.data, payload.mtimeMs);
        setSchematicBuildErrors([]);
        if (!buildInFlight) {
            updateSchematicBuildState({
                phase: 'success',
                dirty: false,
                viewingLastSuccessful: false,
                message: null,
            });
        }
        void pushSchematicArtifactsToWebview();
    }

    return true;
}

function parseBuildIdFromResponse(data: unknown): string | null {
    const obj = (data && typeof data === 'object') ? data as Record<string, unknown> : {};
    const rawTargets = obj.buildTargets ?? obj.build_targets;
    if (!Array.isArray(rawTargets) || rawTargets.length === 0) return null;
    const first = rawTargets[0];
    if (!first || typeof first !== 'object') return null;
    const firstObj = first as Record<string, unknown>;
    const buildId = firstObj.buildId ?? firstObj.build_id;
    return typeof buildId === 'string' ? buildId : null;
}

async function enqueueSchematicBuild(projectRoot: string, target: string): Promise<string> {
    const response = await axios.post(
        `${backendServer.apiUrl}/api/build`,
        {
            project_root: projectRoot,
            targets: [target],
            include_targets: SCHEMATIC_INCLUDE_TARGETS,
            exclude_targets: SCHEMATIC_EXCLUDE_TARGETS,
            keep_picked_parts: true,
        },
        { timeout: 15000 },
    );
    const data = response.data;
    const success = (data && typeof data === 'object')
        ? ((data as Record<string, unknown>).success !== false)
        : true;
    if (!success) {
        const msg = (data as Record<string, unknown> | undefined)?.message;
        throw new Error(typeof msg === 'string' ? msg : 'Failed to queue schematic build');
    }
    const buildId = parseBuildIdFromResponse(data);
    if (!buildId) {
        throw new Error('Schematic build queued without build ID');
    }
    return buildId;
}

async function waitForBuildCompletion(buildId: string): Promise<{
    status: string;
    error: string | null;
}> {
    const deadline = Date.now() + SCHEMATIC_BUILD_TIMEOUT_MS;

    while (Date.now() < deadline) {
        const response = await axios.get(`${backendServer.apiUrl}/api/build/${buildId}/status`, {
            timeout: 10000,
        });
        const data = response.data as Record<string, unknown>;
        const status = typeof data.status === 'string' ? data.status : 'queued';
        const error = typeof data.error === 'string' ? data.error : null;

        if (status === 'queued') {
            updateSchematicBuildState({
                phase: 'queued',
                dirty: true,
                viewingLastSuccessful: !!lastSuccessfulSchematicData,
                message: 'Build queued',
            });
        } else if (status === 'building') {
            updateSchematicBuildState({
                phase: 'building',
                dirty: true,
                viewingLastSuccessful: !!lastSuccessfulSchematicData,
                message: null,
            });
        } else {
            return { status, error };
        }

        await sleep(SCHEMATIC_BUILD_POLL_MS);
    }

    return { status: 'failed', error: 'Schematic build timed out' };
}

async function fetchBuildErrors(
    projectRoot: string,
    target: string,
    startedAtMs: number,
): Promise<SchematicBuildError[]> {
    try {
        const response = await axios.get(`${backendServer.apiUrl}/api/problems`, {
            params: {
                project_root: projectRoot,
                build_name: target,
                level: 'error',
            },
            timeout: 10000,
        });
        const rawProblems = response.data?.problems;
        if (!Array.isArray(rawProblems)) return [];
        return rawProblems
            .filter((p: Record<string, unknown>) => {
                const timestamp = typeof p.timestamp === 'string'
                    ? Date.parse(p.timestamp)
                    : Number.NaN;
                return Number.isNaN(timestamp) || timestamp >= startedAtMs - 5000;
            })
            .map((p: Record<string, unknown>) => {
                const rawFile = typeof p.file === 'string' ? p.file : null;
                const filePath = rawFile
                    ? (path.isAbsolute(rawFile) ? rawFile : path.resolve(projectRoot, rawFile))
                    : null;
                const line = typeof p.line === 'number'
                    ? p.line
                    : (typeof p.line === 'string' ? Number.parseInt(p.line, 10) : null);
                const column = typeof p.column === 'number'
                    ? p.column
                    : (typeof p.column === 'string' ? Number.parseInt(p.column, 10) : null);
                return {
                    message: typeof p.message === 'string' ? p.message : 'Build error',
                    filePath,
                    line: Number.isFinite(line ?? Number.NaN) ? line : null,
                    column: Number.isFinite(column ?? Number.NaN) ? column : null,
                };
            });
    } catch {
        return [];
    }
}

function postLastSuccessfulSchematicIfAvailable(): void {
    if (!lastSuccessfulSchematicData) return;
    schematicViewer?.postMessage({
        type: 'update-schematic',
        data: lastSuccessfulSchematicData,
    });
}

function applyBuildFailureState(
    message: string,
    errors: SchematicBuildError[],
): void {
    setSchematicBuildErrors(errors);
    updateSchematicBuildState({
        phase: 'failed',
        dirty: true,
        viewingLastSuccessful: !!lastSuccessfulSchematicData,
        message,
    });
    postLastSuccessfulSchematicIfAvailable();
}

function queueFollowupBuildIfNeeded(): void {
    if (!buildQueued) return;
    buildQueued = false;
    if (buildDebounceTimer) {
        clearTimeout(buildDebounceTimer);
    }
    buildDebounceTimer = setTimeout(() => {
        buildDebounceTimer = null;
        void runAutoSchematicBuild();
    }, SCHEMATIC_BUILD_DEBOUNCE_MS);
}

async function runAutoSchematicBuild(): Promise<void> {
    if (buildInFlight) return;
    const build = getBuildTarget();
    if (!build) {
        updateSchematicBuildState({
            phase: 'failed',
            dirty: true,
            viewingLastSuccessful: !!lastSuccessfulSchematicData,
            message: 'No build target selected for schematic rebuild',
        });
        return;
    }

    buildInFlight = true;
    const startedAtMs = Date.now();
    updateSchematicBuildState({
        phase: 'building',
        dirty: true,
        viewingLastSuccessful: !!lastSuccessfulSchematicData,
        message: null,
    });
    setSchematicBuildErrors([]);

    try {
        await backendServer.startServer();
        const buildId = await enqueueSchematicBuild(build.root, build.name);

        const result = await waitForBuildCompletion(buildId);
        if (result.status === 'success' || result.status === 'warning') {
            const updated = sendSchematicUpdate(true);
            if (!updated) postLastSuccessfulSchematicIfAvailable();
            updateSchematicBuildState({
                phase: 'success',
                dirty: false,
                viewingLastSuccessful: false,
                message: null,
            });
            setSchematicBuildErrors([]);
        } else {
            const message = result.error || `Build ${result.status}`;
            const errors = await fetchBuildErrors(build.root, build.name, startedAtMs);
            applyBuildFailureState(
                message,
                errors.length > 0
                    ? errors
                    : [{ message, filePath: null, line: null, column: null }],
            );
        }
    } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        applyBuildFailureState(message, [
            {
                message,
                filePath: null,
                line: null,
                column: null,
            },
        ]);
    } finally {
        buildInFlight = false;
        queueFollowupBuildIfNeeded();
    }
}

function scheduleAutoSchematicBuild(): void {
    if (!schematicViewer?.isOpen()) return;

    if (buildInFlight) {
        buildQueued = true;
        updateSchematicBuildState({
            phase: 'queued',
            dirty: true,
            viewingLastSuccessful: !!lastSuccessfulSchematicData,
            message: 'Build queued',
        });
        return;
    }

    updateSchematicBuildState({
        dirty: true,
        viewingLastSuccessful: !!lastSuccessfulSchematicData,
    });

    if (buildDebounceTimer) {
        clearTimeout(buildDebounceTimer);
    }

    buildDebounceTimer = setTimeout(() => {
        buildDebounceTimer = null;
        void runAutoSchematicBuild();
    }, SCHEMATIC_BUILD_DEBOUNCE_MS);
}

function shouldAutoBuildForSave(document: vscode.TextDocument): boolean {
    if (!schematicViewer?.isOpen()) return false;
    if (document.uri.scheme !== 'file') return false;

    const fsPath = document.uri.fsPath;
    const basename = path.basename(fsPath).toLowerCase();
    const ext = path.extname(fsPath).toLowerCase();

    if (ext === '.ato_sch') return false;
    const isAllowed = basename === 'ato.yaml' || AUTO_BUILD_EXTENSIONS.has(ext);
    if (!isAllowed) return false;

    const selectedBuild = getBuildTarget();
    if (!selectedBuild?.root) return false;

    const rel = path.relative(selectedBuild.root, fsPath);
    if (rel.startsWith('..') || path.isAbsolute(rel)) return false;

    return true;
}

function clearBuildDebounce(): void {
    if (buildDebounceTimer) {
        clearTimeout(buildDebounceTimer);
        buildDebounceTimer = null;
    }
}

function pushBuildStateAndErrorsToWebview(): void {
    if (!schematicViewer?.isOpen()) return;
    schematicViewer.postMessage({
        type: 'schematic-build-status',
        ...schematicBuildState,
    });
    schematicViewer.postMessage({
        type: 'schematic-build-errors',
        errors: lastBuildErrors,
    });
}

function normalizeSymbolToken(raw: string | null | undefined): string | undefined {
    if (!raw) return undefined;
    const cleaned = raw
        .trim()
        .replace(/^['"`]+|['"`]+$/g, '')
        .replace(/[,:;(){}\[\]]+$/g, '');
    if (!cleaned) return undefined;
    const lower = cleaned.toLowerCase();
    if (IGNORED_SYMBOL_TOKENS.has(lower)) return undefined;
    return cleaned;
}

function extractSymbolAtPosition(
    document: vscode.TextDocument,
    position: vscode.Position,
): string | undefined {
    const range = document.getWordRangeAtPosition(position, SYMBOL_TOKEN_RE);
    if (range) {
        const direct = normalizeSymbolToken(document.getText(range));
        if (direct) return direct;
    }

    // Context-menu clicks often land on whitespace; in that case, pick the closest
    // symbol token on the same line so "Show in Schematic" still targets intent.
    const lineText = document.lineAt(position.line).text;
    const tokenPattern = /[A-Za-z_][A-Za-z0-9_\[\]\.]*/g;
    let bestToken: string | undefined;
    let bestDistance = Number.POSITIVE_INFINITY;
    let bestStart = -1;
    let match: RegExpExecArray | null;

    while ((match = tokenPattern.exec(lineText)) !== null) {
        const token = normalizeSymbolToken(match[0]);
        if (!token) continue;

        const start = match.index;
        const end = start + match[0].length;
        let distance = 0;
        if (position.character < start) {
            distance = start - position.character;
        } else if (position.character > end) {
            distance = position.character - end;
        }

        // Tie-break toward tokens to the left of the cursor, since right-click
        // usually happens just after the identifier in source code lines.
        const isBetter = distance < bestDistance
            || (
                distance === bestDistance
                && start <= position.character
                && start > bestStart
            );
        if (isBetter) {
            bestDistance = distance;
            bestStart = start;
            bestToken = token;
        }
    }

    return bestToken;
}

function postShowInSchematicRequest(request: ShowInSchematicRequest): void {
    if (!schematicViewer?.isOpen()) return;
    const message = { type: 'showInSchematic', ...request };
    schematicViewer.postMessage(message);
    // Re-send once shortly after to survive first-load race conditions.
    setTimeout(() => {
        if (!schematicViewer?.isOpen()) return;
        schematicViewer.postMessage(message);
    }, 220);
}

async function showInSchematicFromEditor(
    uri?: vscode.Uri,
    positionOrRange?: vscode.Position | vscode.Range,
): Promise<void> {
    let editor = vscode.window.activeTextEditor;

    if (uri) {
        const existing = vscode.window.visibleTextEditors.find(
            (candidate) => candidate.document.uri.toString() === uri.toString(),
        );
        if (existing) {
            editor = existing;
        } else {
            const doc = await vscode.workspace.openTextDocument(uri);
            editor = await vscode.window.showTextDocument(doc, {
                viewColumn: vscode.ViewColumn.Active,
                preserveFocus: true,
                preview: false,
            });
        }
    }

    if (!editor) {
        void vscode.window.showInformationMessage('Open an .ato file first.');
        return;
    }

    if (editor.document.languageId !== 'ato') {
        void vscode.window.showInformationMessage(
            'Show in Schematic is only available for .ato files.',
        );
        return;
    }

    const position = positionOrRange instanceof vscode.Range
        ? positionOrRange.start
        : positionOrRange ?? editor.selection.active;

    const request: ShowInSchematicRequest = {
        filePath: editor.document.uri.fsPath,
        line: position.line + 1,
        column: position.character + 1,
    };
    const symbol = extractSymbolAtPosition(editor.document, position);
    if (symbol) {
        request.symbol = symbol;
    }

    await openSchematicPreview();
    postShowInSchematicRequest(request);
}

const showInSchematicCodeActionProvider: vscode.CodeActionProvider = {
    provideCodeActions(
        document: vscode.TextDocument,
        range: vscode.Range | vscode.Selection,
        _context: vscode.CodeActionContext,
        _token: vscode.CancellationToken,
    ): vscode.CodeAction[] {
        if (document.languageId !== 'ato') return [];
        const action = new vscode.CodeAction(
            'Show in Schematic',
            vscode.CodeActionKind.QuickFix,
        );
        action.command = {
            command: SHOW_IN_SCHEMATIC_COMMAND,
            title: 'Show in Schematic',
            arguments: [document.uri, range.start],
        };
        action.isPreferred = true;
        return [action];
    },
};

export async function openSchematicPreview() {
    if (!schematicViewer) {
        schematicViewer = new SchematicWebview();
    }
    await schematicViewer.open();

    // Always seed from the currently selected schematic to avoid stale
    // last-successful snapshots when switching targets/projects.
    sendSchematicUpdate(true);
    void pushSchematicArtifactsToWebview();

    setTimeout(() => {
        pushBuildStateAndErrorsToWebview();
    }, 150);
}

export function closeSchematicPreview() {
    schematicViewer?.dispose();
    schematicViewer = undefined;
}

/**
 * Notify the schematic viewer of the currently active editor file.
 * Used for bidirectional source highlighting.
 */
export function notifyActiveFile(filePath: string | null) {
    schematicViewer?.postMessage({ type: 'activeFile', filePath });
}

export async function activate(context: vscode.ExtensionContext) {
    context.subscriptions.push(
        vscode.commands.registerCommand(
            SHOW_IN_SCHEMATIC_COMMAND,
            (uri?: vscode.Uri, positionOrRange?: vscode.Position | vscode.Range) =>
                showInSchematicFromEditor(uri, positionOrRange),
        ),
        vscode.languages.registerCodeActionsProvider(
            { language: 'ato' },
            showInSchematicCodeActionProvider,
            {
                providedCodeActionKinds: [vscode.CodeActionKind.QuickFix],
            },
        ),
        onSchematicChanged((_) => {
            if (schematicViewer?.isOpen()) {
                // Skip reload when the change was triggered by our own position save
                if (schematicViewer.shouldSuppressReload()) {
                    return;
                }
                // For external changes (rebuild), send data via message
                // to preserve navigation state instead of replacing HTML.
                sendSchematicUpdate(true);
            }
        }),
        vscode.workspace.onDidSaveTextDocument((document) => {
            if (!shouldAutoBuildForSave(document)) return;
            scheduleAutoSchematicBuild();
        }),
        // Track active editor for bidirectional navigation
        vscode.window.onDidChangeActiveTextEditor((editor) => {
            if (schematicViewer?.isOpen()) {
                const filePath = editor?.document?.uri?.fsPath ?? null;
                notifyActiveFile(filePath);
            }
        }),
    );
}

export function deactivate() {
    clearBuildDebounce();
    closeSchematicPreview();
}
