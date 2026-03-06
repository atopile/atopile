/**
 * Shared VS Code API instance.
 *
 * acquireVsCodeApi() can only be called once per webview.
 * Import `vscode` from this module instead of calling it directly.
 */
export const vscode = acquireVsCodeApi();

class WebviewRequestBroker {
  private _pendingRequests = new Map<
    string,
    {
      resolve: (value: unknown) => void;
      reject: (error: Error) => void;
    }
  >();
  private _requestCounter = 0;

  constructor() {
    window.addEventListener("message", (event: MessageEvent) => {
      this._handleMessage(event);
    });
  }

  request<T>(type: string, payload: Record<string, unknown> = {}): Promise<T> {
    const requestId = `req-${this._requestCounter++}`;
    return new Promise<T>((resolve, reject) => {
      this._pendingRequests.set(requestId, { resolve, reject });
      vscode.postMessage({
        ...payload,
        requestId,
        type,
      });
    });
  }

  private _handleMessage(event: MessageEvent): void {
    const data = event.data as {
      type?: unknown;
      requestId?: unknown;
      ok?: unknown;
      result?: unknown;
      error?: unknown;
    };
    if (data.type !== "response" || typeof data.requestId !== "string") {
      return;
    }

    const pending = this._pendingRequests.get(data.requestId);
    if (!pending) {
      return;
    }
    this._pendingRequests.delete(data.requestId);

    if (data.ok === false) {
      pending.reject(new Error(typeof data.error === "string" ? data.error : "Request failed"));
      return;
    }

    pending.resolve(data.result);
  }
}

export const requestBroker = new WebviewRequestBroker();

class WebviewConsoleBridge {
  private readonly _origLog = console.log;
  private readonly _origWarn = console.warn;
  private readonly _origError = console.error;

  install(): void {
    console.log = (...args: unknown[]) => {
      this._origLog.apply(console, args);
      this._forward("log", args);
    };
    console.warn = (...args: unknown[]) => {
      this._origWarn.apply(console, args);
      this._forward("warn", args);
    };
    console.error = (...args: unknown[]) => {
      this._origError.apply(console, args);
      this._forward("error", args);
    };
  }

  private _forward(level: "log" | "warn" | "error", args: unknown[]): void {
    const message = args
      .map((a) => (typeof a === "string" ? a : JSON.stringify(a)))
      .join(" ");
    vscode.postMessage({ type: "log", level, message });
  }
}

new WebviewConsoleBridge().install();
