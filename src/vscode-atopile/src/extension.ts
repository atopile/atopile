import * as vscode from "vscode";
import { ProcessManager } from "./processManager";
import { AtoResolver } from "./atoResolver";
import { CoreClient } from "./coreClient";
import { RpcProxy } from "./rpcProxy";
import { findFreePort } from "./utils";
import { openKicadForBuild } from "./kicad";
import { ExtensionRequestHandler } from "./extensionRequestHandler";
import {
  HostedWebviewViewProvider,
  LOGS_VIEW_ID,
  PanelHost,
  SIDEBAR_VIEW_ID,
} from "./webviewHost";
import { CoreStatus } from "../../ui/shared/types";

const CORE_SERVER_READY_MARKER = "ATOPILE_SERVER_READY";

const panels = [
  { id: "panel-developer", label: "Developer" },
  { id: "panel-layout", label: "Layout" },
  { id: "panel-3d", label: "3D Model" },
];

let coreClient: CoreClient | undefined;

// -- Activate -----------------------------------------------------------------

export async function activate(context: vscode.ExtensionContext): Promise<void> {
  const output = vscode.window.createOutputChannel("atopile");
  output.appendLine("atopile extension activating");

  const coreServerPort = await findFreePort();
  const workspaceFolders =
    vscode.workspace.workspaceFolders?.map((folder) => folder.uri.fsPath) ?? [];

  const portEnv = {
    ATOPILE_CORE_SERVER_PORT: String(coreServerPort),
  };

  const version: string = context.extension.packageJSON.version;
  const resolver = new AtoResolver(context, output);
  const resolved = await resolveAtoBinary(resolver, version, output);
  if (!resolved) return;

  let panelHost!: PanelHost;
  const requestHandler = new ExtensionRequestHandler(
    (panelId) => panelHost.openPanel(panelId),
    output,
  );
  const proxy = new RpcProxy(coreServerPort, output, (webview, message) =>
    requestHandler.handle(webview, message)
  );
  panelHost = new PanelHost(context.extensionUri, proxy);
  const sidebarProvider = new HostedWebviewViewProvider(context.extensionUri, proxy, "sidebar");
  const logsProvider = new HostedWebviewViewProvider(context.extensionUri, proxy, "panel-logs");

  registerWebviews(context, sidebarProvider, logsProvider);
  registerCommands(context, panelHost);
  context.subscriptions.push(proxy, output, panelHost, sidebarProvider, logsProvider);

  const coreServer = await startCoreServer(resolved, portEnv, output, proxy);
  context.subscriptions.push(coreServer);

  coreClient = new CoreClient(proxy, workspaceFolders);
  coreClient.start();
  coreClient.sendResolverInfo({
    uvPath: resolved.command,
    atoBinary: resolved.atoBinary ?? "",
    mode: resolved.isLocal ? "local" : "production",
    version,
    coreServerPort,
  });
  context.subscriptions.push(coreClient);

  context.subscriptions.push(
    vscode.workspace.onDidChangeConfiguration((event) => {
      if (event.affectsConfiguration("atopile")) {
        coreClient?.sendExtensionSettings();
      }
    }),

    vscode.window.onDidChangeActiveTextEditor((editor) => {
      coreClient?.sendActiveFile(editor?.document.uri.fsPath ?? null);
    }),
  );
  coreClient.sendActiveFile(vscode.window.activeTextEditor?.document.uri.fsPath ?? null);

  output.appendLine("atopile extension activated");
}

export function deactivate(): void {
  coreClient?.dispose();
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
  panelHost: PanelHost,
): void {
  context.subscriptions.push(
    vscode.commands.registerCommand("atopile.openPanel", async () => {
      const pick = await vscode.window.showQuickPick(
        panels.map((p) => ({ label: p.label, id: p.id })),
        { placeHolder: "Select a panel to open" },
      );
      if (pick) panelHost.openPanel(pick.id);
    }),

    vscode.commands.registerCommand(
      "atopile.openKicad",
      async ({
        projectRoot,
        target,
      }: {
        projectRoot?: string;
        target?: string;
      } = {}) => {
        if (!projectRoot || !target) {
          vscode.window.showErrorMessage("Select a project and target first.");
          return;
        }

        try {
          await openKicadForBuild(projectRoot, target);
        } catch (err) {
          vscode.window.showErrorMessage(
            `Failed to open KiCad: ${err instanceof Error ? err.message : err}`,
          );
        }
      },
    ),

    vscode.commands.registerCommand(
      "atopile.openFile",
      async ({ path }: { path?: string } = {}) => {
        if (!path) {
          return;
        }

        await vscode.window.showTextDocument(vscode.Uri.file(path));
      },
    ),

    vscode.commands.registerCommand(
      "atopile.browseFolder",
      async (): Promise<string | undefined> => {
        const result = await vscode.window.showOpenDialog({
          canSelectFiles: false,
          canSelectFolders: true,
          canSelectMany: false,
          openLabel: "Select folder",
        });
        return result?.[0]?.fsPath;
      },
    ),
  );
}

function registerWebviews(
  context: vscode.ExtensionContext,
  sidebarProvider: HostedWebviewViewProvider,
  logsProvider: HostedWebviewViewProvider,
): void {
  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider(SIDEBAR_VIEW_ID, sidebarProvider, {
      webviewOptions: { retainContextWhenHidden: true },
    }),

    vscode.window.registerWebviewViewProvider(LOGS_VIEW_ID, logsProvider, {
      webviewOptions: { retainContextWhenHidden: true },
    }),
  );
}

async function startCoreServer(
  resolved: Awaited<ReturnType<AtoResolver["resolve"]>>,
  portEnv: Record<string, string>,
  output: vscode.OutputChannel,
  proxy: RpcProxy,
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
    proxy.clearBootstrapState("coreStatus");
  } catch (err: any) {
    output.appendLine(`[Extension] Core server failed to start: ${err.message}`);
    vscode.window.showWarningMessage(`atopile core server failed to start: ${err.message}`);
    const coreStatus = new CoreStatus();
    coreStatus.error = err.message;
    proxy.setBootstrapState("coreStatus", coreStatus);
  }
  return pm;
}
