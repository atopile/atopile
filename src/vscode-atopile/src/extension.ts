import * as vscode from "vscode";
import { ProcessManager } from "./processManager";
import { WebviewManager } from "./webviewManager";
import {
  findFreePort,
  HUB_READY_MARKER,
  CORE_SERVER_READY_MARKER,
  HUB_PORT_ENV,
  CORE_SERVER_PORT_ENV,
} from "./constants";

const panels = [
  { id: "panel-developer", label: "Developer" },
  { id: "panel-b", label: "Panel B" },
];

let hub: ProcessManager | undefined;
let coreServer: ProcessManager | undefined;
let webviewManager: WebviewManager | undefined;

export async function activate(context: vscode.ExtensionContext): Promise<void> {
  const output = vscode.window.createOutputChannel("atopile");

  output.appendLine("atopile extension activating");

  // 1. Assign all ports upfront
  const hubPort = await findFreePort();
  const coreServerPort = await findFreePort();

  // Shared env — both processes know both ports
  const portEnv = {
    [HUB_PORT_ENV]: String(hubPort),
    [CORE_SERVER_PORT_ENV]: String(coreServerPort),
  };

  // 2. Start hub (fast Python process)
  hub = new ProcessManager(output, {
    name: "Hub",
    command: "ato",
    args: ["serve", "hub"],
    readyMarker: HUB_READY_MARKER,
    env: portEnv,
    timeoutMs: 10_000,
  });
  await hub.start();

  // 3. Register webviews + commands BEFORE the slow coreServer.start(),
  //    so VS Code can resolve the sidebar view immediately.
  webviewManager = new WebviewManager(context.extensionUri, hubPort);

  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider(
      WebviewManager.sidebarViewId,
      webviewManager
    ),
    vscode.commands.registerCommand("atopile.openPanel", async () => {
      const pick = await vscode.window.showQuickPick(
        panels.map((p) => ({ label: p.label, id: p.id })),
        { placeHolder: "Select a panel to open" }
      );
      if (pick) {
        webviewManager?.openPanel(pick.id);
      }
    }),
    vscode.commands.registerCommand("atopile.restart", async () => {
      if (!coreServer) return;
      try {
        await coreServer.restart();
        vscode.window.showInformationMessage("atopile core server restarted");
      } catch (err: any) {
        vscode.window.showErrorMessage(
          `Failed to restart core server: ${err.message}`
        );
      }
    }),
    hub,
    output
  );

  // 4. Start core server (slow)
  coreServer = new ProcessManager(output, {
    name: "CoreServer",
    command: "ato",
    args: ["serve", "core"],
    readyMarker: CORE_SERVER_READY_MARKER,
    env: portEnv,
  });
  context.subscriptions.push(coreServer);
  try {
    await coreServer.start();
  } catch (err: any) {
    output.appendLine(`[Extension] Core server failed to start: ${err.message}`);
    vscode.window.showWarningMessage(
      `atopile core server failed to start: ${err.message}`
    );
  }

  output.appendLine("atopile extension activated");
}

export function deactivate(): void {
  // Disposables are cleaned up by VS Code via context.subscriptions
}
