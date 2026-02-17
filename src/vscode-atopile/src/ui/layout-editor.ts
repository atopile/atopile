import * as vscode from 'vscode';
import { getAndCheckResource } from '../common/resources';
import { backendServer } from '../common/backendServer';
import { getWsOrigin, getNonce } from '../common/webview';
import { BaseWebview } from './webview-base';
import { WebSocket as NodeWebSocket } from 'ws';

interface FetchProxyRequest {
    type: 'fetchProxy';
    id: number;
    url: string;
    method?: string;
    headers?: Record<string, string>;
    body?: string;
}

interface WsProxyConnect {
    type: 'wsProxyConnect';
    id: number;
    url: string;
}

interface WsProxySend {
    type: 'wsProxySend';
    id: number;
    data: string;
}

interface WsProxyClose {
    type: 'wsProxyClose';
    id: number;
    code?: number;
    reason?: string;
}

class LayoutEditorWebview extends BaseWebview {
    private messageDisposable?: vscode.Disposable;
    private wsProxies: Map<number, NodeWebSocket> = new Map();

    constructor() {
        super({
            id: 'layout_editor',
            title: 'Layout',
            iconName: 'pcb-icon-transparent.svg',
        });
    }

    protected setupPanel(): void {
        if (!this.panel) {
            return;
        }
        this.messageDisposable = this.panel.webview.onDidReceiveMessage((message: unknown) => {
            if (!message || typeof message !== 'object' || !('type' in message)) {
                return;
            }
            const msg = message as { type?: string };
            switch (msg.type) {
                case 'fetchProxy':
                    this.handleFetchProxy(message as FetchProxyRequest);
                    break;
                case 'wsProxyConnect':
                    this.handleWsProxyConnect(message as WsProxyConnect);
                    break;
                case 'wsProxySend':
                    this.handleWsProxySend(message as WsProxySend);
                    break;
                case 'wsProxyClose':
                    this.handleWsProxyClose(message as WsProxyClose);
                    break;
                default:
                    break;
            }
        });
    }

    protected onDispose(): void {
        this.messageDisposable?.dispose();
        this.messageDisposable = undefined;
        for (const ws of this.wsProxies.values()) {
            ws.removeAllListeners();
            ws.close();
        }
        this.wsProxies.clear();
    }

    private postToWebview(message: Record<string, unknown>): void {
        this.panel?.webview.postMessage(message);
    }

    private handleFetchProxy(req: FetchProxyRequest): void {
        const init: Record<string, unknown> = {
            method: req.method ?? 'GET',
            headers: req.headers ?? {},
        };
        if (req.body && req.method !== 'GET' && req.method !== 'HEAD') {
            init.body = req.body;
        }

        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (globalThis as any).fetch(req.url, init)
            .then(async (response: { text: () => Promise<string>; status: number; statusText: string; headers: { forEach: (cb: (value: string, key: string) => void) => void } }) => {
                const body = await response.text();
                const headers: Record<string, string> = {};
                response.headers.forEach((value: string, key: string) => {
                    headers[key] = value;
                });
                this.postToWebview({
                    type: 'fetchProxyResult',
                    id: req.id,
                    status: response.status,
                    statusText: response.statusText,
                    headers,
                    body,
                });
            })
            .catch((err: Error) => {
                this.postToWebview({
                    type: 'fetchProxyResult',
                    id: req.id,
                    error: String(err),
                });
            });
    }

