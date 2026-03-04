import type { ActionCommand, LayoutWsMessage, RenderModel, StatusResponse } from "./types";

type UpdateHandler = (message: LayoutWsMessage) => void;

function extractErrorMessage(payload: unknown, status: number): string {
    if (payload && typeof payload === "object") {
        const obj = payload as Record<string, unknown>;
        if (typeof obj.message === "string" && obj.message.trim()) {
            return obj.message;
        }
        if (typeof obj.detail === "string" && obj.detail.trim()) {
            return obj.detail;
        }
        if (Array.isArray(obj.detail)) {
            const parts = obj.detail
                .map(item => {
                    if (item && typeof item === "object") {
                        const entry = item as Record<string, unknown>;
                        if (typeof entry.msg === "string" && entry.msg.trim()) return entry.msg;
                    }
                    return "";
                })
                .filter(Boolean);
            if (parts.length > 0) {
                return parts.join("; ");
            }
        }
    }
    return `Request failed (${status})`;
}

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
        const postAction = async (payload: ActionCommand): Promise<Response> => fetch(`${this.baseUrl}${this.apiPrefix}/execute-action`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        const resp = await postAction(action);

        let payload: unknown = null;
        try {
            payload = await resp.json();
        } catch {
            payload = null;
        }

        if (
            payload
            && typeof payload === "object"
            && "status" in payload
            && (((payload as Record<string, unknown>).status) === "ok" || ((payload as Record<string, unknown>).status) === "error")
        ) {
            return payload as StatusResponse;
        }

        if (!resp.ok) {
            return {
                status: "error",
                code: `http_${resp.status}`,
                message: extractErrorMessage(payload, resp.status),
                delta: null,
                action_id: null,
            };
        }

        return {
            status: "error",
            code: "invalid_response",
            message: "Layout action response payload is missing status.",
            delta: null,
            action_id: null,
        };
    }

    connect(onUpdate: UpdateHandler): void {
        const wsUrl = this.baseUrl.replace(/^http/, "ws") + this.wsPath;
        this.ws = new WebSocket(wsUrl);
        this.ws.onopen = () => console.log("WS connected");
        this.ws.onmessage = (event) => {
            const msg = JSON.parse(event.data) as LayoutWsMessage;
            if (
                (msg.type === "layout_updated" && msg.model)
                || (msg.type === "layout_delta" && msg.delta)
            ) {
                onUpdate(msg);
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
