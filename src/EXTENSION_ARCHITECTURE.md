# VS Code Extension Architecture

Active rewrite-native runtime only:

- Extension host runtime: `src/vscode-atopile/src`
- Webview UI source: `src/ui/webview`
- Shared RPC/types: `src/ui/shared`
- Python core runtime: `src/atopile/server`, `src/atopile/agent`, `src/atopile/layout_server`

Key invariants:

- Webviews only talk to the extension host through `rpc:*` postMessage events.
- The extension host keeps one shared websocket open to the Python core at
  `ws://127.0.0.1:<port>/atopile-ui`.
- Webview traffic and extension-owned traffic are multiplexed on that socket by
  `sessionId`.
- The canonical shared UI state lives in the backend `UiStore`.
- Backend work that needs VS Code APIs round-trips back through
  `extension_request` / `extension_response`.

```mermaid
flowchart LR
  subgraph CLIENT["Client machine"]
    IDE["VS Code workbench UI
activity bar / panels / editors / settings"]
    WV["Webview renderer
React UI
WebviewRpcClient
PostMessageTransport"]
  end

  subgraph EH["Extension host process (Node)
src/vscode-atopile/src"]
    HOST["Activation and webview hosting
extension.ts
webviewHost.ts
panel host
commands"]
    PROC["Runtime bootstrap
AtoResolver
ProcessManager
spawn ato serve core"]
    PROXY["RpcProxy
consumes rpc:send
emits rpc:open / rpc:close / rpc:recv
one shared websocket
multiplexes sessionId"]
    CORECLI["CoreClient
sessionId=extension
sends resolverInfo / extensionSettings /
setActiveFile / discoverProjects"]
    EXTSRV["ExtensionRequestHandler
consumes extension_request for vscode actions
openPanel / showLogsView / openFile / openDiff /
browseFolder / revealInOs / openInTerminal /
openKicad / resolveThreeDModel / restartExtensionHost / log"]
  end

  subgraph CORE["Python core process
src/atopile/server"]
    SERVER["CoreServer
server.py
endpoint: ws://127.0.0.1:PORT/atopile-ui"]
    SOCK["CoreSocket
consumes subscribe / action / extension_response
emits state / action_result / logs_stream /
agent_progress / extension_request"]
    STORE["UiStore
canonical shared UI state"]
    DOMAIN["Domain handlers
projects / builds / files / packages /
parts / stdlib / structure / variables /
BOM / migration / remote assets"]
    AGENT["AgentService
session state + progress"]
    LOGS["SQLite log streaming"]
    VSB["VscodeBridge
creates extension_request
converts extension_response to action_result"]
    LAYOUT["Layout service
separate local HTTP and layout websocket service"]
  end

  IDE -. workbench events and command invocations .-> HOST
  HOST -->|"HTML bootstrap for sidebar and panels"| WV
  PROC -->|"spawn child process: ato serve core"| SERVER

  WV -->|"window.postMessage
type=rpc:send"| PROXY
  PROXY -->|"window.message
type=rpc:open / rpc:close / rpc:recv"| WV

  HOST --> PROXY
  HOST --> CORECLI
  CORECLI -->|"same RpcProxy transport
sessionId=extension"| PROXY

  PROXY -->|"shared websocket
subscribe / action / extension_response
all tagged with sessionId"| SERVER
  SERVER --> SOCK

  SOCK <--> STORE
  SOCK <--> DOMAIN
  SOCK <--> AGENT
  SOCK <--> LOGS
  SOCK -->|"backend wants vscode side effect"| VSB
  DOMAIN -->|"openLayout selects PCB"| LAYOUT

  STORE -->|"state changes"| SOCK
  LOGS -->|"logs_stream"| SOCK

  VSB -->|"extension_request"| PROXY
  PROXY -->|"extension_request"| EXTSRV
  EXTSRV -->|"VS Code API side effects"| IDE
  PROXY -->|"extension_response"| SOCK

  classDef proc fill:#e8f0fe,stroke:#4a67d6,color:#102040
  classDef state fill:#e8fff1,stroke:#2b8a57,color:#123524
  classDef ui fill:#fff4db,stroke:#c48a18,color:#4a3510
  class HOST,PROC,PROXY,CORECLI,EXTSRV,SERVER,SOCK,DOMAIN,AGENT,LOGS,VSB,LAYOUT proc
  class STORE state
  class IDE,WV ui
```

Notes:

- This diagram shows the normal extension runtime path. It does not show the
  old `src/ui-server` path because that is not part of the active rewrite.
- `panel-layout` is the main intentional side channel: the panel still uses the
  main RPC path to choose the PCB, then embeds the separate local layout
  service.