    private handleWsProxyConnect(msg: WsProxyConnect): void {
        const existing = this.wsProxies.get(msg.id);
        if (existing) {
            existing.removeAllListeners();
            existing.close();
            this.wsProxies.delete(msg.id);
        }

        let targetUrl = msg.url;
        try {
            const parsed = new URL(msg.url);
            const internalBase = backendServer.internalApiUrl || backendServer.apiUrl;
            if (internalBase) {
                const internal = new URL(internalBase);
                const wsProtocol = internal.protocol === 'https:' ? 'wss:' : 'ws:';
                const port = internal.port ? `:${internal.port}` : '';
                targetUrl = `${wsProtocol}//${internal.hostname}${port}${parsed.pathname}${parsed.search}`;
            }
        } catch {
            // Use URL as-is on parse failures.
        }

        const ws = new NodeWebSocket(targetUrl);
        ws.on('open', () => {
            this.postToWebview({ type: 'wsProxyOpen', id: msg.id });
        });
        ws.on('message', (data: Buffer | string) => {
            const payload = typeof data === 'string' ? data : data.toString('utf-8');
            this.postToWebview({ type: 'wsProxyMessage', id: msg.id, data: payload });
        });
        ws.on('close', (code: number, reason: Buffer) => {
            this.wsProxies.delete(msg.id);
            this.postToWebview({
                type: 'wsProxyClose',
                id: msg.id,
                code,
                reason: reason.toString('utf-8'),
            });
        });
        ws.on('error', (err: Error) => {
            this.postToWebview({ type: 'wsProxyError', id: msg.id, error: err.message });
        });

        this.wsProxies.set(msg.id, ws);
    }

    private handleWsProxySend(msg: WsProxySend): void {
        const ws = this.wsProxies.get(msg.id);
        if (ws?.readyState === NodeWebSocket.OPEN) {
            ws.send(msg.data);
        }
    }

    private handleWsProxyClose(msg: WsProxyClose): void {
        const ws = this.wsProxies.get(msg.id);
        if (ws) {
            ws.close(msg.code ?? 1000, msg.reason ?? '');
            this.wsProxies.delete(msg.id);
        }
    }

