# VS Code Extension Architecture

Key invariants:

- webviews only talk through RPC
- core interprets every webview-originated action first
- extension-only work returns from core as `extension_request`
- VS Code-coupled backend actions live under the `vscode.*` RPC namespace
- there is exactly one extension-to-core IPC socket
- webview and extension sessions are multiplexed over that socket via `sessionId`
- there is no direct webview command channel into the extension host

```mermaid
flowchart LR
  subgraph CLIENT["Client machine: desktop VS Code workbench or browser workbench"]
    subgraph VS["VS Code Workbench UI"]
      IDE["Workbench shell
activity bar
sidebar container
editor tabs
command palette
settings UI
active editor state"]
    end

    subgraph WV["Webview renderer processes"]
      HTML["render.tsx
mount app"]
      PMT["PostMessageTransport
send: vscode.postMessage(type=rpc:send)
recv: window.message(type=rpc:open / rpc:close / rpc:recv)"]
      WRPC["WebviewRpcClient
RpcClient(PostMessageTransport)
subscribe()
sendAction()
requestAction()
local connected state"]
      LOGRPC["LogRpcClient
same RPC connection
subscribeLogs / unsubscribeLogs
consume logs_stream / logs_error"]
      UI["Sidebar / Logs / Panels
call rpcClient directly"]
    end
  end

  subgraph SERVER["Extension-side runtime: local machine in normal desktop mode, remote VS Code server in SSH / web-IDE mode"]
    subgraph EH["Extension host process (Node)"]
      ACT["extension.ts / activate()
resolve ato
start core process
create RpcProxy
create CoreClient
register passive webview hosts"]
      HOST["HostedWebviewViewProvider + PanelHost
serve HTML/bootstrap only
sidebar view
logs view
editor panels
register webview with RpcProxy using panel/view id as sessionId"]
      PROXY["RpcProxy
only webview entrypoint in extension runtime
recv from webview: rpc:send
send to webview: rpc:open / rpc:close / rpc:recv
one shared WS to core
multiplex sessions by sessionId
intercept extension_request
send extension_response"]
      EXTSRV["ExtensionRequestHandler
vscode.openPanel
vscode.openFile
vscode.browseFolder
vscode.openKicad
vscode.resolveThreeDModel
vscode.log"]
      CORECLI["CoreClient
extension-owned RpcClient
uses RpcProxy transport
sessionId=extension
send resolverInfo
send extensionSettings
send setActiveFile
send discoverProjects
subscribe extensionSettings
apply backend settings to VS Code config"]
      PM["ProcessManager
spawn: ato serve core
env: ATOPILE_CORE_SERVER_PORT"]
      OUT["OutputChannel"]
      CMDS["VS Code commands
openPanel
openFile
browseFolder
openKicad"]
    end

    subgraph PY["Python core server process"]
      ENTRY["serve core
websockets.serve(CoreSocket.handle_client)
endpoint: ws://127.0.0.1:CORE/atopile-ui"]
      SOCK["CoreSocket
receive subscribe / action / extension_response
track subscriptions per sessionId
track pending extension requests per sessionId
track log task per sessionId
dispatch actions
broadcast state
return action_result"]
      STORE["Store
canonical shared UI state"]
      FILES["FileWatcher"]
      BUILDS["BuildQueue + builds model"]
      DOMAIN["Project / packages / parts / stdlib / artifacts handlers"]
      LOGS["SQLite Logs polling"]
    end
  end

  IDE -. activate extension .-> ACT
  IDE -. active editor + settings events .-> ACT
  IDE -. show views / panels .-> HOST
  IDE -. command palette .-> CMDS

  ACT --> PM
  ACT --> HOST
  ACT --> PROXY
  ACT --> CORECLI
  ACT --> CMDS
  ACT --> OUT
  ACT -. setActiveFile / extensionSettings .-> CORECLI
  PM -->|"spawn child process"| ENTRY
  CMDS --> HOST

  HOST -->|"HTML + asset bootstrap"| HTML
  HOST -->|"registerWebview(webview)"| PROXY

  HTML --> WRPC
  UI --> WRPC
  UI --> LOGRPC
  WRPC --> PMT
  LOGRPC --> WRPC

  PMT -->|"rpc:send + raw JSON"| PROXY
  PROXY -->|"rpc:open / rpc:close / rpc:recv"| PMT

  PROXY -->|"single WS
subscribe / action / extension_response
with sessionId"| ENTRY
  CORECLI -->|"same shared WS via RpcProxy
sessionId=extension"| PROXY

  ENTRY --> SOCK
  SOCK <--> STORE
  SOCK <--> FILES
  SOCK <--> BUILDS
  SOCK <--> DOMAIN
  SOCK <--> LOGS

  FILES -->|"projectFiles"| STORE
  BUILDS -->|"currentBuilds / previousBuilds"| STORE
  DOMAIN -->|"projects / packagesSummary / partsSearch /
installedParts / stdlibData / structureData /
variablesData / bomData"| STORE

  STORE -->|"on_change(key,data)"| SOCK
  SOCK -->|"state(key,data)
only to subscribed sessionIds"| PROXY
  LOGS -->|"logs_stream / logs_error"| SOCK
  SOCK -->|"state / logs_stream / logs_error / action_result
with sessionId"| PROXY

  SOCK -->|"extension_request
sessionId + requestId + action=vscode.* + payload"| PROXY
  PROXY -->|"handle(webview, extension_request)"| EXTSRV
  EXTSRV -->|"open panel / open file / browse dialog /
launch KiCad / resolve asWebviewUri / output log"| IDE
  PROXY -->|"extension_response
sessionId + requestId + ok/result/error"| SOCK
  PROXY -->|"sessionId=extension messages"| CORECLI

  CORECLI -->|"state(extensionSettings)
apply VS Code config"| IDE

  classDef proc fill:#e8f0fe,stroke:#4a67d6,color:#102040
  classDef state fill:#e8fff1,stroke:#2b8a57,color:#123524
  classDef ui fill:#fff4db,stroke:#c48a18,color:#4a3510
  class ACT,HOST,PROXY,EXTSRV,CORECLI,PM,OUT,CMDS,ENTRY,SOCK,FILES,BUILDS,DOMAIN,LOGS proc
  class STORE state
  class IDE,HTML,PMT,WRPC,LOGRPC,UI ui
```

