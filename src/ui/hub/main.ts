/**
 * Hub entry point — reads configuration from environment variables,
 * wires up store, webview socket, and core socket, then starts.
 */

import { Store } from "./store";
import { WebviewWebSocketServer } from "./webviewWebSocketServer";
import { CoreWebSocketClient } from "./coreWebSocketClient";
import { requirePort } from "./utils";

const HUB_READY_MARKER = "ATOPILE_HUB_READY";

// -- Globals ------------------------------------------------------------------

export const store = new Store();
export const webviewSocket = new WebviewWebSocketServer();
export const coreSocket = new CoreWebSocketClient();

// -- Hub ----------------------------------------------------------------------

class Hub {
  private _hubPort: number;
  private _workspaceFolders: string[];

  constructor() {
    this._hubPort = requirePort("ATOPILE_HUB_PORT");
    const coreServerPort = requirePort("ATOPILE_CORE_SERVER_PORT");
    this._workspaceFolders = (process.env.ATOPILE_WORKSPACE_FOLDERS ?? "")
      .split(":")
      .filter(Boolean);

    store.set("coreStatus", { coreServerPort });

    webviewSocket
      .start(this._hubPort)
      .then(() => {
        coreSocket.start(coreServerPort, () => this._onCoreConnected());
        console.log(HUB_READY_MARKER);
      })
      .catch((err) => {
        console.error(`Hub failed to start: ${err}`);
        process.exit(1);
      });
  }

  shutdown(): void {
    coreSocket.stop();
    webviewSocket.stop();
    process.exit(0);
  }

  private _onCoreConnected(): void {
    coreSocket.sendAction("discoverProjects", { paths: this._workspaceFolders });
  }
}

// -- Entry point --------------------------------------------------------------

const hub = new Hub();

process.on("SIGTERM", () => hub.shutdown());
process.on("SIGINT", () => hub.shutdown());
