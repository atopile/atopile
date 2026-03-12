export interface RpcTransport {
  onMessage: ((data: string) => void) | null;
  onOpen: (() => void) | null;
  onClose: (() => void) | null;
  connect(): void;
  send(data: string): void;
  close(): void;
}

export interface SocketLike {
  readyState: number;
  send(data: string): void;
  close(): void;
  onopen: ((ev: any) => void) | null;
  onmessage: ((ev: { data: any }) => void) | null;
  onclose: ((ev: any) => void) | null;
  onerror: ((ev: any) => void) | null;
}
