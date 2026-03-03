import * as path from "path";
import * as vscode from "vscode";
import { ProcessManager } from "./processManager";
import { WebviewManager } from "./webviewManager";
import { AtoResolver } from "./atoResolver";
import { HubWebSocketClient } from "./hubWebSocketClient";
import { findFreePort } from "../../ui/hub/utils";

const HUB_READY_MARKER = "ATOPILE_HUB_READY";
const CORE_SERVER_READY_MARKER = "ATOPILE_SERVER_READY";

const panels = [
  { id: "panel-developer", label: "Developer" },
  { id: "panel-b", label: "Panel B" },
];

let hub: ProcessManager | undefined;
let hubSocket: HubWebSocketClient | undefined;
let webviewManager: WebviewManager | undefined;

// -- Activate -----------------------------------------------------------------

export async function activate(context: vscode.ExtensionContext): Promise<void> {
  const output = vscode.window.createOutputChannel("atopile");
  output.appendLine("atopile extension activating");

  const hubPort = await findFreePort();
  const coreServerPort = await findFreePort();

  const portEnv = {
    ATOPILE_HUB_PORT: String(hubPort),
    ATOPILE_CORE_SERVER_PORT: String(coreServerPort),
  };

  hub = await startHub(context, output, hubPort, coreServerPort, portEnv);
  hubSocket = await connectHub(hubPort);

  const version: string = context.extension.packageJSON.version;
  const resolver = new AtoResolver(context, output);
  const resolved = await resolveAtoBinary(resolver, version, output);
  if (!resolved) return;

  webviewManager = new WebviewManager(context.extensionUri, hubPort, coreServerPort, output);
  hubSocket.sendAction("resolverInfo", {
    uvPath: resolved.command,
    atoBinary: resolved.atoBinary ?? "",
    mode: resolved.isLocal ? "local" : "production",
    version,
  });

  registerCommands(context, webviewManager);
  context.subscriptions.push(hubSocket, hub, output);

  // Track active editor file for structure/context panels
  context.subscriptions.push(
    vscode.window.onDidChangeActiveTextEditor((editor) => {
      if (editor) {
        hubSocket?.sendAction("setActiveFile", { filePath: editor.document.uri.fsPath });
      }
    }),
  );
  // Send initial active file
  if (vscode.window.activeTextEditor) {
    hubSocket.sendAction("setActiveFile", {
      filePath: vscode.window.activeTextEditor.document.uri.fsPath,
    });
  }

  const coreServer = await startCoreServer(resolved, portEnv, output, hubSocket);
  context.subscriptions.push(coreServer);

  output.appendLine("atopile extension activated");
}

export function deactivate(): void {
  // Disposables (including hubSocket) are cleaned up by VS Code via context.subscriptions
}

// -- Helpers ------------------------------------------------------------------

async function startHub(
  context: vscode.ExtensionContext,
  output: vscode.OutputChannel,
  hubPort: number,
  coreServerPort: number,
  portEnv: Record<string, string>,
): Promise<ProcessManager> {
  const workspaceFolders =
    vscode.workspace.workspaceFolders?.map((f) => f.uri.fsPath).join(":") ?? "";

  const pm = new ProcessManager(output, {
    name: "Hub",
    command: "node",
    args: [path.join(context.extensionPath, "hub-dist", "main.js")],
    readyMarker: HUB_READY_MARKER,
    env: {
      ...portEnv,
      ATOPILE_WORKSPACE_FOLDERS: workspaceFolders,
    },
    timeoutMs: 10_000,
  });
  await pm.start();
  return pm;
}

async function connectHub(port: number): Promise<HubWebSocketClient> {
  const client = new HubWebSocketClient(port);
  await client.connect();
  return client;
}

async function resolveAtoBinary(
  resolver: AtoResolver,
  version: string,
  output: vscode.OutputChannel,
): Promise<Awaited<ReturnType<AtoResolver["resolve"]>> | null> {
  try {
    return await resolver.resolve(version);
  } catch (err: any) {
    output.appendLine(`[Extension] Failed to resolve ato binary: ${err.message}`);
    vscode.window.showWarningMessage(`atopile: ${err.message}`);
    return null;
  }
}

function registerCommands(
  context: vscode.ExtensionContext,
  wm: WebviewManager,
): void {
  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider(WebviewManager.sidebarViewId, wm, {
      webviewOptions: { retainContextWhenHidden: true },
    }),

    vscode.window.registerWebviewViewProvider(WebviewManager.logsViewId, wm, {
      webviewOptions: { retainContextWhenHidden: true },
    }),

    vscode.commands.registerCommand("atopile.openPanel", async () => {
      const pick = await vscode.window.showQuickPick(
        panels.map((p) => ({ label: p.label, id: p.id })),
        { placeHolder: "Select a panel to open" },
      );
      if (pick) wm.openPanel(pick.id);
    }),
  );
}

async function startCoreServer(
  resolved: Awaited<ReturnType<AtoResolver["resolve"]>>,
  portEnv: Record<string, string>,
  output: vscode.OutputChannel,
  hub: HubWebSocketClient,
): Promise<ProcessManager> {
  const pm = new ProcessManager(output, {
    name: "CoreServer",
    command: resolved.command,
    args: [...resolved.prefixArgs, "serve", "core"],
    readyMarker: CORE_SERVER_READY_MARKER,
    env: portEnv,
  });
  try {
    await pm.start();
  } catch (err: any) {
    output.appendLine(`[Extension] Core server failed to start: ${err.message}`);
    vscode.window.showWarningMessage(`atopile core server failed to start: ${err.message}`);
    hub.sendAction("coreStartupError", { message: err.message });
  }
  return pm;
}
