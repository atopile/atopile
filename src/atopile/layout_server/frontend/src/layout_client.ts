import type { ActionCommand, RenderModel, StatusResponse } from "./types";

type UpdateHandler = (model: RenderModel) => void;

export class LayoutClient {
    private readonly baseUrl: string;
    private readonly apiPrefix: string;
    private readonly wsPath: string;
    private ws: WebSocket | null = null;
    private reconnectTimer: number | null = null;

    constructor(baseUrl: string, apiPrefix = "/api", wsPath = "/ws") {
        this.baseUrl = baseUrl;
        this.apiPrefix = apiPrefix;
        this.wsPath = wsPath;
    }

    async fetchRenderModel(): Promise<RenderModel> {
        const resp = await fetch(`${this.baseUrl}${this.apiPrefix}/render-model`);
        return await resp.json() as RenderModel;
    }

    async executeAction(action: ActionCommand): Promise<StatusResponse> {
        const resp = await fetch(`${this.baseUrl}${this.apiPrefix}/execute-action`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(action),
        });
        return await resp.json() as StatusResponse;
    }

    async post(path: string): Promise<StatusResponse> {
        const resp = await fetch(`${this.baseUrl}${this.apiPrefix}${path}`, { method: "POST" });
        return await resp.json() as StatusResponse;
    }

    connect(onUpdate: UpdateHandler): void {
        const wsUrl = this.baseUrl.replace(/^http/, "ws") + this.wsPath;
        this.ws = new WebSocket(wsUrl);
        this.ws.onopen = () => console.log("WS connected");
        this.ws.onmessage = (event) => {
            const msg = JSON.parse(event.data) as { type?: string; model?: RenderModel };
            if (msg.type === "layout_updated" && msg.model) {
                onUpdate(msg.model);
            }
        };
        this.ws.onerror = (err) => console.error("WS error:", err);
        this.ws.onclose = () => {
            if (this.reconnectTimer !== null) {
                window.clearTimeout(this.reconnectTimer);
            }
            this.reconnectTimer = window.setTimeout(() => {
                this.reconnectTimer = null;
                this.connect(onUpdate);
            }, 2000);
        };
    }

    disconnect(): void {
        if (this.reconnectTimer !== null) {
            window.clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }
        if (this.ws) {
            this.ws.onclose = null;
            this.ws.close();
            this.ws = null;
        }
    }
}
