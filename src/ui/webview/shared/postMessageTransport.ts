import type { RpcTransport } from "../../shared/rpcTransport";
import { getVscodeApi } from "./vscodeApi";

export class PostMessageTransport implements RpcTransport {
  onMessage: ((data: string) => void) | null = null;
  onOpen: (() => void) | null = null;
  onClose: (() => void) | null = null;

  private _connected = false;
  private _listening = false;

  connect(): void {
    if (this._listening) {
      return;
    }
    this._listening = true;
    window.addEventListener("message", this._handleMessage);
  }

  send(data: string): void {
    const vscode = getVscodeApi();
    if (!vscode) {
      throw new Error("VS Code API is not available");
    }
    vscode.postMessage({ type: "rpc:send", data });
  }

  close(): void {
    if (!this._listening) {
      return;
    }
    this._listening = false;
    this._connected = false;
    window.removeEventListener("message", this._handleMessage);
  }

  private readonly _handleMessage = (event: MessageEvent) => {
    const message = event.data as {
      type?: unknown;
      data?: unknown;
    };

    if (message.type === "rpc:open") {
      this._connected = true;
      this.onOpen?.();
      return;
    }

    if (message.type === "rpc:close") {
      this._connected = false;
      this.onClose?.();
      return;
    }

    if (message.type === "rpc:recv" && typeof message.data === "string") {
      this.onMessage?.(message.data);
    }
  };
}
