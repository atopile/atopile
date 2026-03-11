import { RpcTransport, type SocketLike } from "./rpcTransport";

export class WebSocketTransport implements RpcTransport {
  onMessage: ((data: string) => void) | null = null;
  onOpen: (() => void) | null = null;
  onClose: (() => void) | null = null;

  private readonly _create: () => SocketLike;
  private _socket: SocketLike | null = null;

  constructor(create: () => SocketLike) {
    this._create = create;
  }

  connect(): void {
    if (this._socket) {
      this._socket.close();
    }

    const socket = this._create();
    this._socket = socket;

    socket.onopen = () => {
      this.onOpen?.();
    };

    socket.onmessage = (event) => {
      this.onMessage?.(typeof event.data === "string" ? event.data : String(event.data));
    };

    socket.onclose = () => {
      this._socket = null;
      this.onClose?.();
    };

    socket.onerror = () => {};
  }

  send(data: string): void {
    if (!this._socket || this._socket.readyState !== 1) {
      throw new Error("Transport is not connected");
    }
    this._socket.send(data);
  }

  close(): void {
    if (!this._socket) {
      return;
    }
    this._socket.close();
    this._socket = null;
  }
}