    protected getHtmlContent(webview: vscode.Webview): string {
        const apiUrl = backendServer.apiUrl;
        const wsOrigin = getWsOrigin(backendServer.wsUrl);
        const nonce = getNonce();

        const editorUri = `${webview.asWebviewUri(
            vscode.Uri.file(getAndCheckResource('layout-editor/editor.js'))
        ).toString()}?v=${Date.now()}`;

        return /* html */ `
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8" />
                <meta name="viewport" content="width=device-width, initial-scale=1.0" />
                <meta http-equiv="Content-Security-Policy" content="
                    default-src 'none';
                    style-src 'unsafe-inline';
                    script-src 'nonce-${nonce}' ${webview.cspSource};
                    connect-src ${webview.cspSource} ${apiUrl} ${wsOrigin} ws: wss:;
                ">
                <title>Layout Editor</title>
                <style>
                    html, body {
                        padding: 0; margin: 0;
                        height: 100%; width: 100%;
                        overflow: hidden;
                        background: var(--vscode-editor-background, #1e1e1e);
                    }
                    canvas { display: block; width: 100%; height: 100%; }
                    #status {
                        position: fixed; bottom: 8px; left: 8px;
                        color: var(--vscode-descriptionForeground, #aaa);
                        font: 12px monospace;
                        pointer-events: none; z-index: 10;
                    }
                    #layer-panel {
                        position: fixed; top: 0; right: 0; bottom: 0;
                        width: 140px;
                        background: var(--vscode-sideBar-background, rgba(30,30,30,0.95));
                        border-left: 1px solid var(--vscode-panel-border, #444);
                        border-radius: 4px 0 0 4px;
                        z-index: 20;
                        font: 11px/1.4 monospace;
                        color: var(--vscode-foreground, #ccc);
                        transform: translateX(0);
                        transition: transform 0.2s ease;
                        display: flex;
                        flex-direction: column;
                    }
                    #layer-panel.collapsed {
                        transform: translateX(100%);
                    }
                    .layer-panel-header {
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        padding: 6px 8px;
                        font-weight: bold;
                        font-size: 12px;
                        border-bottom: 1px solid var(--vscode-panel-border, #444);
                        flex-shrink: 0;
                    }
                    .layer-collapse-btn {
                        cursor: pointer;
                        opacity: 0.6;
                        font-size: 10px;
                    }
                    .layer-collapse-btn:hover { opacity: 1; }
                    .layer-expand-tab {
                        display: none;
                        position: fixed;
                        top: 50%;
                        right: 0;
                        transform: translateY(-50%);
                        writing-mode: vertical-rl;
                        background: var(--vscode-sideBar-background, rgba(30,30,30,0.95));
                        border: 1px solid var(--vscode-panel-border, #444);
                        border-right: none;
                        border-radius: 4px 0 0 4px;
                        padding: 8px 4px;
                        cursor: pointer;
                        font: 11px monospace;
                        color: var(--vscode-foreground, #ccc);
                        z-index: 21;
                    }
                    .layer-expand-tab.visible { display: block; }
                    .layer-panel-content {
                        overflow-y: auto;
                        padding: 4px 0;
                        flex: 1;
                    }
                    .layer-group-header {
                        display: flex;
                        align-items: center;
                        gap: 4px;
                        padding: 2px 8px;
                        cursor: pointer;
                        font-weight: 600;
                        transition: opacity 0.15s;
                    }
                    .layer-group-header:hover { background: var(--vscode-list-hoverBackground, rgba(255,255,255,0.05)); }
                    .layer-chevron {
                        font-size: 10px;
                        width: 10px;
                        text-align: center;
                        flex-shrink: 0;
                    }
                    .layer-group-name { flex: 1; }
                    .layer-group-children { padding-left: 22px; }
                    .layer-row {
                        display: flex;
                        align-items: center;
                        gap: 5px;
                        padding: 1px 8px;
                        cursor: pointer;
                        transition: opacity 0.15s;
                    }
                    .layer-row:hover { background: var(--vscode-list-hoverBackground, rgba(255,255,255,0.05)); }
                    .layer-top-level { padding-left: 22px; }
                    .layer-swatch {
                        display: inline-block;
                        width: 10px; height: 10px;
                        border-radius: 50%;
                        flex-shrink: 0;
                    }
                </style>
            </head>
            <body>
                <script nonce="${nonce}">
                    window.__LAYOUT_BASE_URL__ = '${apiUrl}';
                    window.__LAYOUT_API_PREFIX__ = '/api/layout';
                    window.__LAYOUT_WS_PATH__ = '/ws/layout';
                </script>
                <script nonce="${nonce}">
                    // Fetch/WS bridge for browser-hosted webviews (OpenVSCode Server).
                    (function() {
                        var originalAcquire = window.acquireVsCodeApi;
                        var vsCodeApi = null;
                        if (typeof originalAcquire === 'function') {
                            window.acquireVsCodeApi = function() {
                                if (!vsCodeApi) {
                                    vsCodeApi = originalAcquire();
                                }
                                return vsCodeApi;
                            };
                        }

                        function getVsCodeApi() {
                            try {
                                return vsCodeApi || (window.acquireVsCodeApi ? window.acquireVsCodeApi() : null);
                            } catch {
                                return null;
                            }
                        }

                        function resolveFallbackWsUrl(url) {
                            try {
                                var parsed = new URL(url, window.location.href);
                                if (parsed.hostname !== 'localhost' && parsed.hostname !== '127.0.0.1') {
                                    return url;
                                }

                                var parentOrigin = '';
                                try {
                                    var params = new URLSearchParams(window.location.search);
                                    parentOrigin = params.get('parentOrigin') || '';
                                    if (parentOrigin) parentOrigin = decodeURIComponent(parentOrigin);
                                } catch {}

                                if (!parentOrigin && document.referrer) {
                                    try {
                                        parentOrigin = new URL(document.referrer).origin;
                                    } catch {}
                                }

                                if (!parentOrigin) {
                                    return url;
                                }

                                var parent = new URL(parentOrigin);
                                var wsProtocol = parent.protocol === 'https:' ? 'wss:' : 'ws:';
                                return wsProtocol + '//' + parent.host + parsed.pathname + parsed.search;
                            } catch {
                                return url;
                            }
                        }

                        var backendBase = '${apiUrl}';
                        var originalFetch = window.fetch;
                        var fetchId = 0;
                        var pendingFetch = new Map();

                        function normalizeHeaders(headers) {
                            if (!headers) return {};
                            if (typeof Headers !== 'undefined' && headers instanceof Headers) {
                                var out = {};
                                headers.forEach(function(v, k) { out[k] = v; });
                                return out;
                            }
                            if (Array.isArray(headers)) {
                                var outArray = {};
                                for (var i = 0; i < headers.length; i++) {
                                    var entry = headers[i];
                                    if (Array.isArray(entry) && entry.length >= 2) {
                                        outArray[String(entry[0])] = String(entry[1]);
                                    }
                                }
                                return outArray;
                            }
                            return headers;
                        }

                        window.addEventListener('message', function(event) {
                            var msg = event.data;
                            if (!msg || !msg.type) return;
                            if (msg.type === 'fetchProxyResult' && pendingFetch.has(msg.id)) {
                                var handler = pendingFetch.get(msg.id);
                                pendingFetch.delete(msg.id);
                                handler(msg);
                            }
                        });

                        window.fetch = function(input, init) {
                            var url = typeof input === 'string' ? input : (input instanceof Request ? input.url : String(input));
                            if (!url.startsWith(backendBase)) {
                                return originalFetch.apply(this, arguments);
                            }

                            return new Promise(function(resolve, reject) {
                                var id = ++fetchId;
                                var timeout = setTimeout(function() {
                                    pendingFetch.delete(id);
                                    reject(new TypeError('Fetch proxy timeout'));
                                }, 30000);

                                pendingFetch.set(id, function(msg) {
                                    clearTimeout(timeout);
                                    if (msg.error) {
                                        reject(new TypeError(msg.error));
                                        return;
                                    }
                                    resolve(new Response(msg.body, {
                                        status: msg.status || 200,
                                        statusText: msg.statusText || 'OK',
                                        headers: msg.headers || {},
                                    }));
                                });

                                var api = getVsCodeApi();
                                if (!api) {
                                    clearTimeout(timeout);
                                    pendingFetch.delete(id);
                                    originalFetch.apply(window, [input, init]).then(resolve, reject);
                                    return;
                                }

                                try {
                                    api.postMessage({
                                        type: 'fetchProxy',
                                        id: id,
                                        url: url,
                                        method: (init && init.method) || 'GET',
                                        headers: normalizeHeaders(init && init.headers),
                                        body: (init && init.body) || null,
                                    });
                                } catch {
                                    clearTimeout(timeout);
                                    pendingFetch.delete(id);
                                    originalFetch.apply(window, [input, init]).then(resolve, reject);
                                }
                            });
                        };

                        function createCompatEvent(type, init) {
                            var evt;
                            try {
                                if (type === 'message' && typeof MessageEvent === 'function') {
                                    evt = new MessageEvent('message', { data: init && init.data });
                                } else if (type === 'close' && typeof CloseEvent === 'function') {
                                    evt = new CloseEvent('close', {
                                        code: (init && init.code) || 1000,
                                        reason: (init && init.reason) || '',
                                        wasClean: true,
                                    });
                                } else {
                                    evt = new Event(type);
                                }
                            } catch {
                                evt = document.createEvent('Event');
                                evt.initEvent(type, false, false);
                            }
                            if (init && init.data !== undefined && evt.data === undefined) evt.data = init.data;
                            if (init && init.code !== undefined && evt.code === undefined) evt.code = init.code;
                            if (init && init.reason !== undefined && evt.reason === undefined) evt.reason = init.reason;
                            return evt;
                        }

                        function createProxySocket(url, id) {
                            var listeners = { open: [], message: [], close: [], error: [] };
                            var target = {
                                _readyState: 0,
                                url: url,
                                onopen: null,
                                onmessage: null,
                                onclose: null,
                                onerror: null,
                                CONNECTING: 0,
                                OPEN: 1,
                                CLOSING: 2,
                                CLOSED: 3,
                                addEventListener: function(type, cb) {
                                    if (!listeners[type] || typeof cb !== 'function') return;
                                    listeners[type].push(cb);
                                },
                                removeEventListener: function(type, cb) {
                                    if (!listeners[type]) return;
                                    listeners[type] = listeners[type].filter(function(fn) { return fn !== cb; });
                                },
                                dispatchEvent: function(evt) {
                                    var type = evt && evt.type ? evt.type : '';
                                    var fns = listeners[type] || [];
                                    for (var i = 0; i < fns.length; i++) {
                                        try { fns[i](evt); } catch {}
                                    }
                                    return true;
                                },
                                send: function(data) {
                                    var api = getVsCodeApi();
                                    if (api) api.postMessage({ type: 'wsProxySend', id: id, data: data });
                                },
                                close: function(code, reason) {
                                    target._readyState = 2;
                                    var api = getVsCodeApi();
                                    if (api) api.postMessage({ type: 'wsProxyClose', id: id, code: code, reason: reason });
                                },
                            };
                            Object.defineProperty(target, 'readyState', {
                                get: function() { return target._readyState; },
                            });
                            return target;
                        }

                        var wsProxyId = 0;
                        var wsProxyInstances = new Map();
                        var NativeWebSocket = window.WebSocket;

                        window.addEventListener('message', function(event) {
                            var msg = event.data;
                            if (!msg || !msg.type) return;
                            var instance = msg.id != null ? wsProxyInstances.get(msg.id) : null;
                            if (!instance) return;
                            switch (msg.type) {
                                case 'wsProxyOpen': {
                                    instance._readyState = 1;
                                    var openEvt = createCompatEvent('open');
                                    if (instance.onopen) instance.onopen(openEvt);
                                    instance.dispatchEvent(openEvt);
                                    break;
                                }
                                case 'wsProxyMessage': {
                                    var msgEvt = createCompatEvent('message', { data: msg.data });
                                    if (instance.onmessage) instance.onmessage(msgEvt);
                                    instance.dispatchEvent(msgEvt);
                                    break;
                                }
                                case 'wsProxyClose': {
                                    instance._readyState = 3;
                                    var closeEvt = createCompatEvent('close', { code: msg.code || 1000, reason: msg.reason || '' });
                                    if (instance.onclose) instance.onclose(closeEvt);
                                    instance.dispatchEvent(closeEvt);
                                    wsProxyInstances.delete(msg.id);
                                    break;
                                }
                                case 'wsProxyError': {
                                    var errEvt = createCompatEvent('error');
                                    if (instance.onerror) instance.onerror(errEvt);
                                    instance.dispatchEvent(errEvt);
                                    break;
                                }
                            }
                        });

                        function ProxyWebSocket(url, protocols) {
                            var api = getVsCodeApi();
                            if (!api && typeof NativeWebSocket === 'function') {
                                var fallbackUrl = resolveFallbackWsUrl(url);
                                return protocols !== undefined
                                    ? new NativeWebSocket(fallbackUrl, protocols)
                                    : new NativeWebSocket(fallbackUrl);
                            }

                            var id = ++wsProxyId;
                            var target = createProxySocket(url, id);
                            wsProxyInstances.set(id, target);
                            if (api) {
                                try {
                                    api.postMessage({ type: 'wsProxyConnect', id: id, url: url });
                                } catch {
                                    wsProxyInstances.delete(id);
                                    if (typeof NativeWebSocket === 'function') {
                                        var fallbackUrl = resolveFallbackWsUrl(url);
                                        return protocols !== undefined
                                            ? new NativeWebSocket(fallbackUrl, protocols)
                                            : new NativeWebSocket(fallbackUrl);
                                    }
                                }
                            }
                            return target;
                        }
                        ProxyWebSocket.CONNECTING = 0;
                        ProxyWebSocket.OPEN = 1;
                        ProxyWebSocket.CLOSING = 2;
                        ProxyWebSocket.CLOSED = 3;
                        window.WebSocket = ProxyWebSocket;
                    })();
                </script>
                <canvas id="editor-canvas"></canvas>
                <div id="layer-panel"></div>
                <div id="status">scroll to zoom, middle-click to pan, left-click to select/drag, R rotate, F flip</div>
                <script nonce="${nonce}" type="module" src="${editorUri}"></script>
            </body>
            </html>`;
    }
}

let layoutEditor: LayoutEditorWebview | undefined;

export async function openLayoutEditor() {
    if (!layoutEditor) {
        layoutEditor = new LayoutEditorWebview();
    }
    await layoutEditor.open();
}

export function closeLayoutEditor() {
    layoutEditor?.dispose();
    layoutEditor = undefined;
}

export async function activate(_context: vscode.ExtensionContext) {
    // Nothing extra needed — the webview is opened on demand.
}

export function deactivate() {
    closeLayoutEditor();
}