## Boundary Meaning

`VS Code Workbench UI` is the host application shell: the activity bar, editor tabs, command palette, settings UI, and the active-editor state that the extension observes through the VS Code API.

It is not the same thing as either of these:

- `Extension host process`: the Node process running the extension code and owning the VS Code extension API surface.
- `Webview renderer processes`: isolated browser documents/processes used to render the sidebar, logs view, and editor panels.

So the workbench box is there to show where user-visible UI and VS Code-owned events live, while the extension host and webviews are the programmable runtimes attached to that shell.

## Placement In Remote Modes

In normal desktop VS Code:

- client machine runs the workbench UI, webview renderers, extension host, and Python core server

In Remote SSH, Codespaces, or similar web-IDE/server-backed modes:

- client machine runs the workbench UI and webview renderers
- backend VS Code server runs the extension host and Python core server

That is the main reason the diagram is split into `Client machine` and `Extension-side runtime`: the left side always stays with the user, while the right side may be local or remote depending on how VS Code is being used.

## Notes

- `connected` is local webview state derived from `rpc:open` / `rpc:close`; it is not stored in Python.
- panel/view ids are the logical `sessionId`s used for multiplexing webview traffic on the shared extension-to-core socket.
- `updateExtensionSetting` still goes through core first: webview action -> backend store -> `CoreClient` subscription -> VS Code config update.
- Logs share the same proxied RPC connection as the rest of the logs panel.
- VS Code-coupled backend routing lives in [`src/atopile/server/domains/vscode_bridge.py`](/home/ra/git/atopile/src/atopile/server/domains/vscode_bridge.py).
